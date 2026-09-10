"""Command-line entry point for raw ingestion. Run from the repo root.

    python -m include.ingestion ddl
    python -m include.ingestion load --start 2024-01-01 --end 2024-03-31
    python -m include.ingestion load --feeds card_events --start 2024-01-15 --end 2024-01-15
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from .feeds import FEEDS, RAW_DATABASE, RAW_SCHEMA, render_setup_sql
from .loader import FeedLoadResult, load_all

REQUIRED_ENV = ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PRIVATE_KEY_PATH", "SNOWFLAKE_ROLE")


def _fill_env_from_file(path: Path) -> None:
    """Set any variable from a KEY=VALUE file that isn't already in the environment."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _connect():
    import snowflake.connector

    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        sys.exit(f"missing env vars: {', '.join(missing)}")
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key_file=os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ.get("SNOWFLAKE_INGEST_WAREHOUSE", "ingest_wh"),
        database=RAW_DATABASE,
        schema=RAW_SCHEMA,
        session_parameters={"QUERY_TAG": "ingest_raw:cli"},
    )


def _print_summary(results: list[FeedLoadResult]) -> None:
    header = f"{'feed':<20} {'found':>6} {'skipped':>8} {'loaded':>7} {'in_sf':>6} {'rows':>9}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r.feed:<20} {r.files_found:>6} {r.files_skipped:>8} {r.files_loaded:>7} "
            f"{r.files_already_in_snowflake:>6} {r.rows_loaded:>9,}"
        )
    print("-" * len(header))
    print(f"{'total rows loaded':<50} {sum(r.rows_loaded for r in results):>9,}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m include.ingestion")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ddl", help="print the raw-layer setup DDL")

    load = sub.add_parser("load", help="load landing files into INTERCHANGE_RAW.SIM")
    load.add_argument("--start", type=date.fromisoformat, help="first partition date (inclusive)")
    load.add_argument("--end", type=date.fromisoformat, help="last partition date (inclusive)")
    load.add_argument("--feeds", nargs="+", choices=[f.name for f in FEEDS], help="default: all")
    load.add_argument("--landing-dir", type=Path, default=Path("data/landing"))
    load.add_argument("--batch-id", help="default: cli-<utc timestamp>")
    load.add_argument("--env-file", type=Path, default=Path(".env"))
    args = parser.parse_args(argv)

    if args.command == "ddl":
        print(";\n\n".join(render_setup_sql()) + ";")
        return

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for noisy in ("snowflake", "botocore", "boto3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _fill_env_from_file(args.env_file)
    batch_id = args.batch_id or "cli-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    conn = _connect()
    try:
        results = load_all(conn, args.landing_dir, batch_id, args.feeds, args.start, args.end)
    finally:
        conn.close()
    print(f"\nbatch {batch_id}")
    _print_summary(results)


if __name__ == "__main__":
    main()
