-- One row per merchant, current state, with its MCC translated into the spend
-- category reports actually group by: "restaurants", not "5812".

select
    {{ dbt_utils.generate_surrogate_key(['m.merchant_id']) }}::varchar as merchant_key,
    m.merchant_id,
    m.merchant_name,
    -- The raw card-network text (e.g. "SQ *ACME"), kept because it is what shows up
    -- on a customer's statement and what support gets asked about.
    m.descriptor,
    m.merchant_country,
    m.mcc,
    c.mcc_description,
    c.spend_category,
    m._loaded_at_utc
from {{ ref('stg_merchants') }} m
left join {{ ref('mcc_categories') }} c
    on m.mcc = c.mcc
