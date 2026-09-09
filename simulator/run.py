"""Orchestrates one simulation run over a date window."""

import numpy as np
import pandas as pd
from faker import Faker

from .config import SimConfig
from .entities import build_cards, build_companies, build_merchants
from .rates import build_fx_rates, build_interchange_rates, build_rewards_rates
from .settlement import build_network_settlement
from .transactions import generate_events
from .writer import write_partitioned, write_static


def run(start: str, end: str, seed: int = 42, out_dir: str = "data/landing", fmt: str = "parquet") -> None:
    cfg = SimConfig(seed=seed)
    rng = np.random.default_rng(seed)
    fake = Faker()
    Faker.seed(seed)

    window_start = pd.Timestamp(start)
    window_end = pd.Timestamp(end)
    if window_end < window_start:
        raise ValueError("--end is before --start")
    dates = pd.date_range(window_start, window_end, freq="D")

    companies = build_companies(cfg, rng, fake)
    cards = build_cards(cfg, rng, companies)
    merchants = build_merchants(cfg, rng, fake)

    interchange_rates = build_interchange_rates(rng, window_start, window_end)
    rewards_rates = build_rewards_rates(rng, window_start, window_end)
    fx_rates = build_fx_rates(rng, dates)

    events = generate_events(cfg, rng, cards, merchants, dates, window_end)
    network_settlement = build_network_settlement(events, fx_rates)

    write_static(companies, out_dir, "companies", fmt)
    write_static(cards, out_dir, "cards", fmt)
    write_static(merchants, out_dir, "merchants", fmt)
    write_static(interchange_rates, out_dir, "interchange_rates", fmt)
    write_static(rewards_rates, out_dir, "rewards_rates", fmt)

    write_partitioned(events, out_dir, "card_events", "event_ts", fmt)
    write_partitioned(fx_rates, out_dir, "fx_rates", "rate_date", fmt)
    write_partitioned(network_settlement, out_dir, "network_settlement", "settlement_date", fmt)

    print(
        f"companies={len(companies)}  cards={len(cards)}  merchants={len(merchants)}\n"
        f"card_events={len(events)}  settlement_days={len(network_settlement)}  "
        f"window_days={len(dates)}\n"
        f"written to {out_dir}/ as {fmt}"
    )
