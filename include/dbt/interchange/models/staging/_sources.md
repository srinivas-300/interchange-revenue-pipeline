{% docs sim_raw_feeds %}

Raw simulator feeds loaded by `ingest_raw` into `INTERCHANGE_RAW.SIM`.

Append-only by design: every load is kept, so duplicate rows and re-sent files are
all still here. Each row carries `_loaded_at`, `_batch_id` and `_source_file`, so any
row can be traced back to the file that delivered it.

The staging layer is what cleans this up, with light cleaning only:

- **deduplicated** — one row per key, keeping the most recently loaded version
- **typed and renamed** — stable column names and types, enforced by contracts
- **time-zone corrected** — `_loaded_at_utc` instead of the account-local `_loaded_at`
- **lineage kept** — `_batch_id` and `_source_file` carried through

No joins and no business logic; those belong in intermediate. Nothing downstream
should read these raw tables directly.

{% enddocs %}
