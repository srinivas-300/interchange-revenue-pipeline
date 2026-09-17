-- Every date the pipeline reports on must exist in dim_date. If activity lands
-- outside the spine's bounds, a report joining to dim_date would drop those days
-- without an error. Returns each uncovered date and where it came from.
with activity_dates as (

    select distinct settlement_date as activity_date, 'int_txn_rated.settlement_date' as source
    from {{ ref('int_txn_rated') }}

    union all

    select distinct refund_ts::date, 'int_refund_matching.refund_ts'
    from {{ ref('int_refund_matching') }}

    union all

    select distinct settlement_date, 'stg_network_settlement.settlement_date'
    from {{ ref('stg_network_settlement') }}

    union all

    select distinct authorized_at::date, 'int_transaction_lifecycle.authorized_at'
    from {{ ref('int_transaction_lifecycle') }}

)

select a.activity_date, a.source
from activity_dates a
left join {{ ref('dim_date') }} d
    on a.activity_date = d.date_day
where d.date_day is null
