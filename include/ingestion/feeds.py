"""Registry of the raw feeds the simulator lands.

This is the single definition of what INTERCHANGE_RAW.SIM looks like: each
table's columns and types, how every column is pulled out of Parquet during
COPY, and the column contract a landing file must satisfy. The DDL and COPY
statements are rendered from here, so the table shape and the load can't drift
apart.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

RAW_DATABASE = "interchange_raw"
RAW_SCHEMA = "sim"
STAGE = f"{RAW_DATABASE}.{RAW_SCHEMA}.landing"

# Owned by interchange_role: the ff_parquet from bootstrap belongs to ACCOUNTADMIN
# and the role can't use it. use_logical_type is required, otherwise Parquet
# timestamps arrive as raw epoch-microsecond integers.
FILE_FORMAT = f"{RAW_DATABASE}.{RAW_SCHEMA}.ff_parquet_logical"
AUDIT_TABLE = f"{RAW_DATABASE}.{RAW_SCHEMA}.ingest_audit"

METADATA_COLUMNS = ("_loaded_at", "_batch_id", "_source_file")

_BATCH_ID_RE = re.compile(r"^[A-Za-z0-9_.:+\-]{1,200}$")
_STAGE_PATH_RE = re.compile(r"^[A-Za-z0-9_=./\-]+$")


class SchemaDriftError(ValueError):
    """A landing file's columns don't match the feed contract."""


@dataclass(frozen=True)
class Column:
    name: str
    sf_type: str

    def select_expr(self) -> str:
        if self.sf_type == "date":
            # Logical Parquet timestamps surface as strings with a time part
            # ("2024-02-15 00:00:00.000"). A direct ::date on that fails, so
            # cast through timestamp_ntz first.
            return f"$1:{self.name}::timestamp_ntz::date"
        return f"$1:{self.name}::{self.sf_type}"


@dataclass(frozen=True)
class Feed:
    name: str
    partitioned: bool
    columns: tuple[Column, ...]

    @property
    def table(self) -> str:
        return f"{RAW_DATABASE}.{RAW_SCHEMA}.{self.name}"

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]


def _cols(*pairs: tuple[str, str]) -> tuple[Column, ...]:
    return tuple(Column(name, sf_type) for name, sf_type in pairs)


FEEDS: tuple[Feed, ...] = (
    Feed("companies", partitioned=False, columns=_cols(
        ("company_id", "varchar"),
        ("company_name", "varchar"),
        ("region", "varchar"),
        ("onboarded_at", "timestamp_ntz"),
    )),
    Feed("cards", partitioned=False, columns=_cols(
        ("card_id", "varchar"),
        ("company_id", "varchar"),
        ("card_program", "varchar"),
        ("issued_at", "timestamp_ntz"),
        ("status", "varchar"),
    )),
    Feed("merchants", partitioned=False, columns=_cols(
        ("merchant_id", "varchar"),
        ("merchant_name", "varchar"),
        ("mcc", "varchar"),
        ("merchant_country", "varchar"),
        ("descriptor", "varchar"),
    )),
    Feed("interchange_rates", partitioned=False, columns=_cols(
        ("mcc", "varchar"),
        ("card_program", "varchar"),
        ("region", "varchar"),
        ("bps", "number(6,1)"),
        ("valid_from", "date"),
        ("valid_to", "date"),
    )),
    Feed("rewards_rates", partitioned=False, columns=_cols(
        ("spend_category", "varchar"),
        ("cashback_pct", "number(6,4)"),
        ("valid_from", "date"),
        ("valid_to", "date"),
    )),
    Feed("fx_rates", partitioned=True, columns=_cols(
        ("currency", "varchar"),
        ("rate_date", "date"),
        ("usd_rate", "number(12,6)"),
    )),
    Feed("network_settlement", partitioned=True, columns=_cols(
        ("settlement_date", "date"),
        ("file_id", "varchar"),
        ("total_settled_amount_usd", "number(18,2)"),
        ("total_txn_count", "number(38,0)"),
    )),
    Feed("card_events", partitioned=True, columns=_cols(
        ("event_id", "varchar"),
        ("event_ts", "timestamp_ntz"),
        ("ingested_at", "timestamp_ntz"),
        ("transaction_id", "varchar"),
        ("card_id", "varchar"),
        ("merchant_id", "varchar"),
        ("mcc", "varchar"),
        ("event_type", "varchar"),
        ("amount", "number(18,2)"),
        ("currency", "varchar"),
        ("original_transaction_id", "varchar"),
    )),
)

FEEDS_BY_NAME: dict[str, Feed] = {feed.name: feed for feed in FEEDS}


@dataclass(frozen=True)
class LandingFile:
    feed: str
    local_path: Path
    stage_dir: str             # e.g. "card_events/dt=2024-01-15"
    partition: date | None

    @property
    def stage_path(self) -> str:
        """Path relative to the stage root. Matches metadata$filename after COPY."""
        return f"{self.stage_dir}/{self.local_path.name}"


def discover_files(
    feed: Feed, landing_dir: Path | str, start: date | None = None, end: date | None = None
) -> list[LandingFile]:
    """Landing files for a feed. The date window only applies to partitioned feeds."""
    base = Path(landing_dir) / feed.name
    if not feed.partitioned:
        return [LandingFile(feed.name, p, feed.name, None) for p in sorted(base.glob("*.parquet"))]

    files: list[LandingFile] = []
    for part_dir in sorted(base.glob("dt=*")):
        day = date.fromisoformat(part_dir.name.removeprefix("dt="))
        if (start and day < start) or (end and day > end):
            continue
        stage_dir = f"{feed.name}/{part_dir.name}"
        files.extend(LandingFile(feed.name, p, stage_dir, day) for p in sorted(part_dir.glob("*.parquet")))
    return files


def check_contract(feed: Feed, path: Path) -> None:
    """Fail loudly if a file's columns differ from the feed definition."""
    import pyarrow.parquet as pq

    actual = pq.read_schema(path).names
    missing = [c for c in feed.column_names if c not in actual]
    unexpected = [c for c in actual if c not in feed.column_names]
    if missing or unexpected:
        raise SchemaDriftError(
            f"{feed.name}: {path} missing={missing} unexpected={unexpected}"
        )


