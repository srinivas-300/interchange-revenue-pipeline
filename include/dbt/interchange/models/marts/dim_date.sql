-- One row per calendar day. Daily reports join to this rather than grouping
-- transactions directly, because a day with no activity has no transactions to
-- group - it would silently disappear from the report instead of showing zero.

with spine as (

    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('" ~ var('date_spine_start') ~ "' as date)",
        end_date="cast('" ~ var('date_spine_end') ~ "' as date)"
    ) }}

),

days as (

    select cast(date_day as date) as date_day
    from spine

)

select
    date_day,

    -- ISO numbering (Monday = 1). Computed explicitly rather than with
    -- date_trunc('week', ...), whose result depends on the Snowflake session's
    -- WEEK_START parameter and could shift between environments.
    dayofweekiso(date_day)::number(4,0)                          as day_of_week_iso,
    dayname(date_day)::varchar                                   as day_name,
    dayofweekiso(date_day) in (6, 7)                             as is_weekend,
    dateadd('day', 1 - dayofweekiso(date_day), date_day)         as week_start_date,
    weekiso(date_day)::number(4,0)                               as iso_week_of_year,

    month(date_day)::number(4,0)                                 as month_of_year,
    monthname(date_day)::varchar                                 as month_name,
    date_trunc('month', date_day)::date                          as month_start_date,
    last_day(date_day, 'month')                                  as month_end_date,
    -- The close in Phase 6 runs on month-end, so it gets its own flag.
    date_day = last_day(date_day, 'month')                       as is_month_end,

    quarter(date_day)::number(4,0)                               as quarter_of_year,
    date_trunc('quarter', date_day)::date                        as quarter_start_date,
    year(date_day)::number(4,0)                                  as year_number

from days
