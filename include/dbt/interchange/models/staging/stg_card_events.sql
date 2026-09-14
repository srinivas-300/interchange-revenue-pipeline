with source as (

    select * from {{ source('sim', 'card_events') }}

),

deduped as (

    -- Raw keeps every copy of an event (exact duplicates and re-sent files).
    -- Keep the most recently loaded version of each event_id.
    select *
    from source
    qualify row_number() over (
        partition by event_id
        order by _loaded_at desc, _batch_id desc
    ) = 1

)

select
    event_id,
    transaction_id,
    card_id,
    merchant_id,
    mcc,
    event_type,
    event_ts,
    event_ts::date                                               as event_date,
    ingested_at,
    amount,
    upper(currency)                                              as currency,
    original_transaction_id,
    convert_timezone('America/Los_Angeles', 'UTC', _loaded_at)   as _loaded_at_utc,
    _batch_id,
    _source_file
from deduped
