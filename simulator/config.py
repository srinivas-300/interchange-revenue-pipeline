"""Tunable parameters for the simulator.

Everything that shapes the generated data lives here so the behaviour is easy to
read and adjust without digging through the generation code.
"""

from dataclasses import dataclass

# USD value of one unit of each currency (rough, only needs to be plausible).
CURRENCIES = {"USD": 1.00, "EUR": 1.08, "GBP": 1.27, "INR": 0.012}

REGIONS = ["NA", "EU", "APAC"]

CARD_PROGRAMS = ["VISA_COMMERCIAL_STANDARD", "VISA_COMMERCIAL_PREMIUM"]

# (mcc, spend_category, relative share of transaction volume)
MCC_CATALOG = [
    ("5812", "restaurants", 0.18),
    ("5411", "grocery", 0.10),
    ("4511", "airlines", 0.06),
    ("7011", "lodging", 0.07),
    ("5734", "software", 0.20),
    ("5732", "electronics", 0.08),
    ("5942", "office_supplies", 0.09),
    ("4121", "rideshare", 0.10),
    ("5999", "misc_retail", 0.12),
]


@dataclass(frozen=True)
class SimConfig:
    seed: int = 42

    # entity counts
    n_companies: int = 40
    cards_per_company: tuple = (3, 25)      # inclusive uniform range
    n_merchants: int = 300

    # daily authorization volume (across all cards)
    auths_per_day: tuple = (1200, 1800)     # inclusive uniform range

    # lifecycle probabilities
    p_auth_reversal: float = 0.08
    p_never_clears: float = 0.03
    p_partial_clearing: float = 0.15        # clearing arrives split in two
    p_refund: float = 0.03
    p_refund_missing_link: float = 0.20     # refund row without original_transaction_id
    p_dispute: float = 0.005
    p_cross_border: float = 0.05
    p_duplicate_event: float = 0.01         # exact-duplicate rows in the feed
    p_late_arrival: float = 0.03            # event ingested a day after it occurred

    # lag distributions, in days (inclusive uniform range)
    clearing_lag_days: tuple = (0, 2)
    settlement_lag_days: tuple = (1, 2)
    refund_lag_days: tuple = (2, 30)
    dispute_lag_days: tuple = (5, 60)

    # transaction amount ~ lognormal(mean, sigma) on the natural-log scale
    amount_lognorm_mean: float = 4.2       # median ~ e^4.2 ≈ $67
    amount_lognorm_sigma: float = 1.1
    amount_cap: float = 25000.0
