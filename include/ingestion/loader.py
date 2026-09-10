"""Load landing files into INTERCHANGE_RAW.SIM.

Takes any Snowflake DB-API connection, so the CLI (env vars) and the Airflow
DAG (SnowflakeHook) run exactly the same load path.

Idempotency has two layers:
  1. ingest_audit: a file whose (path, md5) is already recorded as loaded is
     never staged or copied again. This guard never expires.
  2. COPY load metadata: Snowflake itself skips files it loaded in the last 64
     days, which covers an audit write that was lost after a successful COPY.

A file with the same path but new content (a re-sent, corrected partition) has a
new md5, so it loads again as a new batch. Raw stays append-only; staging keeps
the latest version.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from .feeds import (
    AUDIT_TABLE,
    FEEDS,
    FEEDS_BY_NAME,
    STAGE,
    Feed,
    check_contract,
    discover_files,
    render_copy,
    render_setup_sql,
    validate_batch_id,
)

log = logging.getLogger(__name__)

COPY_FILE_LIMIT = 1000  # max files Snowflake accepts in one COPY ... FILES = (...)
_DONE_STATUSES = ("LOADED", "ALREADY_LOADED")


class IngestionError(RuntimeError):
    pass


@dataclass
class FeedLoadResult:
    feed: str
    batch_id: str
    files_found: int = 0
    files_skipped: int = 0               # already recorded in ingest_audit
    files_loaded: int = 0
    files_already_in_snowflake: int = 0  # not in the audit, but COPY metadata had it
    rows_loaded: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def ensure_raw_objects(conn) -> None:
    with conn.cursor() as cur:
        for statement in render_setup_sql():
            cur.execute(statement)


def load_all(
    conn,
    landing_dir: Path | str,
    batch_id: str,
    feed_names: list[str] | None = None,
    start: date | None = None,
    end: date | None = None,
) -> list[FeedLoadResult]:
    unknown = sorted(set(feed_names or []) - FEEDS_BY_NAME.keys())
    if unknown:
        raise IngestionError(f"unknown feeds: {unknown}")
    feeds = [FEEDS_BY_NAME[n] for n in feed_names] if feed_names else list(FEEDS)

    ensure_raw_objects(conn)
    return [load_feed(conn, feed, landing_dir, batch_id, start, end) for feed in feeds]


def load_feed(
    conn,
    feed: Feed,
    landing_dir: Path | str,
    batch_id: str,
    start: date | None = None,
    end: date | None = None,
) -> FeedLoadResult:
    validate_batch_id(batch_id)
    result = FeedLoadResult(feed=feed.name, batch_id=batch_id)

    files = discover_files(feed, landing_dir, start, end)
    result.files_found = len(files)
    if not files:
        if not feed.partitioned:
            raise IngestionError(f"{feed.name}: no landing file under {Path(landing_dir) / feed.name}")
        log.info("%s: no partitions between %s and %s", feed.name, start, end)
        return result

    # Contract-check and fingerprint every file before touching Snowflake.
    fingerprints: dict[str, tuple[str, int]] = {}
    for f in files:
        check_contract(feed, f.local_path)
        fingerprints[f.stage_path] = (_md5(f.local_path), _parquet_rows(f.local_path))

    audit_rows: list[tuple] = []
    with conn.cursor() as cur:
        cur.execute(f"alter session set query_tag = 'ingest_raw:{feed.name}'")

        done = _already_loaded(cur, feed.name)
        pending = [f for f in files if (f.stage_path, fingerprints[f.stage_path][0]) not in done]
        result.files_skipped = len(files) - len(pending)
        if not pending:
            log.info("%s: all %d files already loaded", feed.name, len(files))
            return result

        for f in pending:
            _put(cur, f.local_path, f.stage_dir)

        for i in range(0, len(pending), COPY_FILE_LIMIT):
            chunk = pending[i : i + COPY_FILE_LIMIT]
            copied = _copy(cur, feed, batch_id, [f.stage_path for f in chunk])

            for f in chunk:
                md5, expected = fingerprints[f.stage_path]
                row = copied.get(f.stage_path)
                if row is None:
                    status, loaded, error = "ALREADY_LOADED", None, None
                    result.files_already_in_snowflake += 1
                else:
                    loaded = int(row["rows_loaded"] or 0)
                    error = row.get("first_error")
                    if row["status"] != "LOADED":
                        status = row["status"]
                    elif loaded != expected:
                        status = "ROWCOUNT_MISMATCH"
                    else:
                        status = "LOADED"
                        result.files_loaded += 1
                        result.rows_loaded += loaded
                audit_rows.append((batch_id, feed.name, f.stage_path, md5, status, expected, loaded, error))

        _write_audit(cur, audit_rows)

    failed = [r for r in audit_rows if r[4] not in _DONE_STATUSES]
    if failed:
        detail = "; ".join(f"{r[2]} status={r[4]} expected={r[5]} loaded={r[6]}" for r in failed[:5])
        raise IngestionError(f"{feed.name}: {len(failed)} file(s) did not load cleanly: {detail}")

    log.info(
        "%s: loaded %d files / %d rows, skipped %d, already in Snowflake %d",
        feed.name, result.files_loaded, result.rows_loaded,
        result.files_skipped, result.files_already_in_snowflake,
    )
    return result


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()


def _parquet_rows(path: Path) -> int:
    import pyarrow.parquet as pq

    return pq.ParquetFile(path).metadata.num_rows


def _already_loaded(cur, feed_name: str) -> set[tuple[str, str]]:
    cur.execute(
        f"select source_file, file_md5 from {AUDIT_TABLE} "
        "where feed = %s and status in ('LOADED', 'ALREADY_LOADED')",
        (feed_name,),
    )
    return {(source_file, md5) for source_file, md5 in cur.fetchall()}


def _put(cur, local_path: Path, stage_dir: str) -> None:
    uri = f"file://{local_path.resolve().as_posix()}"
    cur.execute(f"put '{uri}' @{STAGE}/{stage_dir}/ auto_compress = false overwrite = true")
    statuses = {row[6] for row in cur.fetchall()}
    if not statuses <= {"UPLOADED", "SKIPPED"}:
        raise IngestionError(f"PUT {local_path} returned {statuses}")


def _copy(cur, feed: Feed, batch_id: str, stage_paths: list[str]) -> dict[str, dict]:
    cur.execute(render_copy(feed, batch_id, stage_paths))
    columns = [d[0].lower() for d in cur.description]
    if "file" not in columns:
        # "Copy executed with 0 files processed." -> every file was already loaded
        return {}
    records = (dict(zip(columns, row)) for row in cur.fetchall())
    return {_stage_relative(rec["file"]): rec for rec in records}


def _stage_relative(reported: str) -> str:
    """COPY reports internal-stage files as '<stage>/<path>'; strip the stage name."""
    prefix = STAGE.rsplit(".", 1)[-1] + "/"
    return reported[len(prefix):] if reported.startswith(prefix) else reported


def _write_audit(cur, rows: list[tuple]) -> None:
    if not rows:
        return
    cur.executemany(
        f"insert into {AUDIT_TABLE} "
        "(batch_id, feed, source_file, file_md5, status, expected_rows, rows_loaded, first_error) "
        "values (%s, %s, %s, %s, %s, %s, %s, %s)",
        rows,
    )
