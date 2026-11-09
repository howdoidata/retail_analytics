"""`uv run build [--seed N]`: the one-command run.

Writes the synthetic source CSVs to `data/raw/` (seed 42 by default) with the generator's CLI, the same
step as `uv run generate`, then runs `dbt build` on every layer of the project in `dbt/` with its tests.
dbt uses the repo-local profile (`dbt/profiles.yml`), so nothing in ~/.dbt is read, and builds into
`RETAIL_DUCKDB_PATH` when set (default `data/retail_analytics.duckdb`). It reads the default
`raw_data_dir` (`data/raw`), so the CSVs just written are the ones built. Last it writes the mart CSVs to
`data/export/` as `uv run export` does, so one command takes the repo from nothing to the files the dashboard
reads. Exits 1 when any dbt node fails, and with the export's own code when that fails; a generator error
propagates before dbt runs, and a dbt failure stops the export. dbt and the export each run in a child
process, because dbt-duckdb holds the database until the process that ran dbt exits.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from retail_analytics.config import DBT_DIR, REPO_ROOT
from retail_analytics.generator import DEFAULT_SEED
from retail_analytics.generator import cli as generator_cli


def dbt_args(command: str) -> list[str]:
    """Arguments for a dbt command against the repo's project and profile."""
    return [command, "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]


def dbt_command(command: str) -> list[str]:
    """A dbt command as a child process of this interpreter, so it runs under the same environment."""
    return [sys.executable, "-m", "dbt.cli.main", *dbt_args(command)]


def export_command() -> list[str]:
    """The export as a child process of this interpreter, so it runs under the same environment."""
    return [sys.executable, "-m", "retail_analytics.export"]


def run_step(command: list[str]) -> int:
    """Run one step in its own process from the repo root, where profiles.yml and raw_data_dir paths
    resolve, and return its exit code."""
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode


def build(argv: list[str] | None = None) -> None:
    """Entry point for `uv run build [--seed N]`: the CSVs, `dbt build`, then the export."""
    parser = argparse.ArgumentParser(
        prog="build",
        description="Write the synthetic source CSVs, dbt build every layer, then export the marts.",
    )
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED, help=f"random seed (default {DEFAULT_SEED})"
    )
    args = parser.parse_args(argv)

    generator_cli.main(["--seed", str(args.seed)])

    # dbt runs in its own process: dbt-duckdb keeps the database open read-write until the process that
    # ran dbt exits, and DuckDB then refuses the export's read-only open, even from another process.
    if run_step(dbt_command("build")):
        sys.exit(1)

    code = run_step(export_command())
    if code:
        sys.exit(code)
