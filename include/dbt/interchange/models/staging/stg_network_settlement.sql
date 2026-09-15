with source as (

    select * from {{ source('sim', 'network_settlement') }}

),

latest as (

    -- One bank settlement file per day; a re-sent file replaces the earlier one.
    select *
    from source
    qualify row_number() over (
        partition by settlement_date
        order by _loaded_at desc, _batch_id desc
    ) = 1

)

select
    settlement_date,
    file_id,
    total_settled_amount_usd,
    total_txn_count,
    convert_timezone('America/Los_Angeles', 'UTC', _loaded_at) as _loaded_at_utc,
    _batch_id,
    _source_file
from latest
