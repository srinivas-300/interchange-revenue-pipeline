-- One row per settled transaction: interchange revenue as recognised at settlement.
-- Refunds are not netted here; fct_refund_reversals records them on their own date.
--
-- Money stays at full precision (number(18,6)). Rounding each row to cents adds up
-- to half a cent of error per row, which across ~1,400 transactions a day drifts
-- daily totals by tens of cents - enough to fail a to-the-cent reconciliation.
-- Anything that sums this table sums first and rounds at the end.

select
    t.transaction_id,

    {{ dbt_utils.generate_surrogate_key(['t.card_id']) }}::varchar     as card_key,
    {{ dbt_utils.generate_surrogate_key(['t.company_id']) }}::varchar  as company_key,
    {{ dbt_utils.generate_surrogate_key(['t.merchant_id']) }}::varchar as merchant_key,
    t.settlement_date,
    t.settled_at,

    -- The inputs the rate was looked up with, as they were at rating time. The
    -- dimensions hold current values only; keeping these on the row means every
    -- figure below stays explainable even if a company later changes region.
    t.mcc,
    t.spend_category,
    t.card_program,
    t.region,
    t.currency,
    t.bps,
    t.cashback_pct,
    t.usd_rate,

    t.is_disputed,

    t.settled_amount,
    t.settled_amount_usd,
    t.gross_interchange_usd,
    t.network_fee_usd,
    t.rewards_accrued_usd,
    t.net_interchange_usd

from {{ ref('int_txn_rated') }} t
