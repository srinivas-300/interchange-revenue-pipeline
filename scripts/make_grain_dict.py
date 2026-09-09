"""Data dictionary: grain + why-it-exists + column notes for every table.

    python scripts/make_grain_dict.py

Writes docs/grain_dict_1.jpg (raw / staging / snapshots)
       docs/grain_dict_2.jpg (intermediate / marts)
"""

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("docs")
OUT.mkdir(parents=True, exist_ok=True)

INK = "#2B2B2A"
MUT = "#5F5E5A"
EDGE = "#7A7A76"
RULE = "#DBD7CD"

LH = 2.35
WRAP_WHY = 92
WRAP_COL = 132


def render(fname, total, title, groups):
    fig, ax = plt.subplots(figsize=(24, total / 6.4), dpi=160)
    ax.set_xlim(0, 210)
    ax.set_ylim(0, total)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(0, total - 2, title, fontsize=15, fontweight="bold", color=INK, va="top")
    ax.text(0, total - 6, "grain = what one row is   |   why = reason the table exists   |   columns = what the fields carry",
            fontsize=8.4, color=MUT, va="top")

    y = total - 13
    for section, rows in groups:
        y -= 3
        ax.text(2, y, section, fontsize=11, fontweight="bold", color=INK, va="top")
        ax.plot([2, 207], [y - 3.0, y - 3.0], color=EDGE, lw=0.9)
        y -= 7
        ax.text(2, y, "table", fontsize=7.0, family="monospace", color=MUT, va="top")
        ax.text(42, y, "why", fontsize=7.0, family="monospace", color=MUT, va="top")
        ax.text(112, y, "columns", fontsize=7.0, family="monospace", color=MUT, va="top")
        y -= 3.4
        for name, grain, key, why, cols in rows:
            why_lines = textwrap.wrap(why, WRAP_WHY)
            col_lines = textwrap.wrap(cols, WRAP_COL)
            n = max(3, len(why_lines), len(col_lines))
            ax.text(2, y, name, fontsize=7.6, family="monospace", fontweight="bold", color=INK, va="top")
            ax.text(2, y - 2.5, "grain: " + grain, fontsize=6.1, family="monospace", color=MUT, va="top")
            ax.text(2, y - 4.8, "key: " + key, fontsize=6.1, family="monospace", color=MUT, va="top")
            for i, ln in enumerate(why_lines):
                ax.text(42, y - i * LH, ln, fontsize=6.7, color=INK, va="top")
            for i, ln in enumerate(col_lines):
                ax.text(112, y - i * LH, ln, fontsize=6.5, color=MUT, va="top")
            y -= n * LH + 2.4
            ax.plot([2, 207], [y + 1.0, y + 1.0], color=RULE, lw=0.5)
        y -= 2

    ax.set_ylim(y - 3, total)
    fig.set_size_inches(24, (total - (y - 3)) / 6.4)
    fig.savefig(OUT / fname, dpi=160, bbox_inches="tight", facecolor="white", format="jpg")
    plt.close(fig)
    print("wrote", OUT / fname)


AUDIT = "  Plus _loaded_at / _batch_id / _source_file: audit trail of which load put the row here."

RAW = ("raw layer  -  raw.sim.*   (landed exactly as delivered; append-only; duplicates kept)", [
    ("card_events", "one row per card lifecycle event", "event_id (not unique)",
     "The immutable copy of the card event stream. Everything downstream is rebuilt from this, so it is never edited.",
     "event_id; event_ts = when it happened, ingested_at = when it reached us (can lag); transaction_id groups the events of one purchase; card_id / merchant_id / mcc = who and where; event_type (authorization..dispute); amount + currency; original_transaction_id links a refund to its charge (often null)." + AUDIT),
    ("interchange_rates", "one row per rate version", "mcc, card_program, region, valid_from",
     "The basis-point fee schedule Ramp earns. Rates change over time, so each version is a separate row.",
     "mcc + card_program + region identify which rate; bps is the rate; valid_from / valid_to bound the period it applies (valid_to null = still current)." + AUDIT),
    ("rewards_rates", "one row per cashback-rate version", "spend_category, valid_from",
     "Cashback % by spend category. Used to accrue the rewards liability that is netted out of gross interchange.",
     "spend_category; cashback_pct; valid_from / valid_to bound the version." + AUDIT),
    ("fx_rates", "one row per currency per day", "currency, rate_date",
     "Daily exchange rates so non-USD settlements can be converted to USD on their settlement date.",
     "currency; rate_date; usd_rate = USD value of one unit (USD row is always 1.0)." + AUDIT),
    ("network_settlement", "one row per settlement date", "settlement_date",
     "The card network's own daily total. This is the external 'truth' the reconciliation step checks the internal numbers against.",
     "settlement_date; file_id; total_settled_amount_usd; total_txn_count." + AUDIT),
    ("companies", "one row per company", "company_id",
     "The customer businesses that hold Ramp cards.",
     "company_id; company_name; region (feeds the interchange-rate lookup); onboarded_at." + AUDIT),
    ("cards", "one row per card", "card_id",
     "Links each card to its company and its pricing tier.",
     "card_id; company_id; card_program (standard / premium -> different bps); issued_at; status." + AUDIT),
    ("merchants", "one row per merchant", "merchant_id",
     "Where spend happens. Supplies the mcc (drives rate + category) and a deliberately messy descriptor for the normalization exercise.",
     "merchant_id; merchant_name; mcc; merchant_country; descriptor (raw text like 'SQ *BLUE HARBOR')." + AUDIT),
])

