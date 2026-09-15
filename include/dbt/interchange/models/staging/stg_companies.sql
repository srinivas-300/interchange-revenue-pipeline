with source as (

    select * from {{ source('sim', 'companies') }}

),

latest as (

    -- Each load is a full snapshot; keep the most recently loaded row per company.
    select *
    from source
    qualify row_number() over (
        partition by company_id
        order by _loaded_at desc, _batch_id desc
    ) = 1

)

select
    company_id,
    company_name,
    region,
    onboarded_at,
    convert_timezone('America/Los_Angeles', 'UTC', _loaded_at) as _loaded_at_utc,
    _batch_id,
    _source_file
from latest
