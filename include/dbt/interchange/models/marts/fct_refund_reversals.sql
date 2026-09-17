-- One row per refund event, with the interchange it takes back.
--
-- Policy:
--   * A refund reduces revenue on the date it happens. Closed periods are never
--     restated; the month-end close depends on a closed month staying closed.
--   * The clawback is proportional to the original booking: refund amount over
--     settled amount, applied to the gross interchange and rewards that purchase
--     actually booked. A full refund reverses exactly what was earned, at the
--     original rates and FX rate, so no FX movement leaks into interchange revenue.
--   * Network fees are not reversed. They are treated as a cost already incurred.
--   * A purchase can never give back more than it earned. The matcher can assign
--     two refunds to one purchase, so the reversal is capped per purchase.
--   * An unmatched refund is kept with null reversal amounts: there is no booking
--     to reverse, and dropping it would hide it from the people who resolve it.

with refunds as (

    select
        m.event_id,
        m.matched_transaction_id,
        m.is_matched,
        m.match_method,
        m.match_confidence,
        m.card_id,
        m.merchant_id,
        m.currency,
        m.refund_amount,
        m.refund_ts,

        f.settlement_date       as original_settlement_date,
        f.settled_amount        as original_settled_amount,
        f.usd_rate              as original_usd_rate,
        f.gross_interchange_usd as original_gross_interchange_usd,
        f.rewards_accrued_usd   as original_rewards_accrued_usd

    from {{ ref('int_refund_matching') }} m
    left join {{ ref('fct_interchange_revenue') }} f
        on m.matched_transaction_id = f.transaction_id

),

cumulative as (

    -- Running share of the purchase refunded, up to and including this refund.
    -- Ordered by match confidence before time: when refunds compete for the same
    -- purchase, the trustworthy link claims its share first and the guess absorbs
    -- the cap. Time order alone would let a low-confidence match that happened to
    -- arrive first crowd out the refund that is known to be real.
    select
        *,
        refund_amount / original_settled_amount as requested_ratio,
        sum(refund_amount / original_settled_amount) over (
            partition by matched_transaction_id
            order by
                case match_confidence
                    when 'exact_link' then 0
                    when 'high'       then 1
                    when 'medium'     then 2
                    else 3
                end,
                refund_ts,
                event_id
            rows between unbounded preceding and current row
        ) as cumulative_ratio
    from refunds

),

capped as (

    -- Cap the running total at 1, then take the difference from the previous
    -- capped total. Each refund gets its share, and the shares of one purchase can
    -- never add up to more than 1.
    select
        *,
        case
            when matched_transaction_id is null then null
            else least(cumulative_ratio, 1)
               - least(cumulative_ratio - requested_ratio, 1)
        end as reversal_ratio
    from cumulative

)

select
    c.event_id,
    c.matched_transaction_id,

    {{ dbt_utils.generate_surrogate_key(['c.card_id']) }}::varchar     as card_key,
    d.company_key,
    {{ dbt_utils.generate_surrogate_key(['c.merchant_id']) }}::varchar as merchant_key,

    c.refund_ts::date            as refund_date,
    c.refund_ts,
    c.original_settlement_date,

    -- Under this policy a refund in a later month reduces that later month, which
    -- is exactly the kind of line finance will ask about.
    date_trunc('month', c.refund_ts) > date_trunc('month', c.original_settlement_date)
                                 as is_prior_period_purchase,

    c.is_matched,
    c.match_method,
    c.match_confidence,

    c.currency,
    c.refund_amount,
    -- Converted at the original purchase's rate, to match how it was booked.
    (c.refund_amount * c.original_usd_rate)::number(18,6)              as refund_amount_usd,

    c.reversal_ratio::number(18,10)                                     as reversal_ratio,
    coalesce(c.reversal_ratio < c.requested_ratio, false)               as is_capped,

    (c.original_gross_interchange_usd * c.reversal_ratio)::number(18,6) as gross_interchange_reversed_usd,
    (c.original_rewards_accrued_usd   * c.reversal_ratio)::number(18,6) as rewards_reversed_usd,
    (  (c.original_gross_interchange_usd * c.reversal_ratio)::number(18,6)
     - (c.original_rewards_accrued_usd   * c.reversal_ratio)::number(18,6)
    )::number(18,6)                                                     as net_interchange_reversed_usd

from capped c
join {{ ref('dim_card') }} d
    on d.card_id = c.card_id
