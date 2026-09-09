"""Render the full pipeline architecture to a single JPEG.

    python scripts/make_architecture_diagram.py

Writes docs/architecture.jpg
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path("docs/architecture.jpg")
OUT.parent.mkdir(parents=True, exist_ok=True)

FILL = {
    "src": "#EEEDFE",
    "raw": "#E6F1FB",
    "dbt": "#E1F5EE",
    "mart": "#E6F1FB",
    "close": "#FAECE7",
    "band": "#F1EFE8",
}
EDGE = "#5F5E5A"
INK = "#2B2B2A"

fig, ax = plt.subplots(figsize=(19, 11), dpi=170)
ax.set_xlim(0, 186)
ax.set_ylim(0, 122)
ax.axis("off")
fig.patch.set_facecolor("white")


def box(x, y, w, h, title, lines, fc):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.02,rounding_size=1.4",
            linewidth=0.9, edgecolor=EDGE, facecolor=fc,
        )
    )
    ax.text(x + w / 2, y + h - 2.6, title, ha="center", va="top",
            fontsize=11.5, fontweight="bold", color=INK)
    for i, ln in enumerate(lines):
        ax.text(x + 1.8, y + h - 7.4 - i * 3.15, ln, ha="left", va="top",
                fontsize=8.3, color=INK)


def harrow(x1, x2, y):
    ax.add_patch(FancyArrowPatch((x1, y), (x2, y), arrowstyle="-|>",
                                 mutation_scale=16, lw=1.2, color="#6F6F6F"))


def varrow(x, y1, y2):
    ax.add_patch(FancyArrowPatch((x, y1), (x, y2), arrowstyle="-|>",
                                 mutation_scale=11, lw=1.0, color="#9A9A96"))


ax.text(3, 119.5, "Interchange revenue recognition  ·  Airflow · dbt · Snowflake",
        ha="left", va="top", fontsize=16, fontweight="bold", color=INK)
ax.text(3, 114.5,
        "card event stream  →  recognized daily interchange revenue, reconciled to the "
        "network settlement file, immutable once the accounting period is locked",
        ha="left", va="top", fontsize=9.5, color="#5F5E5A")

W, GAP, X0, TOP, H = 27.0, 3.6, 3.0, 108.0, 74.0
xs = [X0 + i * (W + GAP) for i in range(6)]
Y = TOP - H

box(xs[0], Y, W, H, "1 · simulator", [
    "deterministic, seeded (--seed)",
    "",
    "Dimensions",
    "  companies, cards, merchants",
    "  (messy descriptors)",
    "Rate tables (effective-dated)",
    "  interchange_rates",
    "  rewards_rates, fx_rates",
    "Event feeds",
    "  card_events:",
    "   auth->reversal->clearing",
    "   ->settlement->refund->dispute",
    "  network_settlement (bank truth)",
    "",
    "mess: 1% dupes, out-of-order,",
    "3% late, 20% refunds unlinked",
    "-> data/landing/ Parquet, dt=",
], FILL["src"])

box(xs[1], Y, W, H, "2 · ingest_raw", [
    "Airflow DAG",
    "",
    "PUT files -> internal stage",
    "COPY INTO raw.sim.*",
    "skip already-loaded files",
    "MERGE where correctable",
    "",
    "raw.sim.* tables",
    "  + _loaded_at",
    "  + _batch_id",
    "  + _source_file",
    "  append-only, replayable",
    "",
    "warehouse: INGEST_WH",
], FILL["raw"])

box(xs[2], Y, W, H, "3 · staging (stg_)", [
    "views  ·  1 row per event",
    "",
    "stg_card_events",
    "  dedupe on event_id",
    "stg_interchange_rates",
    "stg_rewards_rates",
    "stg_fx_rates",
    "stg_companies / cards /",
    "  merchants",
    "",
    "enforced contracts",
    "source freshness checks",
], FILL["dbt"])

box(xs[3], Y, W, H, "4 · intermediate (int_)", [
    "views  ·  core logic",
    "",
    "int_transaction_lifecycle",
    "  event stream -> 1 row per",
    "  transaction_id (status,",
    "  settled_amount, settled_at)",
    "int_txn_rated",
    "  as-of join to SCD2 rate",
    "  on settled_at; FX -> USD",
    "int_refund_matching",
    "  link refunds / disputes,",
    "  confidence, unmatched bucket",
], FILL["dbt"])

box(xs[4], Y, W, H, "5 · marts", [
    "tables",
    "",
    "fct_transactions",
    "  1 row / transaction",
    "fct_interchange_revenue",
    "  grain: txn x settlement_day",
    "  gross_interchange_usd",
    "  network_fee_usd",
    "  rewards_accrued_usd",
    "  net_interchange_usd",
    "  accounting_period",
    "dim_merchant / card /",
    "  company / date",
    "snapshots/  (SCD2 rates)",
], FILL["mart"])

box(xs[5], Y, W, H, "6 · close & serving", [
    "recon_settlement",
    "  internal vs network file",
    "  variance: timing vs break",
    "  over tolerance -> fail run",
    "accounting_periods (open/lock)",
    "fct_revenue_adjustments",
    "  locked-period reversals ->",
    "  current open period",
    "recognized_revenue",
    "close_package",
    "  recognized/accrued/pending",
    "exposures -> board metrics,",
    "dbt docs site",
], FILL["close"])

for i in range(5):
    harrow(xs[i] + W, xs[i + 1], Y + H / 2)

BX, BY, BW, BH = X0, 20.0, xs[5] + W - X0, 13.0
ax.add_patch(FancyBboxPatch((BX, BY), BW, BH,
             boxstyle="round,pad=0.02,rounding_size=1.4",
             linewidth=0.9, edgecolor=EDGE, facecolor=FILL["band"]))
ax.text(BX + BW / 2, BY + BH - 3.0,
        "Airflow (Astronomer Astro)  —  DAGs chained by datasets",
        ha="center", va="top", fontsize=10.5, fontweight="bold", color=INK)
ax.text(BX + BW / 2, BY + BH - 7.6,
        "gen_events  ->  ingest_raw  ->  transform_dbt (Cosmos: one task per model + test)  ->  "
        "recon_close (recon -> approval gate -> lock period)      |woven|      "
        "backfill DAG: idempotent MERGE, refuses locked periods".replace("|woven|", "  "),
        ha="center", va="top", fontsize=8.6, color=INK)
for x in xs:
    varrow(x + W / 2, BY + BH, Y - 0.5)

FX, FY, FW, FH = X0, 4.0, xs[5] + W - X0, 13.0
ax.add_patch(FancyBboxPatch((FX, FY), FW, FH,
             boxstyle="round,pad=0.02,rounding_size=1.4",
             linewidth=0.9, edgecolor=EDGE, facecolor="white"))
ax.text(FX + 2.0, FY + FH - 3.0,
        "Snowflake:  INGEST_WH / TRANSFORM_WH / CI_WH  (XS, auto-suspend 60s)   ·   "
        "service user TYPE=SERVICE + RSA key pair   ·   role interchange_role   ·   "
        "DBs: INTERCHANGE_RAW, INTERCHANGE_ANALYTICS",
        ha="left", va="top", fontsize=8.4, color=INK)
ax.text(FX + 2.0, FY + FH - 8.0,
        "CI: GitHub Actions  —  sqlfluff + dbt build on CI_WH into a throwaway schema "
        "(state:modified+)     ·     Cost: model over SNOWFLAKE.ACCOUNT_USAGE     ·     "
        "secrets: .env / Airflow connections, never in git",
        ha="left", va="top", fontsize=8.4, color=INK)

fig.savefig(OUT, dpi=170, bbox_inches="tight", facecolor="white", format="jpg")
print(f"wrote {OUT.resolve()}")
