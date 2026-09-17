-- The daily aggregate must hold every row of the spine and every dollar of both
-- facts: no day or company dropped, no revenue or refund lost in a join. Same
-- precision on both sides, so the tolerance is zero. Returns each check that fails.
with agg as (

    select
        count(*)                            as row_count,
        sum(settled_txn_count)              as settled_txn_count,
        sum(net_interchange_usd)            as net_interchange_usd,
        sum(refund_count)                   as refund_count,
        sum(net_interchange_reversed_usd)   as net_interchange_reversed_usd
    from {{ ref('agg_daily_interchange_revenue') }}

),

expected as (

    select
        (select count(*) from {{ ref('dim_date') }})
          * (select count(*) from {{ ref('dim_company') }})                          as row_count,
        (select count(*) from {{ ref('fct_interchange_revenue') }})                  as settled_txn_count,
        (select sum(net_interchange_usd) from {{ ref('fct_interchange_revenue') }})  as net_interchange_usd,
        (select count(*) from {{ ref('fct_refund_reversals') }})                     as refund_count,
        (select coalesce(sum(net_interchange_reversed_usd), 0)
           from {{ ref('fct_refund_reversals') }})                                   as net_interchange_reversed_usd

),

compared as (

    select 'row_count' as check_name, a.row_count as agg_value, e.row_count as expected_value from agg a cross join expected e
    union all
    select 'settled_txn_count', a.settled_txn_count, e.settled_txn_count from agg a cross join expected e
    union all
    select 'net_interchange_usd', a.net_interchange_usd, e.net_interchange_usd from agg a cross join expected e
    union all
    select 'refund_count', a.refund_count, e.refund_count from agg a cross join expected e
    union all
    select 'net_interchange_reversed_usd', a.net_interchange_reversed_usd, e.net_interchange_reversed_usd from agg a cross join expected e

)

select *
from compared
where agg_value <> expected_value
