"""File output. Static tables go to one file; feeds are partitioned by date."""

from pathlib import Path

import pandas as pd


def write_static(df: pd.DataFrame, out_dir: str, name: str, fmt: str = "parquet") -> None:
    target = Path(out_dir) / name
    target.mkdir(parents=True, exist_ok=True)
    _write(df, target / f"{name}.{fmt}", fmt)


def write_partitioned(
    df: pd.DataFrame, out_dir: str, name: str, date_col: str, fmt: str = "parquet"
) -> None:
    base = Path(out_dir) / name
    for day, chunk in df.groupby(df[date_col].dt.normalize()):
        part_dir = base / f"dt={day.date()}"
        part_dir.mkdir(parents=True, exist_ok=True)
        _write(chunk, part_dir / f"{name}.{fmt}", fmt)


def _write(df: pd.DataFrame, path: Path, fmt: str) -> None:
    if fmt == "parquet":
        df.to_parquet(path, index=False)
    elif fmt == "csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError(f"unknown format: {fmt}")
