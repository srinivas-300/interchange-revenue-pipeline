-- One row per month: can it be closed, and if not, why not.
--
-- A month is ready when the bank has reported its last day (so no settlements can
-- still arrive for it) and every reconciliation break in it is explained - either a
-- self-clearing cutoff pair, or signed off in settlement_break_resolutions.

with months as (

    select period_month, is_closed, closed_on
    from {{ ref('fct_monthly_revenue') }}

),

month_end_bank_file as (

    select
        date_trunc('month', settlement_date)::date as period_month,
        max(iff(has_bank_file and settlement_date = last_day(settlement_date, 'month'), 1, 0)) = 1
            as has_month_end_bank_file
    from {{ ref('fct_settlement_reconciliation') }}
    group by 1

),

breaks as (

    select
        date_trunc('month', a.settlement_date)::date                        as period_month,
        count(*)                                                            as break_days,
        count_if(a.is_self_clearing)                                        as self_clearing_break_days,
        count_if(not a.is_self_clearing and r.settlement_date is not null)  as resolved_break_days,
        count_if(not a.is_self_clearing and r.settlement_date is null)      as unexplained_break_days
    from {{ ref('fct_settlement_break_attribution') }} a
    left join {{ ref('settlement_break_resolutions') }} r
        on a.settlement_date = r.settlement_date
    group by 1

),

assessed as (

    select
        m.period_month,
        m.is_closed,
        m.closed_on,
        coalesce(f.has_month_end_bank_file, false)             as has_month_end_bank_file,
        coalesce(b.break_days, 0)::number(18,0)                as break_days,
        coalesce(b.self_clearing_break_days, 0)::number(18,0)  as self_clearing_break_days,
        coalesce(b.resolved_break_days, 0)::number(18,0)       as resolved_break_days,
        coalesce(b.unexplained_break_days, 0)::number(18,0)    as unexplained_break_days
    from months m
    left join month_end_bank_file f
        on m.period_month = f.period_month
    left join breaks b
        on m.period_month = b.period_month

)

select
    *,
    has_month_end_bank_file and unexplained_break_days = 0 as is_ready_to_close,
    case
        when not has_month_end_bank_file then 'month_end_bank_file_missing'
        when unexplained_break_days > 0  then 'unexplained_breaks'
    end as close_blocked_reason
from assessed
