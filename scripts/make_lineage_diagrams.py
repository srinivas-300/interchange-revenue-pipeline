"""Render row-level lineage for one example transaction through every layer.

    python scripts/make_lineage_diagrams.py

Writes:
    docs/lineage_0_sources.jpg   every simulator feed, rows for this transaction
    docs/lineage_1_events.jpg    event stream -> one row per transaction
    docs/lineage_2_rating.jpg    as-of rate + FX + revenue math
    docs/lineage_3_close.jpg     daily aggregate -> reconcile to bank file
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

OUT = Path("docs")
OUT.mkdir(parents=True, exist_ok=True)

INK = "#2B2B2A"
MUT = "#5F5E5A"
EDGE = "#7A7A76"
HEAD = "#E6E4DB"
HIFC = "#FBEBCB"
RH = 3.0
FS = 7.2


def _table(ax, x, y, headers, rows, widths, title, grain, hi):
    ax.text(x, y, title, fontsize=11.5, fontweight="bold", color=INK, va="bottom")
    ax.text(x, y - 2.0, grain, fontsize=8.6, style="italic", color=MUT, va="bottom")
    ytop = y - 2.9
    cx = x
    for h_, wd in zip(headers, widths):
        ax.add_patch(Rectangle((cx, ytop - RH), wd, RH, fc=HEAD, ec=EDGE, lw=0.6))
        ax.text(cx + 0.5, ytop - RH / 2, h_, fontsize=FS, family="monospace", color=INK, va="center")
        cx += wd
    for r, row in enumerate(rows):
        ry = ytop - RH * (r + 2)
        fc = HIFC if hi == r else "#FFFFFF"
        cx = x
        for v, wd in zip(row, widths):
            ax.add_patch(Rectangle((cx, ry), wd, RH, fc=fc, ec=EDGE, lw=0.6))
            ax.text(cx + 0.5, ry + RH / 2, str(v), fontsize=FS, family="monospace", color=INK, va="center")
            cx += wd
    return ytop - RH * (len(rows) + 1)


class Stack:
    def __init__(self, ax, top, right=118):
        self.ax = ax
        self.y = top
        self.right = right

    def table(self, headers, rows, widths, title, grain, caption=None, hi=None):
        self.y = _table(self.ax, 2, self.y, headers, rows, widths, title, grain, hi)
        if caption:
            self.ax.text(2, self.y - 1.4, caption, fontsize=8.1, style="italic", color=MUT, va="top")
            self.y -= 5.4

    def section(self, label):
        self.y -= 2
        self.ax.text(2, self.y, label, fontsize=12.5, fontweight="bold", color=INK, va="top")
        self.ax.plot([2, self.right], [self.y - 2.6, self.y - 2.6], color=EDGE, lw=0.8)
        self.y -= 5.5

    def arrow(self, label):
        y1, y2 = self.y - 1.4, self.y - 6.4
        self.ax.add_patch(FancyArrowPatch((16, y1), (16, y2), arrowstyle="-|>",
                                          mutation_scale=17, lw=1.3, color="#6F6F6F"))
        self.ax.text(20, (y1 + y2) / 2, label, fontsize=8.4, style="italic", color=INK, va="center")
        self.y = y2 - 1.6

    def gap(self, n):
        self.y -= n

    def note(self, text):
        self.ax.text(2, self.y, text, fontsize=8.7, color=MUT, va="top")


def make(name, total, title, sub, build, right=100):
    fig, ax = plt.subplots(figsize=(16 * right / 100, total / 6.4), dpi=170)
    ax.set_xlim(0, right)
    ax.set_ylim(0, total)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.text(0, total - 2, title, fontsize=15, fontweight="bold", color=INK, va="top")
    if sub:
        ax.text(0, total - 6, sub, fontsize=9, color=MUT, va="top")
    build(Stack(ax, total - (12 if sub else 9), right - 4))
    fig.savefig(OUT / name, dpi=170, bbox_inches="tight", facecolor="white", format="jpg")
    plt.close(fig)
    print("wrote", OUT / name)


EV_H = ["event_id", "event_ts", "transaction_id", "event_type", "amt", "cur"]
EV_W = [14, 20, 18, 15, 9, 7]


def build0(s: Stack):
    s.section("Dimensions  (static)")
    s.table(["company_id", "company_name", "region", "onboarded_at"],
            [["C0007", "Northwind Trading Co", "NA", "2022-05-14"]],
            [12, 26, 9, 14], "companies", "1 row per company",
            caption="cards.company_id = companies.company_id ;  region NA is used in the interchange-rate lookup")
    s.table(["card_id", "company_id", "card_program", "issued_at", "status"],
            [["K000123", "C0007", "VISA_COMMERCIAL_PREMIUM", "2022-08-30", "active"]],
            [11, 12, 26, 13, 9], "cards", "1 row per card",
            caption="card_events.card_id = cards.card_id ;  card_program PREMIUM adds +15 bps")
    s.table(["merchant_id", "merchant_name", "mcc", "merchant_country", "descriptor"],
            [["M00077", "BLUE HARBOR BISTRO", "5812", "US", "SQ *BLUE HARBOR BISTR"]],
            [13, 22, 7, 17, 24], "merchants", "1 row per merchant",
            caption="card_events.merchant_id = merchants.merchant_id ;  mcc 5812 = restaurants")

    s.section("Rate tables  (effective-dated)")
    s.table(["mcc", "card_program", "region", "bps", "valid_from", "valid_to"],
            [["5812", "VISA_COMMERCIAL_PREMIUM", "NA", "225.0", "2024-01-01", "2024-02-15"],
             ["5812", "VISA_COMMERCIAL_PREMIUM", "NA", "219.0", "2024-02-15", "(null)"]],
            [8, 26, 9, 8, 13, 13], "interchange_rates",
            "emitted for every mcc x card_program x region ;  shown: the slice for this transaction",
            caption="as-of: pick the row whose [valid_from, valid_to) contains settled_at 2024-02-10  ->  225.0 bps", hi=0)
    s.table(["spend_category", "cashback_pct", "valid_from", "valid_to"],
            [["restaurants", "0.0120", "2024-01-01", "2024-02-15"],
             ["restaurants", "0.0126", "2024-02-15", "(null)"]],
            [16, 14, 13, 13], "rewards_rates", "keyed by spend_category (derived from mcc)",
            caption="same as-of rule on settled_at  ->  cashback_pct 0.0120", hi=0)
    s.table(["currency", "rate_date", "usd_rate"],
            [["EUR", "2024-02-08", "1.081900"],
             ["EUR", "2024-02-09", "1.082500"],
             ["EUR", "2024-02-10", "1.083200"],
             ["EUR", "2024-02-11", "1.082800"]],
            [10, 13, 11], "fx_rates", "1 row per currency x date  (USD always 1.0)",
            caption="keyed by (currency, rate_date) ;  EUR on the settlement date 2024-02-10 = 1.0832", hi=2)

    s.section("Event feeds  (date-partitioned)")
    s.table(["event_id", "event_ts", "ingested_at", "txn_id", "card_id", "merch_id", "mcc",
             "event_type", "amt", "cur", "orig_txn"],
            [["E000000512", "2024-02-08 14:03:07", "2024-02-08 15:41", "T000000042", "K000123", "M00077", "5812", "authorization", "120.00", "EUR", "(null)"],
             ["E000000518", "2024-02-08 14:20:55", "2024-02-08 16:02", "T000000042", "K000123", "M00077", "5812", "auth_reversal", "20.00", "EUR", "(null)"],
             ["E000000544", "2024-02-09 09:41:12", "2024-02-09 11:20", "T000000042", "K000123", "M00077", "5812", "clearing", "60.00", "EUR", "(null)"],
             ["E000000544", "2024-02-09 09:41:12", "2024-02-09 11:20", "T000000042", "K000123", "M00077", "5812", "clearing", "60.00", "EUR", "(null)"],
             ["E000000701", "2024-02-10 02:20:39", "2024-02-11 03:05", "T000000042", "K000123", "M00077", "5812", "clearing", "40.00", "EUR", "(null)"],
             ["E000000731", "2024-02-10 06:12:48", "2024-02-10 07:44", "T000000042", "K000123", "M00077", "5812", "settlement", "100.00", "EUR", "(null)"]],
            [13, 18, 16, 12, 9, 10, 6, 13, 8, 5, 10], "card_events",
            "the only per-transaction feed  -  >= 1 row per lifecycle event",
            caption="row 4 = exact duplicate of row 3 ;  row 5 arrives a day late (ingested_at 2024-02-11) ;  no refund/dispute in this window",
            hi=3)
    s.table(["settlement_date", "file_id", "total_settled_amount_usd", "total_txn_count"],
            [["2024-02-10", "NET-20240210", "2,214,905.77", "1,842"]],
            [16, 16, 26, 17], "network_settlement", "1 row per settlement day  (the bank's file)",
            caption="reconciliation sums settled USD for 2024-02-10 from the marts and checks it against total_settled_amount_usd")


def build1(s: Stack):
    s.table(EV_H, [
        ["E000000731", "2024-02-10 06:12", "T000000042", "settlement", "100.00", "EUR"],
        ["E000000544", "2024-02-09 09:41", "T000000042", "clearing", "60.00", "EUR"],
        ["E000000544", "2024-02-09 09:41", "T000000042", "clearing", "60.00", "EUR"],
        ["E000000512", "2024-02-08 14:03", "T000000042", "authorization", "120.00", "EUR"],
        ["E000000701", "2024-02-10 02:20", "T000000042", "clearing", "40.00", "EUR"],
        ["E000000518", "2024-02-08 14:20", "T000000042", "auth_reversal", "20.00", "EUR"],
    ], EV_W, "raw.sim.card_events",
        ">= 1 row per lifecycle event  -  unordered  -  ~1% duplicate rows (highlighted)", hi=2)
    s.arrow("dedupe on event_id  -  cast types  -  order by event_ts")
    s.table(EV_H, [
        ["E000000512", "2024-02-08 14:03:07", "T000000042", "authorization", "120.00", "EUR"],
        ["E000000518", "2024-02-08 14:20:55", "T000000042", "auth_reversal", "20.00", "EUR"],
        ["E000000544", "2024-02-09 09:41:12", "T000000042", "clearing", "60.00", "EUR"],
        ["E000000701", "2024-02-10 02:20:39", "T000000042", "clearing", "40.00", "EUR"],
        ["E000000731", "2024-02-10 06:12:48", "T000000042", "settlement", "100.00", "EUR"],
    ], EV_W, "staging.stg_card_events", "1 row per event  -  deduped  -  typed  -  ordered")
    s.arrow("group by transaction_id: first auth | sum reversals | sum clearings | max(settlement)")
    s.table(
        ["transaction_id", "card_id", "status", "auth_amt", "rev_amt", "clr_amt", "settled_amt", "settled_at", "n_evt"],
        [["T000000042", "K000123", "settled", "120.00", "20.00", "100.00", "100.00", "2024-02-10", "5"]],
        [17, 11, 10, 9, 8, 8, 11, 12, 6],
        "intermediate.int_transaction_lifecycle", "exactly 1 row per transaction_id",
        caption="cleared_amt = auth 120.00 - reversal 20.00 ;  settled_at = max settlement event date")


def build2(s: Stack):
    s.table(["transaction_id", "mcc", "card_program", "region", "cur", "settled_amt", "settled_at"],
            [["T000000042", "5812", "VISA_COMMERCIAL_PREMIUM", "NA", "EUR", "100.00", "2024-02-10"]],
            [17, 7, 24, 8, 6, 12, 13], "in:  intermediate.int_transaction_lifecycle", "1 row per transaction")
    s.gap(3)
    s.table(["mcc", "card_program", "region", "bps", "valid_from", "valid_to"],
            [["5812", "..PREMIUM", "NA", "225.0", "2024-01-01", "2024-02-15"],
             ["5812", "..PREMIUM", "NA", "219.0", "2024-02-15", "(null)"]],
            [8, 14, 9, 8, 13, 13], "snapshots.interchange_rates  (SCD2)",
            "effective-dated history of the rate table",
            caption="as-of join: settled_at 2024-02-10 falls in [2024-01-01, 2024-02-15)  ->  bps 225.0  (row 1, not 219.0)",
            hi=0)
    s.gap(2)
    s.table(["cur", "rate_date", "usd_rate"], [["EUR", "2024-02-10", "1.0832"]], [7, 13, 11],
            "stg_fx_rates", "1 row per currency x date")
    s.gap(2)
    s.table(["spend_category", "cashback_pct", "valid_from", "valid_to"],
            [["restaurants", "0.0120", "2024-01-01", "2024-02-15"],
             ["restaurants", "0.0126", "2024-02-15", "(null)"]], [16, 13, 13, 13],
            "stg_rewards_rates", "effective-dated cashback rate",
            caption="as-of on settled_at 2024-02-10  ->  cashback_pct 0.0120", hi=0)
    s.arrow("multiply in: FX rate, bps, cashback %")
    s.table(["transaction_id", "settled_amt", "fx_usd", "settled_usd", "bps", "gross_usd", "fee_usd", "rewards_usd"],
            [["T000000042", "100.00", "1.0832", "108.32", "225.0", "2.44", "0.15", "1.30"]],
            [17, 12, 9, 12, 8, 11, 10, 12],
            "intermediate.int_txn_rated", "1 row per transaction  -  + rate, FX, USD amounts",
            caption="settled_usd 108.32 = 100.00 x 1.0832    gross_usd 2.44 = 108.32 x 2.25%    rewards_usd 1.30 = 108.32 x 1.20%")
    s.arrow("net = gross - fee - rewards")
    s.table(["transaction_id", "settlement_day", "acct_period", "settled_usd", "gross_usd", "fee_usd", "rewards_usd", "net_usd"],
            [["T000000042", "2024-02-10", "2024-02", "108.32", "2.44", "0.15", "1.30", "0.99"]],
            [16, 14, 11, 12, 10, 9, 12, 9],
            "marts.fct_interchange_revenue", "1 row per transaction x settlement_day",
            caption="net_usd 0.99 = 2.44 - 0.15 - 1.30 ;  accounting_period derived from settlement_day")


def build3(s: Stack):
    s.table(["transaction_id", "settlement_day", "settled_usd", "gross_usd", "fee_usd", "rewards_usd", "net_usd"],
            [["T000000042", "2024-02-10", "108.32", "2.44", "0.15", "1.30", "0.99"],
             ["T000000043", "2024-02-10", "512.90", "11.05", "0.28", "6.15", "4.62"],
             ["T000000051", "2024-02-10", "88.10", "1.94", "0.12", "1.06", "0.76"],
             ["...", "...", "...", "...", "...", "...", "..."]],
            [17, 15, 13, 12, 10, 13, 11],
            "marts.fct_interchange_revenue", "1 row per transaction x settlement_day  (1,842 rows for 2024-02-10)")
    s.arrow("group by settlement_day: count(*), sum(settled_usd), sum(gross_usd), sum(net_usd)")
    s.table(["settlement_day", "txn_count", "settled_usd", "gross_usd", "net_usd"],
            [["2024-02-10", "1,842", "2,214,905.77", "48,127.44", "21,004.10"]],
            [15, 11, 16, 14, 14], "daily rollup  (inside recon_settlement)", "1 row per settlement_day")
    s.gap(3)
    s.table(["settlement_date", "file_id", "total_settled_usd", "total_txn_count"],
            [["2024-02-10", "NET-20240210", "2,214,905.77", "1,842"]],
            [16, 16, 19, 17], "raw.sim.network_settlement", "the bank's file  -  1 row per day")
    s.arrow("join on settlement_day: variance = internal - file")
    s.table(["settlement_day", "internal_usd", "file_usd", "variance_usd", "variance_pct", "status"],
            [["2024-02-10", "2,214,905.77", "2,214,905.77", "0.00", "0.000%", "ok"]],
            [15, 15, 15, 14, 13, 9],
            "marts.recon_settlement", "1 row per settlement_day",
            caption="variance 0.00 within tolerance  ->  status ok")
    s.gap(4)
    s.note("|variance| over tolerance  ->  recon_close DAG fails: nothing published, period stays open.\n"
           "refund / dispute landing in a LOCKED period  ->  new row in fct_revenue_adjustments,\n"
           "dated in the current open period (the locked month is never rewritten).")


make("lineage_0_sources.jpg", 178,
     "0 . every simulator source feed  -  rows for transaction T000000042",
     "EUR 120.00 restaurant charge on card K000123 (company C0007) at merchant M00077, settled 2024-02-10",
     build0, right=124)
make("lineage_1_events.jpg", 96,
     "1 . event stream  ->  one row per transaction",
     "example: transaction T000000042  -  EUR 120.00 restaurant charge, partially cleared, settled 2024-02-10",
     build1)
make("lineage_2_rating.jpg", 124,
     "2 . rate as of the settlement date, convert to USD, compute revenue", None, build2)
make("lineage_3_close.jpg", 104,
     "3 . daily close  -  aggregate, then reconcile to the bank file", None, build3)
