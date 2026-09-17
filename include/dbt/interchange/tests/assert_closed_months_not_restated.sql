-- Control: a closed month's signed-off figures should not move. Returns every closed
-- month whose current figures differ from the version it was closed at.
--
-- Warn, not error: late data for a past month cannot be prevented, and failing the
-- build would block every current report over a month already closed. store_failures
-- keeps the offending rows in a table so the restatement is reviewed, not just logged.
{{ config(severity='warn', store_failures=true) }}

select
    period_month,
    closed_on,
    locked_at,
    locked_net_interchange_after_refunds_usd,
    current_net_interchange_after_refunds_usd,
    restatement_net_interchange_usd
from {{ ref('fct_month_end_close') }}
where is_restated
