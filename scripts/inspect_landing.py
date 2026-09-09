"""Quick sanity checks on the simulator output.

Usage:  python scripts/inspect_landing.py [data/landing]
"""

import sys
from pathlib import Path

import pandas as pd

root = Path(sys.argv[1] if len(sys.argv) > 1 else "data/landing")


def load(name: str) -> pd.DataFrame:
    files = sorted(root.glob(f"{name}/**/*.parquet"))
    if not files:
        return pd.DataFrame()
    return pd.concat((pd.read_parquet(f) for f in files), ignore_index=True)


events = load("card_events")
print(f"card_events rows: {len(events):,}")
print(events["event_type"].value_counts().to_string(), "\n")

print(f"duplicate event_id rows: {int(events['event_id'].duplicated().sum()):,}")

types_by_txn = events.groupby("transaction_id")["event_type"].agg(set)
settled = types_by_txn[types_by_txn.apply(lambda s: "settlement" in s)]
missing_clearing = settled[settled.apply(lambda s: "clearing" not in s)]
print(f"settled txns with no clearing event: {len(missing_clearing):,}  (should be 0)")

refunds = events[events["event_type"] == "refund"]
if len(refunds):
    miss_rate = refunds["original_transaction_id"].isna().mean()
    print(f"refunds: {len(refunds):,}  missing original link: {miss_rate:.1%}")

late = (events["ingested_at"].dt.normalize() > events["event_ts"].dt.normalize()).mean()
print(f"events arriving a day late: {late:.1%}\n")

for name in ["companies", "cards", "merchants", "interchange_rates", "rewards_rates", "fx_rates"]:
    print(f"{name}: {len(load(name)):,} rows")

settlement = load("network_settlement")
print(
    f"network_settlement: {len(settlement):,} days  "
    f"total USD {settlement['total_settled_amount_usd'].sum():,.2f}"
)
