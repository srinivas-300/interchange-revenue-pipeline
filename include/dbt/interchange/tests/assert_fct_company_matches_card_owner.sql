-- The fact's company_key must be the company that owns the card in dim_card. If
-- the two disagree, company revenue reports credit money to the wrong customer.
select
    f.transaction_id,
    f.company_key as fact_company_key,
    c.company_key as card_owner_company_key
from {{ ref('fct_interchange_revenue') }} f
join {{ ref('dim_card') }} c
    on f.card_key = c.card_key
where f.company_key <> c.company_key
