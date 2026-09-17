-- One row per card, current state. company_key is carried so a card rolls up to
-- its company through the dimensions, without going back to staging.

select
    {{ dbt_utils.generate_surrogate_key(['c.card_id']) }}::varchar     as card_key,
    c.card_id,
    {{ dbt_utils.generate_surrogate_key(['c.company_id']) }}::varchar  as company_key,
    c.company_id,
    c.card_program,
    c.card_program = 'VISA_COMMERCIAL_PREMIUM'                         as is_premium,
    c.status,
    c.issued_at,
    c.issued_at::date                                                  as issued_date,
    c._loaded_at_utc
from {{ ref('stg_cards') }} c