STG = ("staging layer  -  stg_*   (typed, renamed, de-duplicated, contract-enforced; same grain as the source)", [
    ("stg_card_events", "one row per card lifecycle event", "event_id (unique)",
     "The trustworthy version of card_events that every model builds on: real types, clean names, duplicates removed, schema pinned by a contract.",
     "Same business columns as raw, cast to proper types; deduped with qualify row_number() on event_id; event_type restricted to the 6 valid values; amount >= 0; currency is 3 chars; loaded_at kept for lineage."),
    ("stg_interchange_rates", "one row per rate version", "mcc, card_program, region, valid_from",
     "Typed, unique rate schedule ready for the as-of join.",
     "mcc / card_program / region / valid_from as the key; bps; valid_to nullable."),
    ("stg_rewards_rates", "one row per cashback-rate version", "spend_category, valid_from",
     "Typed cashback schedule.",
     "spend_category / valid_from key; cashback_pct; valid_to nullable."),
    ("stg_fx_rates", "one row per currency per day", "currency, rate_date",
     "Typed FX table for USD conversion.",
     "currency / rate_date key; usd_rate."),
    ("stg_network_settlement", "one row per settlement date", "settlement_date",
     "Typed bank file for the reconciliation join.",
     "settlement_date key; file_id; total_settled_amount_usd; total_txn_count."),
    ("stg_companies", "one row per company", "company_id",
     "Cleaned company dimension source; region validated against the allowed set.",
     "company_id; company_name; region [enum]; onboarded_at cast to date."),
    ("stg_cards", "one row per card", "card_id",
     "Cleaned card dimension source with the company link.",
     "card_id; company_id (FK companies); card_program [enum]; issued_at (date); status."),
    ("stg_merchants", "one row per merchant", "merchant_id",
     "Cleaned merchant dimension source.",
     "merchant_id; merchant_name; mcc; merchant_country (2 chars); descriptor kept as-is for later normalization."),
])

SNP = ("snapshots  -  dbt SCD2   (grain changes: natural key x validity interval)", [
    ("snap_interchange_rates", "one row per rate key per validity interval", "dbt_scd_id",
     "dbt records every historical version of the rate table so a transaction can be priced with the rate that was in effect on its settlement date, even after the rate later changes.",
     "The source rate columns as they stood when captured; dbt_scd_id (surrogate); dbt_valid_from / dbt_valid_to = when this version was live; dbt_updated_at."),
    ("snap_rewards_rates", "one row per rewards key per validity interval", "dbt_scd_id",
     "Same idea for the cashback rates: preserves each version so accruals use the rate in force at settlement.",
     "spend_category, cashback_pct at capture time; dbt_scd_id; dbt_valid_from / dbt_valid_to; dbt_updated_at."),
])

