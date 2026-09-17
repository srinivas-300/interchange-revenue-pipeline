-- Grades the matcher against ground truth and fails if it regresses.
--
-- The refund event's own transaction_id holds the original transaction, so it is a
-- correct answer key. int_refund_matching is not allowed to read it; this test is.
-- The floors are set below the figures measured when the model was written
-- (overall precision 98.13%, high+medium 100%, recall 98.13%) so this is a
-- regression guard on deterministic data, not a threshold invented in advance.
with truth as (

    select
        event_id,
        transaction_id as true_transaction_id
    from {{ ref('stg_card_events') }}
    where event_type = 'refund'

),

graded as (

    -- Only the refunds that arrived without a link: the linked ones are not a
    -- test of anything.
    select
        m.match_confidence,
        m.is_matched,
        m.matched_transaction_id = t.true_transaction_id as is_correct
    from {{ ref('int_refund_matching') }} m
    join truth t
        on m.event_id = t.event_id
    where m.match_method <> 'original_link'

),

measured as (

    select
        count(*)                                        as unlinked,
        count_if(is_matched)                            as attempted,
        count_if(is_matched and is_correct)             as correct,
        count_if(match_confidence in ('high', 'medium')) as confident,
        count_if(match_confidence in ('high', 'medium') and is_correct) as confident_correct
    from graded

)

-- Precision: of the matches we asserted, how many were right. A wrong match
-- silently rebates the wrong customer, so this is the one that must not slip.
select
    'precision' as metric,
    round(100.0 * correct / nullif(attempted, 0), 2) as actual_pct,
    95.0 as floor_pct
from measured
where 100.0 * correct / nullif(attempted, 0) < 95.0

union all

-- The confidence tiers have to mean something. If high and medium start carrying
-- errors, the reviewer's queue ordering is lying to them.
select
    'confident_tier_precision',
    round(100.0 * confident_correct / nullif(confident, 0), 2),
    99.0
from measured
where 100.0 * confident_correct / nullif(confident, 0) < 99.0

union all

-- Recall: of the refunds needing a match, how many got the right one. Lower stakes
-- than precision - an unmatched refund waits for a human, a wrong one does not.
select
    'recall',
    round(100.0 * correct / nullif(unlinked, 0), 2),
    95.0
from measured
where 100.0 * correct / nullif(unlinked, 0) < 95.0
