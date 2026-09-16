-- Money cannot settle without first clearing. Returns any settled transaction
-- that has no clearing event.
select transaction_id, settled_at, clearing_count
from {{ ref('int_transaction_lifecycle') }}
where settled_at is not null
  and coalesce(clearing_count, 0) = 0
