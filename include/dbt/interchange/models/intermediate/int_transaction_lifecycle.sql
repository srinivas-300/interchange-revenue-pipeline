with events as (

    -- Refunds are handled separately in int_refund_matching: in the real world they
    -- arrive as their own movement, often without a link back to the original.
    select *
    from {{ ref('stg_card_events') }}
    where event_type in ('authorization', 'auth_reversal', 'clearing', 'settlement', 'dispute')

),

watermark as (

    -- The newest event we have seen; "expired" is judged relative to this, not today.
    select max(event_ts) as latest_event_ts from events

),

by_transaction as (

    select
        transaction_id,

        -- constant across every event of a transaction
        any_value(card_id)     as card_id,
        any_value(merchant_id) as merchant_id,
        any_value(mcc)         as mcc,
        any_value(currency)    as currency,

        min(case when event_type = 'authorization' then event_ts end) as authorized_at,
        sum(case when event_type = 'authorization' then amount  end)  as authorized_amount,

        sum(case when event_type = 'auth_reversal' then amount  end)  as reversed_amount,
        max(case when event_type = 'auth_reversal' then event_ts end) as reversed_at,

        count_if(event_type = 'clearing')                             as clearing_count,
        sum(case when event_type = 'clearing' then amount  end)       as cleared_amount,
        max(case when event_type = 'clearing' then event_ts end)      as cleared_at,

        sum(case when event_type = 'settlement' then amount  end)     as settled_amount,
        max(case when event_type = 'settlement' then event_ts end)    as settled_at,

        max(case when event_type = 'dispute' then event_ts end)       as disputed_at,

        count(*)              as event_count,
        min(event_ts)         as first_event_ts,
        max(event_ts)         as last_event_ts,
        max(_loaded_at_utc)   as _loaded_at_utc

    from events
    group by transaction_id

)

select
    t.transaction_id,
    t.card_id,
    t.merchant_id,
    t.mcc,
    t.currency,

    case
        when t.settled_at is not null                                    then 'settled'
        when t.clearing_count > 0                                        then 'cleared'
        when coalesce(t.reversed_amount, 0) >= t.authorized_amount       then 'reversed'
        when t.authorized_at
             < dateadd('day', -{{ var('auth_expiry_days') }}, w.latest_event_ts) then 'expired'
        else 'authorized'
    end as status,

    t.authorized_at,
    t.authorized_amount,
    t.reversed_amount,
    t.reversed_at,
    t.clearing_count,
    t.cleared_amount,
    t.cleared_at,
    t.settled_amount,
    t.settled_at,
    t.settled_at::date as settlement_date,
    t.disputed_at,
    t.disputed_at is not null as is_disputed,

    t.event_count,
    t.first_event_ts,
    t.last_event_ts,
    t._loaded_at_utc
from by_transaction t
cross join watermark w
