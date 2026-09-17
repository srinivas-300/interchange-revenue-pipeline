-- Every refund event must appear exactly once, matched or not. Dropping the ones
-- that found no purchase would quietly shrink the unmatched queue that finance
-- works from, and a fan-out would double-count refunded money.
with expected as (

    select count(*) as row_count
    from {{ ref('stg_card_events') }}
    where event_type = 'refund'

),

actual as (

    select
        count(*)                 as row_count,
        count(distinct event_id) as distinct_events
    from {{ ref('int_refund_matching') }}

)

select
    expected.row_count as expected_rows,
    actual.row_count   as actual_rows,
    actual.distinct_events
from expected
cross join actual
where expected.row_count <> actual.row_count
   or actual.row_count <> actual.distinct_events
