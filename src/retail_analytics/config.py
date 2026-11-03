"""Repo paths shared by the CLI and tests."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DBT_DIR = REPO_ROOT / "dbt"
RAW_DATA_DIR = REPO_ROOT / "data" / "raw"
EXPORT_DIR = REPO_ROOT / "data" / "export"
DOCS_DIR = REPO_ROOT / "docs"