def validate_batch_id(batch_id: str) -> str:
    if not _BATCH_ID_RE.fullmatch(batch_id or ""):
        raise ValueError(f"unsafe batch id: {batch_id!r}")
    return batch_id


def render_create_table(feed: Feed) -> str:
    columns = [f"    {c.name} {c.sf_type}" for c in feed.columns]
    columns += ["    _loaded_at timestamp_ntz", "    _batch_id varchar", "    _source_file varchar"]
    body = ",\n".join(columns)
    return (
        f"create table if not exists {feed.table} (\n{body}\n)\n"
        f"comment = 'Raw {feed.name} from the simulator landing zone. Append-only.'"
    )


def render_setup_sql() -> list[str]:
    statements = [
        f"create file format if not exists {FILE_FORMAT} type = parquet use_logical_type = true",
        f"""create table if not exists {AUDIT_TABLE} (
    batch_id varchar not null,
    feed varchar not null,
    source_file varchar not null,
    file_md5 varchar not null,
    status varchar not null,
    expected_rows number,
    rows_loaded number,
    first_error varchar,
    recorded_at timestamp_ntz not null default current_timestamp()
)
comment = 'One row per landing file per load attempt. Drives file-level idempotency.'""",
    ]
    statements.extend(render_create_table(feed) for feed in FEEDS)
    return statements


def render_copy(feed: Feed, batch_id: str, stage_paths: list[str]) -> str:
    validate_batch_id(batch_id)
    for path in stage_paths:
        if not _STAGE_PATH_RE.fullmatch(path):
            raise ValueError(f"unsafe stage path: {path!r}")

    target_columns = ", ".join([*feed.column_names, *METADATA_COLUMNS])
    selects = ",\n        ".join(c.select_expr() for c in feed.columns)
    files = ",\n    ".join(f"'{p}'" for p in stage_paths)
    return f"""copy into {feed.table} ({target_columns})
from (
    select
        {selects},
        current_timestamp()::timestamp_ntz,
        '{batch_id}',
        metadata$filename
    from @{STAGE}
)
files = (
    {files}
)
file_format = (format_name = '{FILE_FORMAT}')
on_error = abort_statement"""
