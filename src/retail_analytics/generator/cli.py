"""`uv run generate [--seed N]`: write the source CSVs to `data/raw/`."""

from __future__ import annotations

import argparse

from retail_analytics import config
from retail_analytics.generator import DEFAULT_SEED, generate


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="generate", description="Write the synthetic source CSVs.")
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED, help=f"random seed (default {DEFAULT_SEED})"
    )
    args = parser.parse_args(argv)
    report = generate(config.RAW_DATA_DIR, args.seed)
    print(f"Wrote source CSVs to {config.RAW_DATA_DIR} (seed {args.seed})")
    for item, rows in report.items():
        print(f"  {item}: {rows}")
