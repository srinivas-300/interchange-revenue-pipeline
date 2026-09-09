"""Effective-dated rate tables and daily FX rates.

Each rate table gets exactly one change part-way through the window, so the
downstream models have to do a real as-of join on the settlement date rather
than a simple equijoin.
"""

import pandas as pd

from .config import CARD_PROGRAMS, CURRENCIES, MCC_CATALOG, REGIONS

_REGION_ADJ_BPS = {"NA": 0.0, "EU": 8.0, "APAC": 12.0}


def _midpoint(window_start: pd.Timestamp, window_end: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp((window_start + (window_end - window_start) / 2).date())


def build_interchange_rates(rng, window_start, window_end) -> pd.DataFrame:
    change_date = _midpoint(window_start, window_end)
    rows = []
    for mcc, _category, _share in MCC_CATALOG:
        base = float(rng.uniform(150, 240))
        for program in CARD_PROGRAMS:
            premium = 15.0 if program.endswith("PREMIUM") else 0.0
            for region in REGIONS:
                bps_v1 = round(base + premium + _REGION_ADJ_BPS[region], 1)
                bps_v2 = round(bps_v1 * float(rng.uniform(0.96, 1.03)), 1)
                rows.append(
                    dict(mcc=mcc, card_program=program, region=region,
                         bps=bps_v1, valid_from=window_start, valid_to=change_date)
                )
                rows.append(
                    dict(mcc=mcc, card_program=program, region=region,
                         bps=bps_v2, valid_from=change_date, valid_to=pd.NaT)
                )
    return pd.DataFrame(rows)


def build_rewards_rates(rng, window_start, window_end) -> pd.DataFrame:
    change_date = _midpoint(window_start, window_end)
    rows = []
    for _mcc, category, _share in MCC_CATALOG:
        pct_v1 = round(float(rng.uniform(0.005, 0.018)), 4)
        pct_v2 = round(pct_v1 * float(rng.uniform(0.9, 1.1)), 4)
        rows.append(
            dict(spend_category=category, cashback_pct=pct_v1,
                 valid_from=window_start, valid_to=change_date)
        )
        rows.append(
            dict(spend_category=category, cashback_pct=pct_v2,
                 valid_from=change_date, valid_to=pd.NaT)
        )
    return pd.DataFrame(rows)


def build_fx_rates(rng, dates) -> pd.DataFrame:
    """Random-walk each non-USD currency around its starting value."""
    state = dict(CURRENCIES)
    rows = []
    for d in dates:
        for currency, _base in CURRENCIES.items():
            if currency == "USD":
                rate = 1.0
            else:
                drift = float(rng.normal(0, 0.003))
                state[currency] = max(0.001, state[currency] * (1 + drift))
                rate = round(state[currency], 6)
            rows.append(dict(currency=currency, rate_date=pd.Timestamp(d.date()), usd_rate=rate))
    return pd.DataFrame(rows)