INT = ("intermediate layer  -  int_*   (the joins and business logic)", [
    ("int_transaction_lifecycle", "one row per transaction", "transaction_id",
     "Collapses the multi-row event stream into one authoritative row per purchase with its current state and final amounts. Every fact table joins back to this.",
     "transaction_id; card_id / merchant_id / mcc / currency carried from the events; first_auth_at; current_status (authorized / expired / settled / refunded / disputed); authorized_amount, reversed_amount, cleared_amount, settled_amount derived by walking the events in order; settled_at; n_events."),
    ("int_txn_rated", "one row per settled transaction", "transaction_id",
     "Takes each settled transaction, attaches the correct rate / FX / cashback %, and computes the money. This is where volume becomes revenue.",
     "transaction_id (FK lifecycle); settlement_day + accounting_period; card_program / region / spend_category = join keys into the rate snapshots; settled_amount + currency; fx_usd_rate + settled_amount_usd; rate_bps and cashback_pct picked as-of settlement_day; gross_interchange_usd, network_fee_usd, rewards_accrued_usd."),
    ("int_refund_matching", "one row per refund / dispute event", "refund_event_id",
     "Links each refund or dispute back to its original transaction (by id, or fuzzily on card+merchant+amount+window) so revenue can be clawed back, and flags the ones that cannot be matched.",
     "refund_event_id; event_type (refund / dispute); refund_ts, refund_amount, currency; card_id / merchant_id; matched_transaction_id (FK lifecycle, null if unmatched); match_method (original_id / fuzzy / unmatched) + match_confidence; original_settlement_day / original_accounting_period tell the close whether it hits a locked month."),
])

MRT = ("marts layer  -  dim_* / fct_*   (star schema, surrogate keys)", [
    ("dim_company", "one row per company", "company_key (surrogate)",
     "Conformed company dimension for slicing revenue by customer.",
     "company_key (surrogate PK); company_id (natural key); company_name; region; onboarded_at."),
    ("dim_card", "one row per card", "card_key (surrogate)",
     "Card dimension; carries the pricing tier and the link to company.",
     "card_key; card_id; company_key (FK dim_company); card_program; issued_at; status."),
    ("dim_merchant", "one row per merchant", "merchant_key (surrogate)",
     "Merchant dimension with the normalized spend category for analytics.",
     "merchant_key; merchant_id; merchant_name; mcc; spend_category; merchant_country."),
    ("dim_date", "one row per calendar day", "date_day",
     "Standard date spine; carries the accounting period and month-end flag the close relies on.",
     "date_day; year / quarter / month; accounting_period (YYYY-MM); is_month_end."),
    ("fct_transactions", "one row per transaction", "transaction_id",
     "Transaction-level fact for 'how many / how much' analysis, with dimension keys attached.",
     "transaction_id; card_key / merchant_key / company_key / first_auth_date / settled_at (FKs to dims); current_status; currency; authorized_amount, settled_amount, settled_amount_usd."),
    ("fct_interchange_revenue", "one row per transaction per settlement day", "transaction_id, settlement_day",
     "The core deliverable: recognized interchange revenue per settled transaction. This is the number finance closes on.",
     "transaction_id + settlement_day (compound key); accounting_period; card_key / merchant_key / company_key (FKs); settled_amount_usd; gross_interchange_usd, network_fee_usd, rewards_accrued_usd; net_interchange_usd = gross - fee - rewards; is_recognized (true once the period is locked)."),
    ("fct_revenue_adjustments", "one row per prior-period reversal booked", "adjustment_id",
     "A refund or dispute that lands in a closed month cannot rewrite it, so each one becomes an adjustment booked into the current open period.",
     "adjustment_id; source_event_id; original_transaction_id (FK); original_accounting_period vs booked_accounting_period; adjustment_type (refund / dispute / chargeback); gross_interchange_reversed_usd, rewards_reversed_usd, net_adjustment_usd; booked_at."),
    ("recon_settlement", "one row per settlement date", "settlement_day",
     "The daily control: compares the marts' settled total to the bank file and fails the pipeline if the gap exceeds tolerance.",
     "settlement_day; internal_settled_usd vs file_settled_usd; variance_usd, variance_pct; variance_class (ok / timing / break); internal_txn_count vs file_txn_count; status (ok / warn / fail)."),
    ("recognized_revenue", "one row per accounting period (month)", "accounting_period",
     "The month-level close summary: recognized vs still-accruing vs pending, plus the lock state.",
     "accounting_period; period_status (open / locked); recognized_net_interchange_usd, accrued_net_interchange_usd, pending_net_interchange_usd, adjustments_usd; locked_at."),
])

render("grain_dict_1.jpg", 300, "Data dictionary (1 of 2)  -  raw  ->  staging  ->  snapshots", [RAW, STG, SNP])
render("grain_dict_2.jpg", 260, "Data dictionary (2 of 2)  -  intermediate  ->  marts", [INT, MRT])
