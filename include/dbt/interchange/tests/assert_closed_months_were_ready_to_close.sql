-- Control: a month may only be closed when it is ready. Fails the build (error) if a
-- closed month is missing its month-end bank file or has unexplained breaks.
--
-- Error, not warn: closing a month is a deliberate edit to close_calendar, so this is
-- the point where the close process refuses a bad close rather than recording it.
select
    period_month,
    closed_on,
    close_blocked_reason,
    unexplained_break_days
from {{ ref('fct_close_readiness') }}
where is_closed
  and not is_ready_to_close
