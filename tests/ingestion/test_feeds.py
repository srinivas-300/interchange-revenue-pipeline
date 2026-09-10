"""Unit tests for the raw feed registry. No Snowflake or Airflow needed."""

from datetime import date

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from include.ingestion.feeds import (
    FEEDS,
    FEEDS_BY_NAME,
    SchemaDriftError,
    check_contract,
    discover_files,
    render_copy,
    render_create_table,
    validate_batch_id,
)


@pytest.fixture(scope="module")
def landing(tmp_path_factory):
    pytest.importorskip("faker")  # simulator deps aren't in the Airflow image
    from simulator import run

    out = tmp_path_factory.mktemp("landing")
    run(start="2024-01-01", end="2024-01-05", seed=7, out_dir=str(out))
    return out


def test_simulator_output_satisfies_every_feed_contract(landing):
    for feed in FEEDS:
        files = discover_files(feed, landing)
        assert files, f"simulator produced no files for {feed.name}"
        for f in files:
            check_contract(feed, f.local_path)


def test_schema_drift_is_rejected(tmp_path):
    path = tmp_path / "fx_rates.parquet"
    pq.write_table(pa.table({"currency": ["EUR"], "usd_rate": [1.08], "extra": [1]}), path)
    with pytest.raises(SchemaDriftError, match=r"missing=\['rate_date'\] unexpected=\['extra'\]"):
        check_contract(FEEDS_BY_NAME["fx_rates"], path)


def test_date_window_scopes_partitioned_feeds_only(landing):
    window = (date(2024, 1, 2), date(2024, 1, 3))

    events = discover_files(FEEDS_BY_NAME["card_events"], landing, *window)
    assert {f.partition for f in events} == set(window)
    assert all(f.stage_path == f"card_events/dt={f.partition}/card_events.parquet" for f in events)

    merchants = discover_files(FEEDS_BY_NAME["merchants"], landing, *window)
    assert [f.stage_path for f in merchants] == ["merchants/merchants.parquet"]


def test_date_columns_cast_through_timestamp():
    sql = render_copy(
        FEEDS_BY_NAME["interchange_rates"], "batch-1", ["interchange_rates/interchange_rates.parquet"]
    )
    assert "$1:valid_to::timestamp_ntz::date" in sql
    assert "$1:bps::number(6,1)" in sql


def test_copy_stamps_load_metadata_and_aborts_on_error():
    sql = render_copy(
        FEEDS_BY_NAME["card_events"],
        "manual__2026-09-10T10:00:00+00:00",
        ["card_events/dt=2024-01-15/card_events.parquet"],
    )
    assert "original_transaction_id, _loaded_at, _batch_id, _source_file)" in sql
    assert "metadata$filename" in sql
    assert "'card_events/dt=2024-01-15/card_events.parquet'" in sql
    assert "on_error = abort_statement" in sql


@pytest.mark.parametrize("bad", ["x'; drop table t; --", "", "has space"])
def test_unsafe_batch_ids_are_rejected(bad):
    with pytest.raises(ValueError):
        validate_batch_id(bad)


def test_unsafe_stage_paths_are_rejected():
    with pytest.raises(ValueError):
        render_copy(FEEDS_BY_NAME["companies"], "b1", ["companies/x.parquet'); drop table t; --"])


def test_every_raw_table_carries_load_metadata():
    for feed in FEEDS:
        ddl = render_create_table(feed)
        for column in ("_loaded_at timestamp_ntz", "_batch_id varchar", "_source_file varchar"):
            assert column in ddl, f"{feed.name} is missing {column}"
