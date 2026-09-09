"""The card event stream.

Each authorization spawns a short lifecycle of events with their own real
timestamps (which can land on later dates than the auth). All events for the
whole window are produced, then duplicates are injected and the rows are
shuffled so nothing downstream can rely on file ordering.
"""

import numpy as np
import pandas as pd

from .config import CURRENCIES

EVENT_COLUMNS = [
    "event_id",
    "event_ts",
    "ingested_at",
    "transaction_id",
    "card_id",
    "merchant_id",
    "mcc",
    "event_type",
    "amount",
    "currency",
    "original_transaction_id",
]

_HOME_CURRENCY_POOL = np.array(["USD", "USD", "USD", "USD", "EUR", "GBP", "INR"])


def _inclusive(rng, lo_hi: tuple) -> int:
    lo, hi = lo_hi
    return int(rng.integers(lo, hi + 1))


def _card_home_currencies(rng, n: int) -> np.ndarray:
    idx = rng.integers(0, len(_HOME_CURRENCY_POOL), size=n)
    return _HOME_CURRENCY_POOL[idx]


def _other_currency(rng, currency: str) -> str:
    others = [c for c in CURRENCIES if c != currency]
    return others[int(rng.integers(0, len(others)))]


def generate_events(cfg, rng, cards, merchants, dates, window_end) -> pd.DataFrame:
    card_ids = cards["card_id"].to_numpy()
    card_currency = _card_home_currencies(rng, len(card_ids))
    merchant_ids = merchants["merchant_id"].to_numpy()
    merchant_mcc = merchants["mcc"].to_numpy()

    events: list[tuple] = []
    event_seq = 0
    txn_seq = 0

    def emit(ts, txn, card_i, merch_i, event_type, amount, currency, original=None):
        nonlocal event_seq
        event_seq += 1
        arrival = ts + pd.Timedelta(minutes=int(rng.integers(1, 240)))
        if rng.random() < cfg.p_late_arrival:
            arrival = arrival + pd.Timedelta(days=1)
        events.append(
            (
                f"E{event_seq:09d}",
                ts,
                arrival,
                txn,
                card_ids[card_i],
                merchant_ids[merch_i],
                merchant_mcc[merch_i],
                event_type,
                round(float(amount), 2),
                currency,
                original,
            )
        )

    for d in dates:
        day_start = pd.Timestamp(d.date())
        n_auths = int(rng.integers(cfg.auths_per_day[0], cfg.auths_per_day[1] + 1))

        for _ in range(n_auths):
            txn_seq += 1
            txn = f"T{txn_seq:09d}"
            card_i = int(rng.integers(0, len(card_ids)))
            merch_i = int(rng.integers(0, len(merchant_ids)))

            currency = card_currency[card_i]
            if rng.random() < cfg.p_cross_border:
                currency = _other_currency(rng, currency)

            amount = float(np.exp(rng.normal(cfg.amount_lognorm_mean, cfg.amount_lognorm_sigma)))
            amount = min(amount, cfg.amount_cap)

            auth_ts = day_start + pd.Timedelta(seconds=int(rng.integers(0, 86_400)))
            emit(auth_ts, txn, card_i, merch_i, "authorization", amount, currency)

            cleared_amount = amount
            if rng.random() < cfg.p_auth_reversal:
                reversed_amount = amount * float(rng.uniform(0.1, 0.9))
                emit(
                    auth_ts + pd.Timedelta(minutes=int(rng.integers(5, 720))),
                    txn, card_i, merch_i, "auth_reversal", reversed_amount, currency,
                )
                cleared_amount = amount - reversed_amount

            if rng.random() < cfg.p_never_clears:
                continue  # auth expires, nothing settles

            clearing_ts = auth_ts + pd.Timedelta(
                days=_inclusive(rng, cfg.clearing_lag_days),
                hours=int(rng.integers(0, 24)),
            )
            if rng.random() < cfg.p_partial_clearing:
                split = float(rng.uniform(0.3, 0.7))
                emit(clearing_ts, txn, card_i, merch_i, "clearing", cleared_amount * split, currency)
                emit(
                    clearing_ts + pd.Timedelta(days=1),
                    txn, card_i, merch_i, "clearing", cleared_amount * (1 - split), currency,
                )
            else:
                emit(clearing_ts, txn, card_i, merch_i, "clearing", cleared_amount, currency)

            settlement_ts = clearing_ts + pd.Timedelta(days=_inclusive(rng, cfg.settlement_lag_days))
            emit(settlement_ts, txn, card_i, merch_i, "settlement", cleared_amount, currency)

            if rng.random() < cfg.p_refund:
                refund_ts = settlement_ts + pd.Timedelta(days=_inclusive(rng, cfg.refund_lag_days))
                full = rng.random() < 0.7
                refund_amount = cleared_amount if full else cleared_amount * float(rng.uniform(0.2, 0.8))
                original = None if rng.random() < cfg.p_refund_missing_link else txn
                emit(refund_ts, txn, card_i, merch_i, "refund", refund_amount, currency, original)

            if rng.random() < cfg.p_dispute:
                dispute_ts = settlement_ts + pd.Timedelta(days=_inclusive(rng, cfg.dispute_lag_days))
                emit(dispute_ts, txn, card_i, merch_i, "dispute", cleared_amount, currency)

    df = pd.DataFrame(events, columns=EVENT_COLUMNS)

    # inject a few exact-duplicate rows for the staging layer to dedupe
    dup_mask = rng.random(len(df)) < cfg.p_duplicate_event
    df = pd.concat([df, df[dup_mask]], ignore_index=True)

    # drop events that fall after the window (transaction still in flight)
    window_end_eod = pd.Timestamp(window_end.date()) + pd.Timedelta(days=1)
    df = df[df["event_ts"] < window_end_eod].copy()

    # shuffle: the feed is not pre-sorted
    df = df.sample(frac=1.0, random_state=int(rng.integers(0, 2**31))).reset_index(drop=True)
    return df
