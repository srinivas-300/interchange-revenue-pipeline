"""Grain of every table/model from raw to marts.

    python scripts/make_grain_table.py   ->   docs/grain.jpg
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("docs")
OUT.mkdir(parents=True, exist_ok=True)

INK = "#2B2B2A"
MUT = "#5F5E5A"
EDGE = "#7A7A76"

SECTIONS = [
    ("raw layer  -  raw.sim.*   (grain = whatever the source file delivers; duplicates present)", [
        ("card_events", "one row per card lifecycle event", "event_id (not unique: ~1% dups)"),
        ("interchange_rates", "one row per rate version", "mcc, card_program, region, valid_from"),
        ("rewards_rates", "one row per cashback-rate version", "spend_category, valid_from"),
        ("fx_rates", "one row per currency per day", "currency, rate_date"),
        ("network_settlement", "one row per settlement date", "settlement_date"),
        ("companies", "one row per company", "company_id"),
        ("cards", "one row per card", "card_id"),
        ("merchants", "one row per merchant", "merchant_id"),
    ]),
    ("staging layer  -  stg_*   (same grain as the source, now unique)", [
        ("stg_card_events", "one row per card lifecycle event", "event_id  (unique after dedupe)"),
        ("stg_interchange_rates", "one row per rate version", "mcc, card_program, region, valid_from"),
        ("stg_rewards_rates", "one row per cashback-rate version", "spend_category, valid_from"),
        ("stg_fx_rates", "one row per currency per day", "currency, rate_date"),
        ("stg_network_settlement", "one row per settlement date", "settlement_date"),
        ("stg_companies", "one row per company", "company_id"),
        ("stg_cards", "one row per card", "card_id"),
        ("stg_merchants", "one row per merchant", "merchant_id"),
    ]),
    ("snapshots  -  dbt SCD2   (grain = natural key x validity interval)", [
        ("snap_interchange_rates", "one row per rate key per validity interval", "dbt_scd_id"),
        ("snap_rewards_rates", "one row per rewards key per validity interval", "dbt_scd_id"),
    ]),
    ("intermediate layer  -  int_*", [
        ("int_transaction_lifecycle", "one row per transaction", "transaction_id"),
        ("int_txn_rated", "one row per settled transaction  (settled subset only)", "transaction_id"),
        ("int_refund_matching", "one row per refund / dispute event", "refund_event_id"),
    ]),
    ("marts layer  -  dim_* / fct_*", [
        ("dim_company", "one row per company", "company_key  (surrogate)"),
        ("dim_card", "one row per card", "card_key  (surrogate)"),
        ("dim_merchant", "one row per merchant", "merchant_key  (surrogate)"),
        ("dim_date", "one row per calendar day", "date_day"),
        ("fct_transactions", "one row per transaction", "transaction_id"),
        ("fct_interchange_revenue", "one row per transaction per settlement day", "transaction_id, settlement_day"),
        ("fct_revenue_adjustments", "one row per prior-period reversal booked", "adjustment_id"),
        ("recon_settlement", "one row per settlement date", "settlement_day"),
        ("recognized_revenue", "one row per accounting period (month)", "accounting_period"),
    ]),
]

total = 132
fig, ax = plt.subplots(figsize=(18, total / 6.4), dpi=170)
ax.set_xlim(0, 124)
ax.set_ylim(0, total)
ax.axis("off")
fig.patch.set_facecolor("white")

ax.text(0, total - 2, "Grain of every table  -  raw  ->  staging  ->  snapshots  ->  intermediate  ->  marts",
        fontsize=15, fontweight="bold", color=INK, va="top")
ax.text(0, total - 6, "grain = what exactly one row represents", fontsize=8.6, color=MUT, va="top")

y = total - 12
for label, rows in SECTIONS:
    y -= 3
    ax.text(2, y, label, fontsize=10.5, fontweight="bold", color=INK, va="top")
    ax.plot([2, 122], [y - 3.0, y - 3.0], color=EDGE, lw=0.8)
    y -= 6.5
    ax.text(2, y, "table", fontsize=7.4, family="monospace", color=MUT, va="top")
    ax.text(40, y, "grain", fontsize=7.4, family="monospace", color=MUT, va="top")
    ax.text(92, y, "grain key", fontsize=7.4, family="monospace", color=MUT, va="top")
    y -= 3.2
    for name, grain, key in rows:
        ax.text(2, y, name, fontsize=8.0, family="monospace", fontweight="bold", color=INK, va="top")
        ax.text(40, y, grain, fontsize=8.0, color=INK, va="top")
        ax.text(92, y, key, fontsize=7.3, family="monospace", color=MUT, va="top")
        y -= 3.0
    y -= 1.5

ax.set_ylim(y - 3, total)
fig.set_size_inches(18, (total - (y - 3)) / 6.4)
fig.savefig(OUT / "grain.jpg", dpi=170, bbox_inches="tight", facecolor="white", format="jpg")
plt.close(fig)
print("wrote", OUT / "grain.jpg")
