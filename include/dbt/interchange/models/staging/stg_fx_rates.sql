with source as (

    select * from {{ source('sim', 'fx_rates') }}

),

latest as (

    select *
    from source
    qualify row_number() over (
        partition by currency, rate_date
        order by _loaded_at desc, _batch_id desc
    ) = 1

)

select
    currency,
    rate_date,
    usd_rate,
    convert_timezone('America/Los_Angeles', 'UTC', _loaded_at) as _loaded_at_utc,
    _batch_id,
    _source_file
from latest
