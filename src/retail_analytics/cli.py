"""`uv run build [--seed N]`: the one-command run.

Writes the synthetic source CSVs to `data/raw/` (seed 42 by default) with the generator's CLI, the same
step as `uv run generate`, then runs `dbt build` on every layer of the project in `dbt/` with its tests.
dbt uses the repo-local profile (`dbt/profiles.yml`), so nothing in ~/.dbt is read, and builds into
`RETAIL_DUCKDB_PATH` when set (default `data/retail_analytics.duckdb`). It reads the default
`raw_data_dir` (`data/raw`), so the CSVs just written are the ones built. Exits 1 when any dbt node fails;
a generator error propagates before dbt runs.
"""

from __future__ import annotations

import argparse
import os
import sys

from retail_analytics.config import DBT_DIR, REPO_ROOT
from retail_analytics.generator import DEFAULT_SEED
from retail_analytics.generator import cli as generator_cli


def dbt_args(command: str) -> list[str]:
    """Arguments for a dbt command against the repo's project and profile."""
    return [command, "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]


def build(argv: list[str] | None = None) -> None:
    """Entry point for `uv run build [--seed N]`: generate the CSVs, then `dbt build`."""
    parser = argparse.ArgumentParser(
        prog="build", description="Write the synthetic source CSVs, then dbt build every layer."
    )
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED, help=f"random seed (default {DEFAULT_SEED})"
    )
    args = parser.parse_args(argv)

    generator_cli.main(["--seed", str(args.seed)])

    # Stays inside the function: dbt is slow to import, and tests stub dbt.cli.main.dbtRunner.
    from dbt.cli.main import dbtRunner

    os.chdir(REPO_ROOT)  # profiles.yml and raw_data_dir paths are relative to the repo root
    result = dbtRunner().invoke(dbt_args("build"))
    if not result.success:
        sys.exit(1)
