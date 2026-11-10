# AGENTS.md

Flagship How Do I Data demo: synthetic retail data for Switchback Outfitters (a fictional outdoor gear
shop) built into acquisition views by channel. Python source lives in `src/retail_analytics/`
(the generator in `src/retail_analytics/generator/`), scripts in `scripts/`, the dbt project in `dbt/`,
tests in `tests/`, docs in `docs/`.

Set up and check with:

```bash
uv sync && uv run ruff check . && uv run pytest
uv run dbt parse --project-dir dbt --profiles-dir dbt
uv run catalog --check
```

`uv run generate [--seed N]` writes the synthetic source CSVs to `data/raw/` (seed 42 by default).
`uv run build [--seed N]` is the one-command run: it writes the CSVs to `data/raw/` as `generate` does,
runs `dbt build` on every layer with its tests, using the repo-local profile, into
`data/retail_analytics.duckdb`, then writes the three marts to `data/export/*.csv` as `uv run export` does
(its own process, since dbt holds the database). `uv run export` repeats just that last step. CI runs
`uv run generate`, then `uv run build`, after the checks.

Shapes are fixed by `docs/data-contracts.md` (a copy of the spec; change the spec, not this file).
Every story leaves its build record per `docs/build-record/convention.md`.
Standards and review rules: `CONTRIBUTING.md`. Everything committed is public: synthetic data only,
no secrets, no internal or client names.

## Working efficiently

Several agents may work in parallel, each in its own git worktree with its own `.venv`, `data/`, and
DuckDB file. Keep each one's context small:

- **Tests while iterating:** run only the files for what you changed, e.g.
  `uv run pytest -q -x tests/test_export.py` or `-k <name>`. Most tests start dbt (about 6 s each) and
  the full suite takes 5 to 8 minutes, so run it once, before committing.
- **Long output goes to a file:** `uv run pytest -q > .scratch/pytest.log 2>&1; tail -5 .scratch/pytest.log`
  (`.scratch/` is git-ignored). The same for `uv run build` and dbt; read only the tail or `grep` for
  `FAIL|ERROR|Error`. Run the full suite in the background when your tool allows it.
- **Don't read generated or bulky files whole:** `uv.lock`, `CATALOG.md` (generated: run
  `uv run catalog`, then `uv run catalog --check`), `data/`, `dbt/target/`, `dbt/logs/`. Grep them for
  the line you need.
- **Read the part you need:** `docs/data-contracts.md` by section; in `docs/build-record/`, the
  convention, your own story's record, and one recent record as a model, not every record.
- **Git:** `git log --oneline -5` and `git show --stat` before full diffs; `git diff -- <path>` for one file.
