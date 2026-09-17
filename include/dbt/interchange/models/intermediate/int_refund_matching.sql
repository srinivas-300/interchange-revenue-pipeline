-- One row per refund event, matched back to the purchase it reverses.
--
-- Refunds that carry original_transaction_id are linked directly. The rest have to
-- be inferred from card, merchant, currency, amount and timing, which is what
-- actually happens: a refund arrives days or weeks later as its own movement with
-- nothing tying it to the purchase.
--
-- This model never reads the refund event's own transaction_id. In this simulator
-- that column happens to hold the original transaction, so it is ground truth for
-- measuring the matcher - which makes it the one column the matcher is not allowed
-- to see. Leaving it out of the model entirely is what keeps that guarantee
-- structural instead of a promise in a comment.

with refunds as (

    select
        event_id,
        card_id,
        merchant_id,
        currency,
        amount   as refund_amount,
        event_ts as refund_ts,
        original_transaction_id,
        _loaded_at_utc
    from {{ ref('stg_card_events') }}
    where event_type = 'refund'

),

settled_txns as (

    select
        transaction_id,
        card_id,
        merchant_id,
        currency,
        settled_amount,
        settled_at
    from {{ ref('int_transaction_lifecycle') }}
    where settled_at is not null

),

candidates as (

    -- Only the unlinked refunds need searching. A refund cannot precede its
    -- purchase, and cannot exceed the amount that was charged.
    select
        r.event_id,
        t.transaction_id,
        t.settled_amount,
        t.settled_at,
        datediff('day', t.settled_at, r.refund_ts)    as days_since_settlement,
        datediff('second', t.settled_at, r.refund_ts) as seconds_since_settlement,
        r.refund_amount = t.settled_amount            as is_amount_exact,

        -- A full refund is far stronger evidence than a partial one, which could
        -- be any fraction of any purchase on the same card and merchant.
        case when r.refund_amount = t.settled_amount then 100 else 50 end as match_score

    from refunds r
    join settled_txns t
        on  r.card_id     = t.card_id
        and r.merchant_id = t.merchant_id
        and r.currency    = t.currency
    where r.original_transaction_id is null
      and r.refund_ts >  t.settled_at
      and r.refund_ts <= dateadd('day', {{ var('refund_match_window_days') }}, t.settled_at)
      and r.refund_amount <= t.settled_amount

),

best_candidate as (

    -- candidate_count is computed before qualify, so it counts every candidate,
    -- not just the surviving one. transaction_id is the last tie-break so the
    -- choice is deterministic: without it the model could return a different
    -- answer on identical data and the precision tests would flap.
    select
        event_id,
        transaction_id,
        settled_amount,
        settled_at,
        days_since_settlement,
        is_amount_exact,
        count(*) over (partition by event_id) as candidate_count
    from candidates
    qualify row_number() over (
        partition by event_id
        order by match_score desc, seconds_since_settlement asc, transaction_id
    ) = 1

)

select
    r.event_id,
    r.card_id,
    r.merchant_id,
    r.currency,
    r.refund_amount,
    r.refund_ts,

    coalesce(r.original_transaction_id, b.transaction_id)                as matched_transaction_id,
    coalesce(r.original_transaction_id, b.transaction_id) is not null    as is_matched,

    case
        when r.original_transaction_id is not null then 'original_link'
        when b.transaction_id is not null          then 'heuristic'
        else 'none'
    end as match_method,

    -- Confidence is what a human reviewing the unmatched queue actually sorts on.
    case
        when r.original_transaction_id is not null            then 'exact_link'
        when b.transaction_id is null                         then 'unmatched'
        when b.is_amount_exact and b.candidate_count = 1      then 'high'
        when b.is_amount_exact                                then 'medium'
        when b.candidate_count = 1                            then 'medium'
        else 'low'
    end as match_confidence,

    b.candidate_count::number(18,0)        as candidate_count,
    b.settled_amount                       as matched_settled_amount,
    b.settled_at                           as matched_settled_at,
    b.days_since_settlement::number(18,0)  as days_since_settlement,

    r._loaded_at_utc
from refunds r
left join best_candidate b
    on r.event_id = b.event_id
