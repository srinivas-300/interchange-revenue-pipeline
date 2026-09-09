"""Schema diagrams for every table/model from raw to marts.

    python scripts/make_schema_diagrams.py

Writes docs/schema_raw.jpg, schema_staging.jpg, schema_intermediate.jpg, schema_marts.jpg
These describe the DESIGNED schema (types are Snowflake-style); models are built in later phases.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = Path("docs")
OUT.mkdir(parents=True, exist_ok=True)

INK = "#2B2B2A"
MUT = "#5F5E5A"
EDGE = "#7A7A76"
KEY = "#9A5B1D"

RAW = "#E7E4DB"
STG = "#DEEFE8"
SNP = "#F6E7CF"
INT = "#CFE7DD"
MRT = "#DCEBF7"

W = 39.0
XS = [1.0, 42.5, 84.0]


def card(ax, x, y, name, cols, accent):
    n = len(cols)
    body_h = n * 2.5 + 1.4
    ax.add_patch(Rectangle((x, y - 3.4), W, 3.4, fc=accent, ec=EDGE, lw=0.7))
    ax.text(x + 1.1, y - 1.7, name, fontsize=8.1, fontweight="bold", family="monospace",
            va="center", color=INK)
    ax.add_patch(Rectangle((x, y - 3.4 - body_h), W, body_h, fc="#FFFFFF", ec=EDGE, lw=0.7))
    cy = y - 3.4 - 1.7
    for cname, ctype, flag in cols:
        is_key = flag.startswith(("PK", "FK"))
        ax.text(x + 1.3, cy, cname, fontsize=6.8, family="monospace", va="center",
                color=INK, fontweight="bold" if flag.startswith("PK") else "normal")
        ax.text(x + W * 0.46, cy, ctype, fontsize=6.5, family="monospace", va="center", color=MUT)
        if flag:
            ax.text(x + W - 1.2, cy, flag, fontsize=6.2, family="monospace", va="center",
                    ha="right", color=KEY if is_key else MUT)
        cy -= 2.5
    return 3.4 + body_h


def layout(ax, cards, top):
    ys = [top, top, top]
    for name, cols, accent in cards:
        ci = ys.index(max(ys))
        h = card(ax, XS[ci], ys[ci], name, cols, accent)
        ys[ci] -= h + 3.2
    return min(ys)


def make(name, total, title, sub, cards):
    fig, ax = plt.subplots(figsize=(19.8, total / 6.4), dpi=170)
    ax.set_xlim(0, 124)
    ax.set_ylim(0, total)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.text(0, total - 2, title, fontsize=15, fontweight="bold", color=INK, va="top")
    ax.text(0, total - 6, sub, fontsize=8.5, color=MUT, va="top")
    bottom = layout(ax, cards, total - 12)
    used = total - (bottom - 4)
    ax.set_ylim(bottom - 4, total)
    fig.set_size_inches(19.8, used / 6.4)
    fig.savefig(OUT / name, dpi=170, bbox_inches="tight", facecolor="white", format="jpg")
    plt.close(fig)
    print("wrote", OUT / name)


META = [("_loaded_at", "TIMESTAMP_NTZ", ""), ("_batch_id", "VARCHAR", ""), ("_source_file", "VARCHAR", "")]

raw = [
    ("raw.sim.card_events", [
        ("event_id", "VARCHAR", ""), ("event_ts", "TIMESTAMP_NTZ", ""),
        ("ingested_at", "TIMESTAMP_NTZ", ""), ("transaction_id", "VARCHAR", ""),
        ("card_id", "VARCHAR", ""), ("merchant_id", "VARCHAR", ""), ("mcc", "VARCHAR", ""),
        ("event_type", "VARCHAR", ""), ("amount", "NUMBER(18,2)", ""),
        ("currency", "VARCHAR", ""), ("original_transaction_id", "VARCHAR", "null"),
    ] + META, RAW),
    ("raw.sim.interchange_rates", [
        ("mcc", "VARCHAR", ""), ("card_program", "VARCHAR", ""), ("region", "VARCHAR", ""),
        ("bps", "NUMBER(6,1)", ""), ("valid_from", "DATE", ""), ("valid_to", "DATE", "null"),
    ] + META, RAW),
    ("raw.sim.rewards_rates", [
        ("spend_category", "VARCHAR", ""), ("cashback_pct", "NUMBER(6,4)", ""),
        ("valid_from", "DATE", ""), ("valid_to", "DATE", "null"),
    ] + META, RAW),
    ("raw.sim.fx_rates", [
        ("currency", "VARCHAR", ""), ("rate_date", "DATE", ""), ("usd_rate", "NUMBER(12,6)", ""),
    ] + META, RAW),
    ("raw.sim.network_settlement", [
        ("settlement_date", "DATE", ""), ("file_id", "VARCHAR", ""),
        ("total_settled_amount_usd", "NUMBER(18,2)", ""), ("total_txn_count", "NUMBER(38,0)", ""),
    ] + META, RAW),
    ("raw.sim.companies", [
        ("company_id", "VARCHAR", ""), ("company_name", "VARCHAR", ""),
        ("region", "VARCHAR", ""), ("onboarded_at", "TIMESTAMP_NTZ", ""),
    ] + META, RAW),
    ("raw.sim.cards", [
        ("card_id", "VARCHAR", ""), ("company_id", "VARCHAR", ""),
        ("card_program", "VARCHAR", ""), ("issued_at", "TIMESTAMP_NTZ", ""),
        ("status", "VARCHAR", ""),
    ] + META, RAW),
    ("raw.sim.merchants", [
        ("merchant_id", "VARCHAR", ""), ("merchant_name", "VARCHAR", ""), ("mcc", "VARCHAR", ""),
        ("merchant_country", "VARCHAR", ""), ("descriptor", "VARCHAR", ""),
    ] + META, RAW),
]

staging = [
    ("stg_card_events", [
        ("event_id", "VARCHAR", "PK"), ("event_ts", "TIMESTAMP_NTZ", "NN"),
        ("ingested_at", "TIMESTAMP_NTZ", "NN"), ("transaction_id", "VARCHAR", "NN"),
        ("card_id", "VARCHAR", "FK cards"), ("merchant_id", "VARCHAR", "FK merch"),
        ("mcc", "VARCHAR", "NN"), ("event_type", "VARCHAR [enum]", "NN"),
        ("amount", "NUMBER(18,2)", ">=0"), ("currency", "VARCHAR(3)", "NN"),
        ("original_transaction_id", "VARCHAR", "null"), ("loaded_at", "TIMESTAMP_NTZ", ""),
    ], STG),
    ("stg_interchange_rates", [
        ("mcc", "VARCHAR", "PK"), ("card_program", "VARCHAR", "PK"), ("region", "VARCHAR", "PK"),
        ("valid_from", "DATE", "PK"), ("valid_to", "DATE", "null"), ("bps", "NUMBER(6,1)", "NN"),
    ], STG),
    ("stg_rewards_rates", [
        ("spend_category", "VARCHAR", "PK"), ("valid_from", "DATE", "PK"),
        ("valid_to", "DATE", "null"), ("cashback_pct", "NUMBER(6,4)", "NN"),
    ], STG),
    ("stg_fx_rates", [
        ("currency", "VARCHAR(3)", "PK"), ("rate_date", "DATE", "PK"),
        ("usd_rate", "NUMBER(12,6)", "NN"),
    ], STG),
    ("stg_network_settlement", [
        ("settlement_date", "DATE", "PK"), ("file_id", "VARCHAR", "NN"),
        ("total_settled_amount_usd", "NUMBER(18,2)", "NN"), ("total_txn_count", "NUMBER(38,0)", "NN"),
    ], STG),
    ("stg_companies", [
        ("company_id", "VARCHAR", "PK"), ("company_name", "VARCHAR", "NN"),
        ("region", "VARCHAR [enum]", "NN"), ("onboarded_at", "DATE", "NN"),
    ], STG),
    ("stg_cards", [
        ("card_id", "VARCHAR", "PK"), ("company_id", "VARCHAR", "FK companies"),
        ("card_program", "VARCHAR [enum]", "NN"), ("issued_at", "DATE", "NN"),
        ("status", "VARCHAR", "NN"),
    ], STG),
    ("stg_merchants", [
        ("merchant_id", "VARCHAR", "PK"), ("merchant_name", "VARCHAR", "NN"),
        ("mcc", "VARCHAR", "NN"), ("merchant_country", "VARCHAR(2)", "NN"),
        ("descriptor", "VARCHAR", ""),
    ], STG),
    ("snapshots.snap_interchange_rates", [
        ("mcc", "VARCHAR", ""), ("card_program", "VARCHAR", ""), ("region", "VARCHAR", ""),
        ("bps", "NUMBER(6,1)", ""), ("dbt_scd_id", "VARCHAR", "PK"),
        ("dbt_valid_from", "TIMESTAMP_NTZ", ""), ("dbt_valid_to", "TIMESTAMP_NTZ", "null"),
    ], SNP),
    ("snapshots.snap_rewards_rates", [
        ("spend_category", "VARCHAR", ""), ("cashback_pct", "NUMBER(6,4)", ""),
        ("dbt_scd_id", "VARCHAR", "PK"), ("dbt_valid_from", "TIMESTAMP_NTZ", ""),
        ("dbt_valid_to", "TIMESTAMP_NTZ", "null"),
    ], SNP),
]

intermediate = [
    ("int_transaction_lifecycle", [
        ("transaction_id", "VARCHAR", "PK"), ("card_id", "VARCHAR", "FK cards"),
        ("merchant_id", "VARCHAR", "FK merch"), ("mcc", "VARCHAR", "NN"),
        ("currency", "VARCHAR(3)", "NN"), ("first_auth_at", "TIMESTAMP_NTZ", "NN"),
        ("current_status", "VARCHAR [enum]", "NN"), ("authorized_amount", "NUMBER(18,2)", ""),
        ("reversed_amount", "NUMBER(18,2)", ""), ("cleared_amount", "NUMBER(18,2)", ""),
        ("settled_amount", "NUMBER(18,2)", ""), ("settled_at", "DATE", "null"),
        ("n_events", "NUMBER(38,0)", "NN"),
    ], INT),
    ("int_txn_rated", [
        ("transaction_id", "VARCHAR", "PK / FK lifecycle"), ("settlement_day", "DATE", "NN"),
        ("accounting_period", "VARCHAR(7)", "NN"), ("card_program", "VARCHAR", "NN"),
        ("region", "VARCHAR", "NN"), ("spend_category", "VARCHAR", "NN"),
        ("currency", "VARCHAR(3)", "NN"), ("settled_amount", "NUMBER(18,2)", "NN"),
        ("fx_usd_rate", "NUMBER(12,6)", "NN"), ("settled_amount_usd", "NUMBER(18,2)", "NN"),
        ("rate_bps", "NUMBER(6,1)", "NN"), ("cashback_pct", "NUMBER(6,4)", "NN"),
        ("gross_interchange_usd", "NUMBER(18,4)", "NN"), ("network_fee_usd", "NUMBER(18,4)", "NN"),
        ("rewards_accrued_usd", "NUMBER(18,4)", "NN"),
    ], INT),
    ("int_refund_matching", [
        ("refund_event_id", "VARCHAR", "PK"), ("event_type", "VARCHAR [enum]", "NN"),
        ("refund_ts", "TIMESTAMP_NTZ", "NN"), ("refund_amount", "NUMBER(18,2)", "NN"),
        ("currency", "VARCHAR(3)", "NN"), ("card_id", "VARCHAR", "NN"),
        ("merchant_id", "VARCHAR", "NN"), ("matched_transaction_id", "VARCHAR", "FK lifecycle"),
        ("match_method", "VARCHAR [enum]", "NN"), ("match_confidence", "NUMBER(4,3)", ""),
        ("original_settlement_day", "DATE", "null"),
        ("original_accounting_period", "VARCHAR(7)", "null"),
    ], INT),
]

marts = [
    ("dim_company", [
        ("company_key", "NUMBER", "PK"), ("company_id", "VARCHAR", "NK"),
        ("company_name", "VARCHAR", ""), ("region", "VARCHAR", ""), ("onboarded_at", "DATE", ""),
    ], MRT),
    ("dim_card", [
        ("card_key", "NUMBER", "PK"), ("card_id", "VARCHAR", "NK"),
        ("company_key", "NUMBER", "FK dim_company"), ("card_program", "VARCHAR", ""),
        ("issued_at", "DATE", ""), ("status", "VARCHAR", ""),
    ], MRT),
    ("dim_merchant", [
        ("merchant_key", "NUMBER", "PK"), ("merchant_id", "VARCHAR", "NK"),
        ("merchant_name", "VARCHAR", ""), ("mcc", "VARCHAR", ""),
        ("spend_category", "VARCHAR", ""), ("merchant_country", "VARCHAR(2)", ""),
    ], MRT),
    ("dim_date", [
        ("date_day", "DATE", "PK"), ("year", "NUMBER", ""), ("quarter", "NUMBER", ""),
        ("month", "NUMBER", ""), ("accounting_period", "VARCHAR(7)", ""),
        ("is_month_end", "BOOLEAN", ""),
    ], MRT),
    ("fct_transactions", [
        ("transaction_id", "VARCHAR", "PK"), ("card_key", "NUMBER", "FK dim_card"),
        ("merchant_key", "NUMBER", "FK dim_merchant"), ("company_key", "NUMBER", "FK dim_company"),
        ("first_auth_date", "DATE", "FK dim_date"), ("settled_at", "DATE", "FK dim_date"),
        ("current_status", "VARCHAR", ""), ("currency", "VARCHAR(3)", ""),
        ("authorized_amount", "NUMBER(18,2)", ""), ("settled_amount", "NUMBER(18,2)", ""),
        ("settled_amount_usd", "NUMBER(18,2)", ""),
    ], MRT),
    ("fct_interchange_revenue", [
        ("transaction_id", "VARCHAR", "PK / FK fct_txn"), ("settlement_day", "DATE", "PK / FK date"),
        ("accounting_period", "VARCHAR(7)", "NN"), ("card_key", "NUMBER", "FK dim_card"),
        ("merchant_key", "NUMBER", "FK dim_merchant"), ("company_key", "NUMBER", "FK dim_company"),
        ("settled_amount_usd", "NUMBER(18,2)", ""), ("gross_interchange_usd", "NUMBER(18,4)", ""),
        ("network_fee_usd", "NUMBER(18,4)", ""), ("rewards_accrued_usd", "NUMBER(18,4)", ""),
        ("net_interchange_usd", "NUMBER(18,4)", ""), ("is_recognized", "BOOLEAN", ""),
    ], MRT),
    ("fct_revenue_adjustments", [
        ("adjustment_id", "VARCHAR", "PK"), ("source_event_id", "VARCHAR", "NN"),
        ("original_transaction_id", "VARCHAR", "FK fct_txn"),
        ("original_accounting_period", "VARCHAR(7)", "NN"),
        ("booked_accounting_period", "VARCHAR(7)", "NN"),
        ("adjustment_type", "VARCHAR [enum]", "NN"),
        ("gross_interchange_reversed_usd", "NUMBER(18,4)", ""),
        ("rewards_reversed_usd", "NUMBER(18,4)", ""), ("net_adjustment_usd", "NUMBER(18,4)", ""),
        ("booked_at", "DATE", "FK dim_date"),
    ], MRT),
    ("recon_settlement", [
        ("settlement_day", "DATE", "PK / FK date"), ("internal_settled_usd", "NUMBER(18,2)", ""),
        ("file_settled_usd", "NUMBER(18,2)", ""), ("variance_usd", "NUMBER(18,2)", ""),
        ("variance_pct", "NUMBER(8,5)", ""), ("variance_class", "VARCHAR [enum]", ""),
        ("internal_txn_count", "NUMBER", ""), ("file_txn_count", "NUMBER", ""),
        ("status", "VARCHAR [enum]", ""),
    ], MRT),
    ("recognized_revenue", [
        ("accounting_period", "VARCHAR(7)", "PK"), ("period_status", "VARCHAR [enum]", ""),
        ("recognized_net_interchange_usd", "NUMBER(18,2)", ""),
        ("accrued_net_interchange_usd", "NUMBER(18,2)", ""),
        ("pending_net_interchange_usd", "NUMBER(18,2)", ""),
        ("adjustments_usd", "NUMBER(18,2)", ""), ("locked_at", "TIMESTAMP_NTZ", "null"),
    ], MRT),
]

LEG = "keys:  PK primary  -  FK foreign (-> target)  -  NK natural key  -  NN not null  -  [enum] constrained values"

make("schema_raw.jpg", 116, "raw layer  -  raw.sim.*  (loaded as delivered, + audit columns, append-only)",
     LEG + "   -   types carried from the Parquet; no constraints; duplicates kept", raw)
make("schema_staging.jpg", 150, "staging layer  -  stg_*  (typed, renamed, deduped, contract-enforced)  +  SCD2 snapshots",
     LEG + "   -   one staging model per source table, same grain; snapshots add dbt_valid_from / dbt_valid_to", staging)
make("schema_intermediate.jpg", 66, "intermediate layer  -  int_*  (the joins and business logic)",
     LEG + "   -   int_transaction_lifecycle: 1 row/transaction  |  int_txn_rated: settled txns only  |  int_refund_matching: 1 row/refund event", intermediate)
make("schema_marts.jpg", 132, "marts layer  -  dim_* / fct_*  (star schema, surrogate keys)",
     LEG + "   -   fct_interchange_revenue grain = transaction x settlement_day; fct_transactions grain = transaction", marts)
