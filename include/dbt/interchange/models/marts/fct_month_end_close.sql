-- One row per closed month: the figures it was signed off at, today's figures, and
-- whether anything has changed since.
--
-- The refund policy already keeps closed months stable in the normal course: a
-- refund lands in the month it happens, never back in the purchase's month. What can
-- still move a closed month is data arriving late for it, a reprocessed file, or a
-- logic change. Those are exactly the restatements this model surfaces.

with locked as (

    -- The first version the snapshot recorded with the month closed. Versions from
    -- while the month was open are ignored: an open month is supposed to change.
    select *
    from {{ ref('snap_monthly_revenue') }}
    where is_closed
    qualify row_number() over (partition by period_month order by dbt_valid_from) = 1

),

current_closed as (

    select *
    from {{ ref('fct_monthly_revenue') }}
    where is_closed

)

select
    c.period_month,
    c.closed_on,
    c.closed_by,
    l.dbt_valid_from                                        as locked_at,

    l.settled_txn_count                                     as locked_settled_txn_count,
    c.settled_txn_count                                     as current_settled_txn_count,

    l.settled_amount_usd                                    as locked_settled_amount_usd,
    c.settled_amount_usd                                    as current_settled_amount_usd,

    l.net_interchange_after_refunds_usd                     as locked_net_interchange_after_refunds_usd,
    c.net_interchange_after_refunds_usd                     as current_net_interchange_after_refunds_usd,
    (c.net_interchange_after_refunds_usd - l.net_interchange_after_refunds_usd)::number(18,6)
                                                            as restatement_net_interchange_usd,

    -- Any signed-off figure moving counts, not just the headline: a change in
    -- transaction count with the same net would still mean the books were wrong.
    coalesce(
           c.settled_txn_count                 is distinct from l.settled_txn_count
        or c.settled_amount_usd                is distinct from l.settled_amount_usd
        or c.gross_interchange_usd             is distinct from l.gross_interchange_usd
        or c.network_fee_usd                   is distinct from l.network_fee_usd
        or c.rewards_accrued_usd               is distinct from l.rewards_accrued_usd
        or c.net_interchange_usd               is distinct from l.net_interchange_usd
        or c.refund_count                      is distinct from l.refund_count
        or c.net_interchange_reversed_usd      is distinct from l.net_interchange_reversed_usd
        or c.net_interchange_after_refunds_usd is distinct from l.net_interchange_after_refunds_usd,
        false
    )                                                       as is_restated

from current_closed c
left join locked l
    on c.period_month = l.period_month
