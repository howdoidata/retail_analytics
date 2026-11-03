"""Smoke tests for the C-2 scaffold: the package imports, the layout and the
data contract are in place, and the dbt project points at a local DuckDB file."""

import importlib
from pathlib import Path

import pytest

from retail_analytics import cli
from retail_analytics.config import DBT_DIR, DOCS_DIR, EXPORT_DIR, RAW_DATA_DIR, REPO_ROOT


@pytest.mark.parametrize("module", ["retail_analytics", "retail_analytics.generator", "retail_analytics.cli"])
def test_modules_import(module: str) -> None:
    importlib.import_module(module)


def test_data_contract_present() -> None:
    contract = (DOCS_DIR / "data-contracts.md").read_text(encoding="utf-8")
    assert contract.startswith("# Flagship data contracts")
    for mart in ("fct_signups_by_channel", "fct_visit_funnel_by_channel", "fct_customer_cohorts"):
        assert mart in contract


@pytest.mark.parametrize(
    "path",
    [
        DBT_DIR / "dbt_project.yml",
        DBT_DIR / "profiles.yml",
        DBT_DIR / "models" / "staging",
        DBT_DIR / "models" / "intermediate",
        DBT_DIR / "models" / "marts",
        DBT_DIR / "seeds",
        DBT_DIR / "macros",
        RAW_DATA_DIR / "README.md",
        EXPORT_DIR / "README.md",
        REPO_ROOT / "LICENSE",
        REPO_ROOT / "CONTRIBUTING.md",
    ],
)
def test_layout(path: Path) -> None:
    assert path.exists(), path


def test_profile_targets_local_duckdb() -> None:
    profile = (DBT_DIR / "profiles.yml").read_text(encoding="utf-8")
    assert "type: duckdb" in profile
    assert ".duckdb" in profile


def test_readme_says_data_is_synthetic() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "fictional" in readme
    assert "synthetic" in readme
    assert readme.rstrip().endswith("A How Do I Data demo project")


def test_build_uses_repo_local_profile() -> None:
    args = cli.dbt_args("build")
    assert args[0] == "build"
    assert args[args.index("--profiles-dir") + 1] == str(DBT_DIR)
    assert args[args.index("--project-dir") + 1] == str(DBT_DIR)
