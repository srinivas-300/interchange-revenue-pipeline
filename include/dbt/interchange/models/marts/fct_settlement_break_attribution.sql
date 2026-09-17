-- One row per reconciliation break, with its most likely cause.
--
-- The cause is a diagnosis made from the numbers alone, not a confirmation. It tells
-- whoever investigates where to look first; signing a break off is a separate,
-- human step (see the break resolutions seed and fct_close_readiness).

with breaks as (

    select
        settlement_date,
        recon_status,
        txn_count_diff,
        settled_amount_diff_usd
    from {{ ref('fct_settlement_reconciliation') }}
    where is_break

),

with_neighbours as (

    -- A transaction settled on day D by us and on D+1 by the bank leaves us one
    -- transaction up on D and one down on D+1. Counts cancel exactly; amounts only
    -- within tolerance, since each side converts at its own day's FX rate.
    select
        b.*,

        p.settlement_date is not null
            and b.recon_status = 'break' and p.recon_status = 'break'
            and b.txn_count_diff <> 0
            and b.txn_count_diff + p.txn_count_diff = 0
            and abs(b.settled_amount_diff_usd + p.settled_amount_diff_usd)
                <= greatest({{ var('recon_amount_tolerance_usd') }},
                            abs(b.settled_amount_diff_usd) * {{ var('recon_cutoff_amount_tolerance_pct') }})
            as offsets_previous_day,

        n.settlement_date is not null
            and b.recon_status = 'break' and n.recon_status = 'break'
            and b.txn_count_diff <> 0
            and b.txn_count_diff + n.txn_count_diff = 0
            and abs(b.settled_amount_diff_usd + n.settled_amount_diff_usd)
                <= greatest({{ var('recon_amount_tolerance_usd') }},
                            abs(b.settled_amount_diff_usd) * {{ var('recon_cutoff_amount_tolerance_pct') }})
            as offsets_next_day

    from breaks b
    left join breaks p
        on p.settlement_date = dateadd('day', -1, b.settlement_date)
    left join breaks n
        on n.settlement_date = dateadd('day', 1, b.settlement_date)

)

select
    settlement_date,
    recon_status,
    txn_count_diff,
    settled_amount_diff_usd,

    case
        when coalesce(offsets_previous_day, false) then dateadd('day', -1, settlement_date)
        when coalesce(offsets_next_day, false)     then dateadd('day', 1, settlement_date)
    end::date as offsetting_settlement_date,

    -- Evaluated in order. Whole-day gaps first; then the timing pattern, because a
    -- cutoff break also looks like missing or extra transactions on each day alone.
    case
        when recon_status = 'missing_bank_file'   then 'missing_bank_file'
        when recon_status = 'missing_in_ledger'   then 'ledger_day_missing'
        when coalesce(offsets_previous_day, false)
          or coalesce(offsets_next_day, false)     then 'cutoff_timing'
        when txn_count_diff < 0                    then 'ledger_missing_transactions'
        when txn_count_diff > 0                    then 'ledger_extra_transactions'
        else 'amount_mismatch'
    end as break_cause,

    -- A timing break is not an error: the money is complete across the two days and
    -- the pair clears itself. Every other cause needs someone to look.
    coalesce(offsets_previous_day, false) or coalesce(offsets_next_day, false)
        as is_self_clearing

from with_neighbours
