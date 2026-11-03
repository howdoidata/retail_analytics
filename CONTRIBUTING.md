# Contributing and coding standards

This repo is the flagship How Do I Data demo. It is public: everything committed must be
public-safe (no secrets, no internal or client names, no real customer data). All data is
synthetic and every result is simulated.

## Setup

```bash
uv sync                 # Python 3.12, dbt-core, dbt-duckdb, duckdb, pytest, ruff
uv run ruff check .     # lint
uv run pytest           # Python tests
uv run dbt parse --project-dir dbt --profiles-dir dbt
uv run build            # dbt build into data/retail_analytics.duckdb
```

CI (`.github/workflows/ci.yml`) runs the same lint, tests, and `dbt parse` on every push to
`main` and every pull request. A change merges only with a green run.

## Workflow

- **Each change is tied to a story.** Branch names, commit messages, and PR titles name the
  story id (for example `C-4: synthetic source generator`).
- **Human review before merge.** Every PR is reviewed and approved by a human before it lands
  on `main`, including AI-assisted changes. Review outcomes are recorded on the PR.
- **Contracts first.** Shapes in [`docs/data-contracts.md`](docs/data-contracts.md) are the
  contract. Changing a source file, model grain, or mart column is a spec change, made in the
  spec first and copied here, not edited in code alone.

## Python

- Formatting and lint: ruff, configured in `pyproject.toml` (`[tool.ruff]`). `uv run ruff check .`
  must pass; `uv run ruff format .` is the formatter.
- Source lives in `src/retail_analytics/`; tests in `tests/`, offline and deterministic.
- New behaviour comes with a test.

## SQL and dbt

- **One model per file**, named for its layer: `stg_<source>`, `int_<entity>_<grain>`,
  `dim_<entity>`, `fct_<subject>`.
- **Layers:** staging reads sources and seeds only; intermediate reads staging; marts read
  only the dimension and intermediate layers.
- **Style:** lowercase keywords and identifiers, snake_case names, four-space indents,
  trailing commas, one column per line in select lists.
- **CTEs over subqueries:** import CTEs at the top (one per `ref`/`source`), then logical CTEs,
  then a final `select * from final`.
- **Parameterize, don't copy.** Periods, milestones, and cohort offsets are dbt variables or
  seeds (see `vars` in `dbt/dbt_project.yml`), never one query per period.
- **Mappings live in seeds**, such as the channel taxonomy; adding a channel is a seed change.

## Documentation

- **Every model and every column is described in YAML** next to the model. Business terms
  (customer, visit, acquisition channel, milestone, step rate) are defined once in dbt doc
  blocks and referenced, not re-worded.
- Every model has tests for its grain (unique key, not null) plus the tests named in the data
  contract.
