"""
### ingest_raw

Loads simulator output from the landing zone into `INTERCHANGE_RAW.SIM`.

1. **ensure_raw_objects** creates the Parquet file format, the eight raw tables,
   and `ingest_audit` if they don't exist yet.
2. **load_feed** runs once per feed (dynamic task mapping). For each Parquet
   file it checks the column contract, skips anything `ingest_audit` already
   has as loaded, PUTs the rest to `@interchange_raw.sim.landing`, then
   `COPY INTO`s them with `_loaded_at` / `_batch_id` / `_source_file`. Loaded
   rows are checked against the Parquet row count.
3. **publish** runs only when every feed loaded cleanly, and updates the
   `raw_interchange_sim` asset so downstream DAGs can trigger off it.

Re-running any window is safe because files that are already loaded get skipped.
The `start` / `end` params (inclusive) scope the date-partitioned feeds; the
static feeds are checked on every run.
"""

from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

from airflow.sdk import Asset, Param, dag, get_current_context, task
from pendulum import datetime

from include.ingestion.feeds import FEEDS

LANDING_DIR = Path("/usr/local/airflow/data/landing")
SNOWFLAKE_CONN_ID = "snowflake_default"
RAW_ASSET = Asset("raw_interchange_sim")


def _connect():
    from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

    return SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID).get_conn()


@dag(
    dag_id="ingest_raw",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    params={
        "start": Param("2024-01-01", type="string", format="date", description="first partition date, inclusive"),
        "end": Param("2024-03-31", type="string", format="date", description="last partition date, inclusive"),
    },
    default_args={"owner": "data-eng", "retries": 2, "retry_delay": timedelta(minutes=2)},
    tags=["ingestion", "raw", "snowflake"],
    doc_md=__doc__,
)
def ingest_raw():
    @task
    def ensure_raw_objects() -> None:
        from include.ingestion.loader import ensure_raw_objects as ensure

        with closing(_connect()) as conn:
            ensure(conn)

    @task(max_active_tis_per_dagrun=3)
    def load_feed(feed_name: str) -> dict:
        from include.ingestion.feeds import FEEDS_BY_NAME
        from include.ingestion.loader import load_feed as load

        ctx = get_current_context()
        with closing(_connect()) as conn:
            result = load(
                conn,
                FEEDS_BY_NAME[feed_name],
                LANDING_DIR,
                batch_id=ctx["run_id"],
                start=date.fromisoformat(ctx["params"]["start"]),
                end=date.fromisoformat(ctx["params"]["end"]),
            )
        return result.as_dict()

    @task(outlets=[RAW_ASSET])
    def publish(results: list[dict]) -> None:
        import logging

        log = logging.getLogger(__name__)
        for r in results:
            log.info(
                "%-20s found=%s skipped=%s loaded=%s already_in_snowflake=%s rows=%s",
                r["feed"], r["files_found"], r["files_skipped"], r["files_loaded"],
                r["files_already_in_snowflake"], r["rows_loaded"],
            )
        log.info("rows loaded this run: %s", sum(r["rows_loaded"] for r in results))

    loaded = load_feed.expand(feed_name=[feed.name for feed in FEEDS])
    ensure_raw_objects() >> loaded
    publish(loaded)


ingest_raw()
