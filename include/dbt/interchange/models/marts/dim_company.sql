-- One row per company, current state.
--
-- region lives here and drives the interchange rate. This dimension holds today's
-- value only, and int_txn_rated rates every transaction with it. If a company ever
-- moved region, past transactions would be re-rated at the new region's rate. The
-- simulator never changes a company, so that is safe here; real data would need
-- this snapshotted like the rate tables.

select
    {{ dbt_utils.generate_surrogate_key(['company_id']) }}::varchar as company_key,
    company_id,
    company_name,
    region,
    onboarded_at,
    onboarded_at::date as onboarded_date,
    _loaded_at_utc
from {{ ref('stg_companies') }}
