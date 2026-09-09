"""CLI entry point:  python -m simulator --start 2024-01-01 --end 2024-03-31"""

import argparse

from .run import run


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="simulator",
        description="Generate raw interchange source data for a date window.",
    )
    parser.add_argument("--start", required=True, help="window start, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="window end, YYYY-MM-DD (inclusive)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="data/landing", help="output directory")
    parser.add_argument("--format", choices=["parquet", "csv"], default="parquet")
    args = parser.parse_args()

    run(start=args.start, end=args.end, seed=args.seed, out_dir=args.out, fmt=args.format)


if __name__ == "__main__":
    main()
