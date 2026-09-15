with source as (

    select * from {{ source('sim', 'rewards_rates') }}

),

latest as (

    select *
    from source
    qualify row_number() over (
        partition by spend_category, valid_from
        order by _loaded_at desc, _batch_id desc
    ) = 1

)

select
    spend_category,
    cashback_pct,
    valid_from,
    valid_to,   -- exclusive; null = still in effect
    convert_timezone('America/Los_Angeles', 'UTC', _loaded_at) as _loaded_at_utc,
    _batch_id,
    _source_file
from latest
