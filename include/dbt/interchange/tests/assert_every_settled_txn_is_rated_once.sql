-- A duplicate rate version would fan the join out, and every row would still pass
-- its per-row tests: nothing NULL, nothing out of range, just more rows and
-- overstated revenue. Only a count against the source model catches that.
-- The same test catches the opposite failure, a row lost to a missed join.
with expected as (

    select count(*) as row_count
    from {{ ref('int_transaction_lifecycle') }}
    where settled_at is not null

),

actual as (

    select
        count(*)                       as row_count,
        count(distinct transaction_id) as distinct_transactions
    from {{ ref('int_txn_rated') }}

)

select
    expected.row_count as expected_rows,
    actual.row_count   as actual_rows,
    actual.distinct_transactions
from expected
cross join actual
where expected.row_count <> actual.row_count
   or actual.row_count <> actual.distinct_transactions
