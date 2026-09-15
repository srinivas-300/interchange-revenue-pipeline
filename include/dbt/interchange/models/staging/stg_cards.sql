with source as (

    select * from {{ source('sim', 'cards') }}

),

latest as (

    select *
    from source
    qualify row_number() over (
        partition by card_id
        order by _loaded_at desc, _batch_id desc
    ) = 1

)

select
    card_id,
    company_id,
    card_program,
    issued_at,
    status,
    convert_timezone('America/Los_Angeles', 'UTC', _loaded_at) as _loaded_at_utc,
    _batch_id,
    _source_file
from latest
