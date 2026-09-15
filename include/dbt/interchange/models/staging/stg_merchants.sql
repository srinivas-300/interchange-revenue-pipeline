with source as (

    select * from {{ source('sim', 'merchants') }}

),

latest as (

    select *
    from source
    qualify row_number() over (
        partition by merchant_id
        order by _loaded_at desc, _batch_id desc
    ) = 1

)

select
    merchant_id,
    merchant_name,
    mcc,
    merchant_country,
    descriptor,
    convert_timezone('America/Los_Angeles', 'UTC', _loaded_at) as _loaded_at_utc,
    _batch_id,
    _source_file
from latest
