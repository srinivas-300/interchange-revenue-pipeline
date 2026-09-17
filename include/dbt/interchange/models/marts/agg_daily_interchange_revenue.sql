-- One row per day per company, including days a company had no activity.
--
-- Settlement revenue lands on its settlement date; refund reversals land on their
-- refund date (see fct_refund_reversals for the policy). Net after refunds is the
-- revenue line for the day.
--
-- Money is not rounded here. This table is itself summed - across companies for a
-- daily total, across days for a month - and rounded stored values would bring
-- back the drift the facts avoid. Round when presenting or comparing, not when
-- storing.

with spine as (

    -- Every company on every day. Without this, a company with a quiet day has no
    -- row, and a chart of its daily revenue skips the day instead of showing zero.
    select
        d.date_day,
        c.company_key
    from {{ ref('dim_date') }} d
    cross join {{ ref('dim_company') }} c

),

settled as (

    select
        settlement_date                 as date_day,
        company_key,
        count(*)                        as settled_txn_count,
        count_if(is_disputed)           as disputed_txn_count,
        sum(settled_amount_usd)         as settled_amount_usd,
        sum(gross_interchange_usd)      as gross_interchange_usd,
        sum(network_fee_usd)            as network_fee_usd,
        sum(rewards_accrued_usd)        as rewards_accrued_usd,
        sum(net_interchange_usd)        as net_interchange_usd
    from {{ ref('fct_interchange_revenue') }}
    group by 1, 2

),

refunded as (

    select
        refund_date                          as date_day,
        company_key,
        count(*)                             as refund_count,
        count_if(not is_matched)             as unmatched_refund_count,
        sum(refund_amount_usd)               as refund_amount_usd,
        sum(gross_interchange_reversed_usd)  as gross_interchange_reversed_usd,
        sum(rewards_reversed_usd)            as rewards_reversed_usd,
        sum(net_interchange_reversed_usd)    as net_interchange_reversed_usd
    from {{ ref('fct_refund_reversals') }}
    group by 1, 2

)

select
    s.date_day,
    s.company_key,

    coalesce(st.settled_txn_count, 0)::number(18,0)            as settled_txn_count,
    coalesce(st.disputed_txn_count, 0)::number(18,0)           as disputed_txn_count,
    coalesce(st.settled_amount_usd, 0)::number(18,6)           as settled_amount_usd,
    coalesce(st.gross_interchange_usd, 0)::number(18,6)        as gross_interchange_usd,
    coalesce(st.network_fee_usd, 0)::number(18,6)              as network_fee_usd,
    coalesce(st.rewards_accrued_usd, 0)::number(18,6)          as rewards_accrued_usd,
    coalesce(st.net_interchange_usd, 0)::number(18,6)          as net_interchange_usd,

    coalesce(r.refund_count, 0)::number(18,0)                  as refund_count,
    coalesce(r.unmatched_refund_count, 0)::number(18,0)        as unmatched_refund_count,
    coalesce(r.refund_amount_usd, 0)::number(18,6)             as refund_amount_usd,
    coalesce(r.gross_interchange_reversed_usd, 0)::number(18,6) as gross_interchange_reversed_usd,
    coalesce(r.rewards_reversed_usd, 0)::number(18,6)          as rewards_reversed_usd,
    coalesce(r.net_interchange_reversed_usd, 0)::number(18,6)  as net_interchange_reversed_usd,

    (  coalesce(st.net_interchange_usd, 0)
     - coalesce(r.net_interchange_reversed_usd, 0)
    )::number(18,6)                                            as net_interchange_after_refunds_usd

from spine s
left join settled st
    on  s.date_day = st.date_day
    and s.company_key = st.company_key
left join refunded r
    on  s.date_day = r.date_day
    and s.company_key = r.company_key
