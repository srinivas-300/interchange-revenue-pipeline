-- Two versions of the same rate must never cover the same day, otherwise the
-- as-of join in intermediate would match two rates. Returns the overlapping pairs.
select
    a.mcc,
    a.card_program,
    a.region,
    a.valid_from,
    a.valid_to,
    b.valid_from as overlapping_valid_from
from {{ ref('stg_interchange_rates') }} a
join {{ ref('stg_interchange_rates') }} b
    on  a.mcc = b.mcc
    and a.card_program = b.card_program
    and a.region = b.region
    and a.valid_from < b.valid_from
    and (a.valid_to is null or a.valid_to > b.valid_from)
