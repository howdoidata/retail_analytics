"""`uv run build`: run `dbt build` on the project in `dbt/`.

Uses the repo-local profile (`dbt/profiles.yml`), so nothing in ~/.dbt is read.
The source generator (C-4) and the mart exports will be added as steps here.
"""

from __future__ import annotations

import sys

from retail_analytics.config import DBT_DIR, REPO_ROOT


def dbt_args(command: str) -> list[str]:
    """Arguments for a dbt command against the repo's project and profile."""
    return [command, "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]


def build() -> None:
    """Entry point for `uv run build`."""
    import os

    from dbt.cli.main import dbtRunner

    os.chdir(REPO_ROOT)  # profiles.yml paths are relative to the repo root
    result = dbtRunner().invoke(dbt_args("build"))
    if not result.success:
        sys.exit(1)
