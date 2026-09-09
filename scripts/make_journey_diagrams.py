"""One sample transaction (T000000042) through every stage, table by table.

    python scripts/make_journey_diagrams.py

Writes docs/journey_1_raw.jpg .. journey_5_close.jpg
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
FS = 7.0
RIGHT = 150


def _table(ax, x, y, headers, rows, widths, title, grain, hi):
    ax.text(x, y, title, fontsize=11, fontweight="bold", color=INK, va="bottom")
    ax.text(x, y - 2.0, grain, fontsize=8.4, style="italic", color=MUT, va="bottom")
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
    if not rows:
        ax.add_patch(Rectangle((x, ytop - RH * 2), sum(widths), RH, fc="#F6F5F1", ec=EDGE, lw=0.6))
        ax.text(x + 1, ytop - RH * 1.5, "(no rows for this transaction)", fontsize=FS,
                style="italic", family="monospace", color=MUT, va="center")
        return ytop - RH * 2
    return ytop - RH * (len(rows) + 1)


class Stack:
    def __init__(self, ax, top):
        self.ax = ax
        self.y = top

    def table(self, headers, rows, widths, title, grain, caption=None, hi=None):
        bottom = _table(self.ax, 2, self.y, headers, rows, widths, title, grain, hi)
        self.y = bottom - 2.6
        if caption:
            self.ax.text(2, self.y, caption, fontsize=7.9, style="italic", color=MUT, va="top")
            self.y -= 4.0
        self.y -= 4.0

    def arrow(self, label):
        y1, y2 = self.y - 1.4, self.y - 6.2
        self.ax.add_patch(FancyArrowPatch((16, y1), (16, y2), arrowstyle="-|>",
                                          mutation_scale=16, lw=1.3, color="#6F6F6F"))
        self.ax.text(20, (y1 + y2) / 2, label, fontsize=8.2, style="italic", color=INK, va="center")
        self.y = y2 - 1.6

    def gap(self, n):
        self.y -= n

    def note(self, text):
        self.ax.text(2, self.y, text, fontsize=8.5, color=MUT, va="top")
        self.y -= 7


def make(name, total, title, sub, build):
    fig, ax = plt.subplots(figsize=(24, total / 6.4), dpi=160)
    ax.set_xlim(0, RIGHT)
    ax.set_ylim(0, total)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.text(0, total - 2, title, fontsize=15, fontweight="bold", color=INK, va="top")
    ax.text(0, total - 6, sub, fontsize=9, color=MUT, va="top")
    s = Stack(ax, total - 11)
    build(s)
    ax.set_ylim(s.y - 3, total)
    fig.set_size_inches(24, (total - (s.y - 3)) / 6.4)
    fig.savefig(OUT / name, dpi=160, bbox_inches="tight", facecolor="white", format="jpg")
    plt.close(fig)
    print("wrote", OUT / name)


# ---- shared example values -------------------------------------------------
EVH = ["event_id", "event_ts", "ingested_at", "transaction_id", "card_id", "merchant_id",
       "mcc", "event_type", "amount", "cur", "orig_txn"]
EVW = [13, 18, 16, 13, 9, 11, 6, 14, 8, 5, 10]
EV_RAW = [
    ["E000000731", "2024-02-10 06:12:48", "2024-02-10 07:44", "T000000042", "K000123", "M00077", "5812", "settlement", "100.00", "EUR", "(null)"],
    ["E000000544", "2024-02-09 09:41:12", "2024-02-09 11:20", "T000000042", "K000123", "M00077", "5812", "clearing", "60.00", "EUR", "(null)"],
    ["E000000544", "2024-02-09 09:41:12", "2024-02-09 11:20", "T000000042", "K000123", "M00077", "5812", "clearing", "60.00", "EUR", "(null)"],
    ["E000000512", "2024-02-08 14:03:07", "2024-02-08 15:41", "T000000042", "K000123", "M00077", "5812", "authorization", "120.00", "EUR", "(null)"],
    ["E000000701", "2024-02-10 02:20:39", "2024-02-11 03:05", "T000000042", "K000123", "M00077", "5812", "clearing", "40.00", "EUR", "(null)"],
    ["E000000518", "2024-02-08 14:20:55", "2024-02-08 16:02", "T000000042", "K000123", "M00077", "5812", "auth_reversal", "20.00", "EUR", "(null)"],
]
EV_STG = [
    ["E000000512", "2024-02-08 14:03:07", "2024-02-08 15:41", "T000000042", "K000123", "M00077", "5812", "authorization", "120.00", "EUR", "(null)"],
    ["E000000518", "2024-02-08 14:20:55", "2024-02-08 16:02", "T000000042", "K000123", "M00077", "5812", "auth_reversal", "20.00", "EUR", "(null)"],
    ["E000000544", "2024-02-09 09:41:12", "2024-02-09 11:20", "T000000042", "K000123", "M00077", "5812", "clearing", "60.00", "EUR", "(null)"],
    ["E000000701", "2024-02-10 02:20:39", "2024-02-11 03:05", "T000000042", "K000123", "M00077", "5812", "clearing", "40.00", "EUR", "(null)"],
    ["E000000731", "2024-02-10 06:12:48", "2024-02-10 07:44", "T000000042", "K000123", "M00077", "5812", "settlement", "100.00", "EUR", "(null)"],
]


def s1(s: Stack):
    s.table(EVH, EV_RAW, EVW, "raw.sim.card_events",
            "6 rows for this txn -- out of order, incl. 1 exact duplicate (rows 2 & 3) and 1 late arrival (row 5)",
            caption="also has _loaded_at / _batch_id / _source_file (audit); nothing is cleaned yet", hi=2)
    s.table(["card_id", "company_id", "card_program", "issued_at", "status"],
            [["K000123", "C0007", "VISA_COMMERCIAL_PREMIUM", "2022-08-30 00:00:00", "active"]],
            [11, 12, 26, 22, 9], "raw.sim.cards", "1 row per card")
    s.table(["company_id", "company_name", "region", "onboarded_at"],
            [["C0007", "Northwind Trading Co", "NA", "2022-05-14 00:00:00"]],
            [12, 24, 9, 22], "raw.sim.companies", "1 row per company")
    s.table(["merchant_id", "merchant_name", "mcc", "merchant_country", "descriptor"],
            [["M00077", "BLUE HARBOR BISTRO", "5812", "US", "SQ *BLUE HARBOR BISTR"]],
            [13, 22, 7, 17, 24], "raw.sim.merchants", "1 row per merchant")
    s.table(["mcc", "card_program", "region", "bps", "valid_from", "valid_to"],
            [["5812", "VISA_COMMERCIAL_PREMIUM", "NA", "225.0", "2024-01-01", "2024-02-15"],
             ["5812", "VISA_COMMERCIAL_PREMIUM", "NA", "219.0", "2024-02-15", "(null)"]],
            [8, 26, 9, 8, 13, 13], "raw.sim.interchange_rates", "2 versions cover this txn's mcc/program/region")
    s.table(["spend_category", "cashback_pct", "valid_from", "valid_to"],
            [["restaurants", "0.0120", "2024-01-01", "2024-02-15"],
             ["restaurants", "0.0126", "2024-02-15", "(null)"]],
            [16, 14, 13, 13], "raw.sim.rewards_rates", "2 versions for spend_category restaurants")
    s.table(["currency", "rate_date", "usd_rate"], [["EUR", "2024-02-10", "1.083200"]],
            [10, 13, 11], "raw.sim.fx_rates", "the row for this txn's currency x settlement date")
    s.table(["settlement_date", "file_id", "total_settled_amount_usd", "total_txn_count"],
            [["2024-02-10", "NET-20240210", "2,214,905.77", "1842"]],
            [16, 16, 26, 17], "raw.sim.network_settlement", "the bank's total for the settlement day")


def s2(s: Stack):
    s.note("what changed vs raw:  types are real, columns renamed to convention, the duplicate card_events row is gone, "
           "rows ordered by event_ts, enums validated.  Grain is unchanged.  Snapshots (SCD2) are new.")
    s.table(EVH, EV_STG, EVW, "staging.stg_card_events",
            "5 rows -- deduped on event_id, cast, ordered", hi=None)
    s.table(["card_id", "company_id", "card_program", "issued_at", "status"],
            [["K000123", "C0007", "VISA_COMMERCIAL_PREMIUM", "2022-08-30", "active"]],
            [11, 12, 26, 13, 9], "staging.stg_cards", "issued_at now DATE")
    s.table(["company_id", "company_name", "region", "onboarded_at"],
            [["C0007", "Northwind Trading Co", "NA", "2022-05-14"]],
            [12, 24, 9, 13], "staging.stg_companies", "region validated against the allowed set")
    s.table(["merchant_id", "merchant_name", "mcc", "merchant_country", "descriptor"],
            [["M00077", "BLUE HARBOR BISTRO", "5812", "US", "SQ *BLUE HARBOR BISTR"]],
            [13, 22, 7, 17, 24], "staging.stg_merchants", "descriptor kept as-is for later normalization")
    s.table(["mcc", "card_program", "region", "bps", "valid_from", "valid_to"],
            [["5812", "VISA_COMMERCIAL_PREMIUM", "NA", "225.0", "2024-01-01", "2024-02-15"],
             ["5812", "VISA_COMMERCIAL_PREMIUM", "NA", "219.0", "2024-02-15", "(null)"]],
            [8, 26, 9, 8, 13, 13], "staging.stg_interchange_rates", "typed, unique")
    s.table(["spend_category", "cashback_pct", "valid_from", "valid_to"],
            [["restaurants", "0.0120", "2024-01-01", "2024-02-15"],
             ["restaurants", "0.0126", "2024-02-15", "(null)"]],
            [16, 14, 13, 13], "staging.stg_rewards_rates", "typed, unique")
    s.table(["currency", "rate_date", "usd_rate"], [["EUR", "2024-02-10", "1.0832"]],
            [10, 13, 11], "staging.stg_fx_rates", "typed")
    s.table(["settlement_date", "file_id", "total_settled_amount_usd", "total_txn_count"],
            [["2024-02-10", "NET-20240210", "2214905.77", "1842"]],
            [16, 16, 24, 17], "staging.stg_network_settlement", "typed")
    s.gap(2)
    s.table(["mcc", "card_program", "region", "bps", "dbt_scd_id", "dbt_valid_from", "dbt_valid_to"],
            [["5812", "VISA_COMMERCIAL_PREMIUM", "NA", "225.0", "a1f3..e9", "2024-01-01 00:00", "2024-02-15 00:00"],
             ["5812", "VISA_COMMERCIAL_PREMIUM", "NA", "219.0", "b7c2..44", "2024-02-15 00:00", "(null)"]],
            [8, 26, 9, 8, 12, 18, 18], "snapshots.snap_interchange_rates",
            "SCD2 history -- the as-of join in the next stage reads this",
            caption="settled_at 2024-02-10 falls inside the first row's validity window  ->  bps 225.0", hi=0)
    s.table(["spend_category", "cashback_pct", "dbt_scd_id", "dbt_valid_from", "dbt_valid_to"],
            [["restaurants", "0.0120", "c9a1..02", "2024-01-01 00:00", "2024-02-15 00:00"],
             ["restaurants", "0.0126", "d4e8..71", "2024-02-15 00:00", "(null)"]],
            [16, 14, 12, 18, 18], "snapshots.snap_rewards_rates", "SCD2 history for cashback", hi=0)


def s3(s: Stack):
    s.note("the 5 event rows collapse to ONE row per transaction; then that row is rated (rate/FX/USD/revenue). "
           "int_refund_matching stays empty -- this transaction has no refund or dispute.")
    s.table(["transaction_id", "card_id", "merchant_id", "mcc", "cur", "first_auth_at", "current_status",
             "auth_amt", "rev_amt", "clr_amt", "settled_amt", "settled_at", "n_evt"],
            [["T000000042", "K000123", "M00077", "5812", "EUR", "2024-02-08 14:03:07", "settled",
              "120.00", "20.00", "100.00", "100.00", "2024-02-10", "5"]],
            [13, 9, 11, 6, 4, 18, 10, 8, 8, 8, 11, 11, 6],
            "intermediate.int_transaction_lifecycle", "exactly 1 row per transaction_id",
            caption="clr_amt = auth 120 - reversal 20 = 100 ;  status from the last event ;  n_evt counts the 5 deduped events")
    s.arrow("as-of join to snap_interchange_rates / snap_rewards_rates on settled_at ;  join stg_fx_rates ;  compute USD")
    s.table(["transaction_id", "settlement_day", "acct_period", "card_program", "region", "spend_category", "cur",
             "settled_amt", "fx_usd", "settled_usd", "bps", "cashback", "gross_usd", "fee_usd", "rewards_usd"],
            [["T000000042", "2024-02-10", "2024-02", "..PREMIUM", "NA", "restaurants", "EUR",
              "100.00", "1.0832", "108.32", "225.0", "0.0120", "2.44", "0.15", "1.30"]],
            [13, 12, 10, 10, 6, 12, 4, 9, 7, 10, 6, 8, 9, 7, 9],
            "intermediate.int_txn_rated", "1 row per settled transaction",
            caption="settled_usd = 100.00 x 1.0832 ;  gross = 108.32 x 2.25% ;  rewards = 108.32 x 1.20%")
    s.arrow("no matching refund / dispute event")
    s.table(["refund_event_id", "event_type", "refund_ts", "refund_amount", "matched_transaction_id", "match_method", "match_confidence"],
            [], [15, 12, 18, 13, 20, 14, 14], "intermediate.int_refund_matching", "1 row per refund/dispute event")


def s4(s: Stack):
    s.note("dimensions get surrogate keys; the transaction becomes two facts -- fct_transactions (per transaction) "
           "and fct_interchange_revenue (per transaction x settlement_day, carrying the revenue).")
    s.table(["company_key", "company_id", "company_name", "region", "onboarded_at"],
            [["7", "C0007", "Northwind Trading Co", "NA", "2022-05-14"]],
            [12, 11, 24, 9, 13], "marts.dim_company", "1 row per company")
    s.table(["card_key", "card_id", "company_key", "card_program", "issued_at", "status"],
            [["123", "K000123", "7", "VISA_COMMERCIAL_PREMIUM", "2022-08-30", "active"]],
            [9, 10, 12, 26, 13, 9], "marts.dim_card", "1 row per card")
    s.table(["merchant_key", "merchant_id", "merchant_name", "mcc", "spend_category", "merchant_country"],
            [["77", "M00077", "BLUE HARBOR BISTRO", "5812", "restaurants", "US"]],
            [13, 12, 22, 7, 15, 16], "marts.dim_merchant", "1 row per merchant")
    s.table(["date_day", "year", "quarter", "month", "accounting_period", "is_month_end"],
            [["2024-02-10", "2024", "1", "2", "2024-02", "FALSE"]],
            [12, 8, 9, 8, 18, 13], "marts.dim_date", "1 row per calendar day")
    s.table(["transaction_id", "card_key", "merchant_key", "company_key", "first_auth_date", "settled_at",
             "current_status", "cur", "auth_amt", "settled_amt", "settled_usd"],
            [["T000000042", "123", "77", "7", "2024-02-08", "2024-02-10", "settled", "EUR", "120.00", "100.00", "108.32"]],
            [13, 9, 11, 11, 14, 11, 13, 4, 9, 10, 10], "marts.fct_transactions", "1 row per transaction")
    s.table(["transaction_id", "settlement_day", "acct_period", "card_key", "merchant_key", "company_key",
             "settled_usd", "gross_usd", "fee_usd", "rewards_usd", "net_usd", "is_recognized"],
            [["T000000042", "2024-02-10", "2024-02", "123", "77", "7", "108.32", "2.44", "0.15", "1.30", "0.99", "FALSE"]],
            [13, 13, 10, 8, 11, 10, 10, 9, 7, 10, 8, 11],
            "marts.fct_interchange_revenue", "1 row per transaction x settlement_day",
            caption="net_usd = gross 2.44 - fee 0.15 - rewards 1.30 = 0.99 ;  is_recognized = FALSE while 2024-02 is open")


def s5(s: Stack):
    s.note("the transaction's revenue row is now aggregated with the day's other 1,841 rows and reconciled to the bank file; "
           "the month total sits in recognized_revenue until the period locks.")
    s.table(["transaction_id", "settlement_day", "settled_usd", "gross_usd", "net_usd"],
            [["T000000042", "2024-02-10", "108.32", "2.44", "0.99"],
             ["T000000043", "2024-02-10", "512.90", "11.05", "4.62"],
             ["...  (1,842 rows)", "2024-02-10", "...", "...", "..."]],
            [18, 14, 12, 11, 10], "marts.fct_interchange_revenue  (day slice)", "grain: transaction x settlement_day")
    s.arrow("group by settlement_day ;  join stg_network_settlement")
    s.table(["settlement_day", "internal_settled_usd", "file_settled_usd", "variance_usd", "variance_pct",
             "variance_class", "internal_txn_count", "file_txn_count", "status"],
            [["2024-02-10", "2,214,905.77", "2,214,905.77", "0.00", "0.00000", "ok", "1842", "1842", "ok"]],
            [14, 20, 18, 13, 13, 14, 18, 15, 8],
            "marts.recon_settlement", "1 row per settlement_day",
            caption="variance within tolerance  ->  status ok ;  over tolerance would fail recon_close and block the publish")
    s.arrow("sum net_interchange_usd for accounting_period = 2024-02")
    s.table(["accounting_period", "period_status", "recognized_net_usd", "accrued_net_usd", "pending_net_usd",
             "adjustments_usd", "locked_at"],
            [["2024-02", "open", "0.00", "184,502.11", "12,904.67", "0.00", "(null)"]],
            [16, 13, 18, 16, 15, 15, 13],
            "marts.recognized_revenue", "1 row per accounting period",
            caption="while open: settled revenue sits in accrued ;  on lock it moves to recognized and locked_at is set ;  "
                    "T000000042's 0.99 is part of accrued_net_usd")


make("journey_1_raw.jpg", 175, "T000000042 . stage 1 -- raw   (raw.sim.*)",
     "landed exactly as delivered: loose types, source names, duplicates and out-of-order rows kept", s1)
make("journey_2_staging.jpg", 210, "T000000042 . stage 2 -- staging + snapshots   (stg_* , snap_*)",
     "typed, renamed, de-duplicated, contract-checked; same grain. SCD2 snapshots capture rate history", s2)
make("journey_3_intermediate.jpg", 92, "T000000042 . stage 3 -- intermediate   (int_*)",
     "the event stream is collapsed to one row per transaction, then rated into revenue", s3)
make("journey_4_marts.jpg", 120, "T000000042 . stage 4 -- marts   (dim_* , fct_*)",
     "star schema: surrogate keys on the dimensions, the transaction split into two fact tables", s4)
make("journey_5_close.jpg", 104, "T000000042 . stage 5 -- reconcile & close   (recon_settlement , recognized_revenue)",
     "aggregate to the day, reconcile to the bank file, roll up to the month", s5)
