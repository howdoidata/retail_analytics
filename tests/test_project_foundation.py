"""Smoke tests for the C-2 scaffold: the package imports, the layout and the
data contract are in place, and the dbt project points at a local DuckDB file.
C-12 adds the one-command run: every console script loads, `uv run build` generates
then runs dbt (stubbed here, so no extra dbt build), and dbt's default source folder
is the generator's output folder."""

import importlib
import sys
import tomllib
from importlib.metadata import EntryPoint
from pathlib import Path
from types import SimpleNamespace

import dbt.cli.main
import pytest
import yaml

from retail_analytics import cli
from retail_analytics.config import DBT_DIR, DOCS_DIR, EXPORT_DIR, RAW_DATA_DIR, REPO_ROOT
from retail_analytics.generator import DEFAULT_SEED


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


def test_default_raw_data_dir_is_the_generator_output() -> None:
    """`uv run build` runs dbt from the repo root with the default `raw_data_dir`, so it must be where
    `uv run generate` writes. Every dbt build in the other tests passes its own folder in `--vars`."""
    project = yaml.safe_load((DBT_DIR / "dbt_project.yml").read_text(encoding="utf-8"))
    assert Path(project["vars"]["raw_data_dir"]) == RAW_DATA_DIR.relative_to(REPO_ROOT)


SCRIPTS = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]


def test_console_scripts_declared() -> None:
    assert {"build", "catalog", "generate"} <= set(SCRIPTS)


@pytest.mark.parametrize("name", sorted(SCRIPTS))
def test_console_script_loads(name: str) -> None:
    target = EntryPoint(name=name, value=SCRIPTS[name], group="console_scripts").load()
    assert callable(target), SCRIPTS[name]


class FakePipeline:
    """Stands in for the generator CLI and dbt; records each call (and dbt's working directory) in order."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.dbt_success = True
        self.generator_error: Exception | None = None

    def generate(self, argv: list[str]) -> None:
        self.calls.append(("generate", argv))
        if self.generator_error:
            raise self.generator_error

    def runner(self) -> object:
        pipeline = self

        class Runner:
            def invoke(self, args: list[str]) -> SimpleNamespace:
                pipeline.calls.append(("dbt", args, Path.cwd()))
                return SimpleNamespace(success=pipeline.dbt_success)

        return Runner()


@pytest.fixture
def pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakePipeline:
    fake = FakePipeline()
    monkeypatch.setattr(cli.generator_cli, "main", fake.generate)
    monkeypatch.setattr(dbt.cli.main, "dbtRunner", fake.runner)
    monkeypatch.chdir(tmp_path)  # build() moves to the repo root; monkeypatch restores the directory
    return fake


def test_build_generates_then_runs_dbt_build_from_repo_root(pipeline: FakePipeline) -> None:
    cli.build([])
    assert pipeline.calls == [
        ("generate", ["--seed", str(DEFAULT_SEED)]),
        ("dbt", cli.dbt_args("build"), REPO_ROOT),
    ]
    assert DEFAULT_SEED == 42


def test_build_passes_seed_to_generator(pipeline: FakePipeline) -> None:
    cli.build(["--seed", "7"])
    assert [call[:2] for call in pipeline.calls] == [
        ("generate", ["--seed", "7"]),
        ("dbt", cli.dbt_args("build")),
    ]


def test_build_console_script_reads_command_line(
    pipeline: FakePipeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", ["build", "--seed", "7"])
    cli.build()
    assert pipeline.calls[0] == ("generate", ["--seed", "7"])


def test_build_exits_1_when_dbt_fails(pipeline: FakePipeline) -> None:
    pipeline.dbt_success = False
    with pytest.raises(SystemExit) as exit_info:
        cli.build([])
    assert exit_info.value.code == 1
    assert [call[0] for call in pipeline.calls] == ["generate", "dbt"]


def test_build_skips_dbt_when_generator_raises(pipeline: FakePipeline) -> None:
    pipeline.generator_error = OSError("disk full")
    with pytest.raises(OSError, match="disk full"):
        cli.build([])
    assert [call[0] for call in pipeline.calls] == ["generate"]
