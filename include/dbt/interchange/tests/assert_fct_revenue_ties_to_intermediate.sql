-- No money may be lost or invented between intermediate and the fact. Both sides
-- are at the same precision, so the tolerance is zero. Returns the measures that
-- differ.
with fct as (

    select
        sum(settled_amount_usd)    as settled_amount_usd,
        sum(gross_interchange_usd) as gross_interchange_usd,
        sum(network_fee_usd)       as network_fee_usd,
        sum(rewards_accrued_usd)   as rewards_accrued_usd,
        sum(net_interchange_usd)   as net_interchange_usd
    from {{ ref('fct_interchange_revenue') }}

),

intermediate as (

    select
        sum(settled_amount_usd)    as settled_amount_usd,
        sum(gross_interchange_usd) as gross_interchange_usd,
        sum(network_fee_usd)       as network_fee_usd,
        sum(rewards_accrued_usd)   as rewards_accrued_usd,
        sum(net_interchange_usd)   as net_interchange_usd
    from {{ ref('int_txn_rated') }}

),

compared as (

    select 'settled_amount_usd' as measure, f.settled_amount_usd as fct_total, i.settled_amount_usd as intermediate_total from fct f cross join intermediate i
    union all
    select 'gross_interchange_usd', f.gross_interchange_usd, i.gross_interchange_usd from fct f cross join intermediate i
    union all
    select 'network_fee_usd', f.network_fee_usd, i.network_fee_usd from fct f cross join intermediate i
    union all
    select 'rewards_accrued_usd', f.rewards_accrued_usd, i.rewards_accrued_usd from fct f cross join intermediate i
    union all
    select 'net_interchange_usd', f.net_interchange_usd, i.net_interchange_usd from fct f cross join intermediate i

)

select *
from compared
where fct_total <> intermediate_total
