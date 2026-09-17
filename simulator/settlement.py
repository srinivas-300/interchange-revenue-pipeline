"""Daily network settlement file.

This is the "bank truth" the reconciliation step checks the internal numbers
against: for each settlement date, the total settled amount converted to USD and
the distinct transaction count.
"""

import pandas as pd


def build_network_settlement(events: pd.DataFrame, fx_rates: pd.DataFrame) -> pd.DataFrame:
    # The event feed carries injected duplicate rows, but the bank settles each
    # transaction once. Building from the raw frame would count the duplicates in
    # the amount (a sum) but not in the transaction count (nunique), so the file
    # would disagree with any correctly deduplicated ledger.
    settled = events[events["event_type"] == "settlement"].drop_duplicates("event_id").copy()
    settled["settlement_date"] = settled["event_ts"].dt.normalize()

    fx = fx_rates.rename(columns={"rate_date": "settlement_date"})
    settled = settled.merge(fx, how="left", on=["currency", "settlement_date"])
    settled["amount_usd"] = settled["amount"] * settled["usd_rate"]

    grouped = (
        settled.groupby("settlement_date")
        .agg(
            total_settled_amount_usd=("amount_usd", "sum"),
            total_txn_count=("transaction_id", "nunique"),
        )
        .reset_index()
    )
    grouped["file_id"] = grouped["settlement_date"].dt.strftime("NET-%Y%m%d")
    grouped["total_settled_amount_usd"] = grouped["total_settled_amount_usd"].round(2)
    return grouped[
        ["settlement_date", "file_id", "total_settled_amount_usd", "total_txn_count"]
    ]
