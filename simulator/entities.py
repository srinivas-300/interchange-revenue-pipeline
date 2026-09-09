"""Static dimensions: companies, cards, merchants."""

import numpy as np
import pandas as pd

from .config import CARD_PROGRAMS, MCC_CATALOG, REGIONS

_DESCRIPTOR_PREFIXES = ["SQ *", "TST* ", "PP*", "", "PAYPAL *", "AMZN Mktp "]


def build_companies(cfg, rng, fake) -> pd.DataFrame:
    rows = []
    for i in range(1, cfg.n_companies + 1):
        onboarded = pd.Timestamp("2022-01-01") + pd.Timedelta(days=int(rng.integers(0, 730)))
        rows.append(
            {
                "company_id": f"C{i:04d}",
                "company_name": fake.company(),
                "region": REGIONS[int(rng.integers(0, len(REGIONS)))],
                "onboarded_at": onboarded,
            }
        )
    return pd.DataFrame(rows)


def build_cards(cfg, rng, companies: pd.DataFrame) -> pd.DataFrame:
    rows = []
    card_seq = 1
    for _, c in companies.iterrows():
        n = int(rng.integers(cfg.cards_per_company[0], cfg.cards_per_company[1] + 1))
        for _ in range(n):
            program = CARD_PROGRAMS[int(rng.integers(0, len(CARD_PROGRAMS)))]
            issued = c["onboarded_at"] + pd.Timedelta(days=int(rng.integers(0, 120)))
            rows.append(
                {
                    "card_id": f"K{card_seq:06d}",
                    "company_id": c["company_id"],
                    "card_program": program,
                    "issued_at": issued,
                    "status": "active",
                }
            )
            card_seq += 1
    return pd.DataFrame(rows)


def build_merchants(cfg, rng, fake) -> pd.DataFrame:
    mcc_codes = [m[0] for m in MCC_CATALOG]
    weights = np.array([m[2] for m in MCC_CATALOG], dtype=float)
    weights = weights / weights.sum()
    countries = ["US", "US", "US", "GB", "DE", "IN"]  # weighted toward the US

    rows = []
    for i in range(1, cfg.n_merchants + 1):
        mcc = mcc_codes[int(rng.choice(len(mcc_codes), p=weights))]
        name = fake.company().upper()
        rows.append(
            {
                "merchant_id": f"M{i:05d}",
                "merchant_name": name,
                "mcc": mcc,
                "merchant_country": countries[int(rng.integers(0, len(countries)))],
                "descriptor": _messy_descriptor(name, rng),
            }
        )
    return pd.DataFrame(rows)


def _messy_descriptor(name: str, rng) -> str:
    """Mimic the noisy free-text descriptor a card network passes through."""
    prefix = _DESCRIPTOR_PREFIXES[int(rng.integers(0, len(_DESCRIPTOR_PREFIXES)))]
    tail = "" if rng.random() > 0.4 else f" #{int(rng.integers(1000, 9999))}"
    return f"{prefix}{name[:18]}{tail}".strip()
