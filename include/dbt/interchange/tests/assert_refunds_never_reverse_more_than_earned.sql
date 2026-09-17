-- A purchase can give back at most what it earned. Returns any purchase whose
-- reversals add up to more than its original booking. The tolerance absorbs the
-- sub-millionth rounding from storing each share at fixed precision; it is far
-- below anything a real double reversal would produce.
with reversed as (

    select
        matched_transaction_id,
        count(*)                            as refunds,
        sum(reversal_ratio)                 as total_ratio,
        sum(gross_interchange_reversed_usd) as gross_reversed,
        sum(rewards_reversed_usd)           as rewards_reversed
    from {{ ref('fct_refund_reversals') }}
    where is_matched
    group by matched_transaction_id

)

select
    r.matched_transaction_id,
    r.refunds,
    r.total_ratio,
    r.gross_reversed,
    f.gross_interchange_usd as gross_earned,
    r.rewards_reversed,
    f.rewards_accrued_usd   as rewards_earned
from reversed r
join {{ ref('fct_interchange_revenue') }} f
    on r.matched_transaction_id = f.transaction_id
where r.total_ratio      > 1 + 0.000001
   or r.gross_reversed   > f.gross_interchange_usd + 0.000001 * r.refunds
   or r.rewards_reversed > f.rewards_accrued_usd   + 0.000001 * r.refunds
