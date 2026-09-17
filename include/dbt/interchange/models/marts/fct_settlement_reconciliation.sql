-- One row per day: our settled ledger against the bank's settlement file.
--
-- Our side is summed from fct_interchange_revenue at full precision and rounded
-- once, the same way the bank produces its figure. Rounding per transaction or per
-- company first would make clean days disagree by cents.

with days as (

    -- The date spine plus any day the bank reports. A bank row dated outside the
    -- spine must still show up as a break, not be filtered away by the join.
    select date_day as settlement_date from {{ ref('dim_date') }}
    union
    select settlement_date from {{ ref('stg_network_settlement') }}

),

ledger as (

    select
        settlement_date,
        count(*)                          as txn_count,
        round(sum(settled_amount_usd), 2) as settled_amount_usd
    from {{ ref('fct_interchange_revenue') }}
    group by settlement_date

),

joined as (

    select
        d.settlement_date,
        b.file_id                         as bank_file_id,
        b.settlement_date is not null     as has_bank_file,
        coalesce(l.txn_count, 0)          as our_txn_count,
        b.total_txn_count                 as bank_txn_count,
        coalesce(l.settled_amount_usd, 0) as our_settled_amount_usd,
        b.total_settled_amount_usd        as bank_settled_amount_usd
    from days d
    left join ledger l
        on d.settlement_date = l.settlement_date
    left join {{ ref('stg_network_settlement') }} b
        on d.settlement_date = b.settlement_date

),

classified as (

    select
        settlement_date,
        bank_file_id,
        has_bank_file,

        our_txn_count::number(18,0)                                      as our_txn_count,
        bank_txn_count::number(18,0)                                     as bank_txn_count,
        (our_txn_count - bank_txn_count)::number(18,0)                   as txn_count_diff,

        our_settled_amount_usd::number(18,2)                             as our_settled_amount_usd,
        bank_settled_amount_usd::number(18,2)                            as bank_settled_amount_usd,
        (our_settled_amount_usd - bank_settled_amount_usd)::number(18,2) as settled_amount_diff_usd,

        -- Order matters: a missing side is reported as missing before anything is
        -- compared, and a count difference is a break even if the amounts agree.
        case
            when not has_bank_file and our_txn_count = 0          then 'no_activity'
            when not has_bank_file                                then 'missing_bank_file'
            when our_txn_count = 0                                then 'missing_in_ledger'
            when our_txn_count <> bank_txn_count                  then 'break'
            when our_settled_amount_usd = bank_settled_amount_usd then 'matched'
            when abs(our_settled_amount_usd - bank_settled_amount_usd)
                 <= {{ var('recon_amount_tolerance_usd') }}       then 'within_tolerance'
            else 'break'
        end as recon_status

    from joined

)

select
    *,
    -- A missing side is as much a break as a wrong amount: money moved that one
    -- party has no record of.
    recon_status in ('break', 'missing_bank_file', 'missing_in_ledger') as is_break
from classified
