# retail_analytics

Flagship How Do I Data demo. **Switchback Outfitters is a fictional outdoor gear shop** (online plus one
store); **all data in this repo is synthetic and every result is simulated.** The demo follows the shop's
marketing lead and one question: *which channels bring customers who keep coming back?*

> **Status: In development.** This README is a stub; sections marked TODO are filled in as the build lands.

## What this shows

- **The problem:** TODO (story E-1): the marketing lead has a question the shop's data can't answer yet.
- **What changes:** TODO (story E-1): messy store and marketing data becomes tested, layered models and three
  acquisition views by channel.
- **In past work:** TODO: approved past-work wording only.
- **What this demo proves:** TODO: measured facts only (model counts, test counts, CI status), added once they exist.

## The question

Answered by three views, one mart each (shapes in [`docs/data-contracts.md`](docs/data-contracts.md)):

1. **Where customers come from:** sign-ups by channel and quarter.
2. **How fast they convert:** visit funnel by channel, from signup through repeat-visit milestones.
3. **Whether they stay:** cohorts by signup quarter and channel.

## Chapters

| Ch | Block | What was built | Artifact |
|---|---|---|---|
| 1 | Data Sources & Tracking | TODO: synthetic generator (story C-4) | TODO |
| 2 | Data Pipelines & Warehousing | TODO: dbt models on DuckDB, tests, CI | TODO |
| 3 | Analytics & Data Products | TODO: three views by channel, dashboard (labeled simulated) | TODO |
| 4 | Data Operations & AI Governance | TODO: build record and data catalog | TODO |

## Build record

TODO: stages from idea to production (idea, definition, planning, build, review, verification, production),
with links to the committed artifacts.

## Repo layout

| Path | Contents |
|---|---|
| `src/retail_analytics/generator/` | Synthetic source-data generator (TODO, story C-4) |
| `dbt/` | dbt-duckdb project: `models/staging`, `models/intermediate`, `models/marts`, `seeds`, `macros` |
| `scripts/` | Helper scripts |
| `tests/` | Python tests |
| `docs/` | [Data contracts](docs/data-contracts.md) |
| `data/raw/`, `data/export/` | Generated CSVs (not committed) |

## Quick start

```bash
uv sync
uv run ruff check . && uv run pytest
uv run build
```

Standards and review rules: [CONTRIBUTING.md](CONTRIBUTING.md).

## Links

- Data catalog: TODO (`CATALOG.md`)
- Tableau Public dashboard: TODO
- Story page on howdoidata.com: TODO (once live)
- Demos: TODO

## License

MIT. See [LICENSE](LICENSE).

---

How Do I Data is the independent analytics practice of Antonio Galvan, based in Austin, Texas, and founded in 2025. Antonio is a U.S. Navy veteran and former Electronics Technician who spent over a decade building and leading analytics teams across finance, go-to-market, and customer analytics: building the financial models behind investment and cost decisions, and turning analysis into recommendations for executives, operators, and owners.

A How Do I Data demo project
