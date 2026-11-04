# AGENTS.md

Flagship How Do I Data demo: synthetic retail data for Switchback Outfitters (a fictional outdoor gear
shop) built into acquisition views by channel. Python source lives in `src/retail_analytics/`
(the generator in `src/retail_analytics/generator/`), scripts in `scripts/`, the dbt project in `dbt/`,
tests in `tests/`, docs in `docs/`.

Set up and check with:

```bash
uv sync && uv run ruff check . && uv run pytest
uv run dbt parse --project-dir dbt --profiles-dir dbt
```

`uv run generate [--seed N]` writes the synthetic source CSVs to `data/raw/` (seed 42 by default).
`uv run build [--seed N]` is the one-command run: it writes the CSVs to `data/raw/` as `generate` does, then
runs `dbt build` on every layer with its tests, using the repo-local profile, into
`data/retail_analytics.duckdb`. CI runs `uv run generate`, then `uv run build`, after the checks.

Shapes are fixed by `docs/data-contracts.md` (a copy of the spec; change the spec, not this file).
Every story leaves its build record per `docs/build-record/convention.md`.
Standards and review rules: `CONTRIBUTING.md`. Everything committed is public: synthetic data only,
no secrets, no internal or client names.
