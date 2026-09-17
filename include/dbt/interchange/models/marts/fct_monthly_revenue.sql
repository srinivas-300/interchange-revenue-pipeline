-- One row per month: the revenue figures the close signs off, and whether the month
-- is closed. snap_monthly_revenue records every version of these rows, which is what
-- lets fct_month_end_close tell a closed month's signed-off figures from today's.

with monthly as (

    select
        date_trunc('month', date_day)::date      as period_month,
        sum(settled_txn_count)                   as settled_txn_count,
        sum(settled_amount_usd)                  as settled_amount_usd,
        sum(gross_interchange_usd)               as gross_interchange_usd,
        sum(network_fee_usd)                     as network_fee_usd,
        sum(rewards_accrued_usd)                 as rewards_accrued_usd,
        sum(net_interchange_usd)                 as net_interchange_usd,
        sum(refund_count)                        as refund_count,
        sum(net_interchange_reversed_usd)        as net_interchange_reversed_usd,
        sum(net_interchange_after_refunds_usd)   as net_interchange_after_refunds_usd
    from {{ ref('agg_daily_interchange_revenue') }}
    group by 1

)

select
    m.period_month,
    c.period_month is not null                            as is_closed,
    c.closed_on,
    c.closed_by,

    m.settled_txn_count::number(18,0)                     as settled_txn_count,
    m.settled_amount_usd::number(18,6)                    as settled_amount_usd,
    m.gross_interchange_usd::number(18,6)                 as gross_interchange_usd,
    m.network_fee_usd::number(18,6)                       as network_fee_usd,
    m.rewards_accrued_usd::number(18,6)                   as rewards_accrued_usd,
    m.net_interchange_usd::number(18,6)                   as net_interchange_usd,
    m.refund_count::number(18,0)                          as refund_count,
    m.net_interchange_reversed_usd::number(18,6)          as net_interchange_reversed_usd,
    m.net_interchange_after_refunds_usd::number(18,6)     as net_interchange_after_refunds_usd

from monthly m
left join {{ ref('close_calendar') }} c
    on m.period_month = c.period_month
