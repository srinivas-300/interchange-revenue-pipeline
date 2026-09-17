-- Every break in the reconciliation must get exactly one cause. A break dropped here
-- would never reach the close controls, and the month could close over it.
with expected as (

    select count(*) as break_count
    from {{ ref('fct_settlement_reconciliation') }}
    where is_break

),

actual as (

    select
        count(*)                        as row_count,
        count(distinct settlement_date) as distinct_days
    from {{ ref('fct_settlement_break_attribution') }}

)

select
    expected.break_count,
    actual.row_count,
    actual.distinct_days
from expected
cross join actual
where expected.break_count <> actual.row_count
   or actual.row_count <> actual.distinct_days
