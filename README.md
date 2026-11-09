# retail_analytics

Flagship How Do I Data demo: which acquisition channels bring customers who keep coming back, answered with
synthetic data from a fictional outdoor gear shop. All data is synthetic and every result is simulated.
**Status: In development.**

> Bracketed placeholders (`[[NUMBER: …]]` for a figure or measured status, `[[LINK: …]]` for a page not yet live) are filled
> in as the build lands.

## What this shows

- **The problem:** the shop's growth and marketing lead wants to know which channels bring customers who
  keep coming back. The store, marketing, and ad tools each hold part of the answer, but the data is messy:
  the same customer appears twice, channels are spelled many different ways, and nobody trusts the totals.
- **What changes:** the raw data cleans and loads itself, is tested on every change, and feeds three views
  by channel: where customers come from, how fast they come back, and whether they stay.
- **In past work:**
  - In past work, customer data from sales, marketing and support systems was joined into one view used across the company.
  - In past work, joining outside company data to CRM records improved lead conversion.
  - In past work, automating campaign targeting increased the team's capacity to run campaigns.
- **What this demo proves:** messy store and marketing data can become a tested, documented answer to an
  acquisition question, rebuilt from this public repo, with AI working under three controls: limits on what
  data it sees, human review before results are used, and a record of what it did. Evidence: [measured facts](#measured-facts)
  and the [build record](#build-record).

## The demo company and question

**Switchback Outfitters is a fictional outdoor gear shop** selling online and in one store. **All data in
this repo is synthetic and every result is simulated.** The question: *Which channels bring customers who
keep coming back?*

Answered by three views, one mart each (shapes in [`docs/data-contracts.md`](docs/data-contracts.md)):

- **Where customers come from:** sign-ups by channel and quarter.
- **How fast they come back:** visit funnel by channel, from signup through repeat-visit milestones.
- **Whether they stay:** cohorts by signup quarter and channel.

## Chapters

| Ch | Block | What was built | Artifact |
|---|---|---|---|
| 1 | Data Sources & Tracking | A synthetic generator that writes the shop's store, marketing, and ad-spend CSVs with deliberate mess: duplicate customers, channel labels spelled many ways, mixed timestamp formats, orders pointing at missing records, test and junk rows | [`src/retail_analytics/generator/`](src/retail_analytics/generator/), mess reference in [`data/raw/README.md`](data/raw/README.md) |
| 2 | Data Pipelines & Warehousing | dbt models on DuckDB that fix each mess item, tests that prove it stays fixed, and CI on every change | [`dbt/models/staging/`](dbt/models/staging/), [`dbt/models/intermediate/`](dbt/models/intermediate/), tests in [`dbt/tests/`](dbt/tests/) and [`tests/`](tests/), [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |
| 3 | Analytics & Data Products | Three marts by channel (sign-ups, visit funnel, cohorts) and one dashboard, labeled simulated | [`dbt/models/marts/`](dbt/models/marts/); Tableau Public dashboard (simulated): [[LINK: Tableau Public dashboard URL]] |
| 4 | Data Operations & AI Governance | The build record from idea to production, and a data catalog generated from the dbt descriptions | [`docs/build-record/README.md`](docs/build-record/README.md), [`CATALOG.md`](CATALOG.md) |

## Build record

How this demo is built, from idea to production, with where AI worked and where a human reviewed it:
the [build record walkthrough](docs/build-record/README.md). AI works under
[three controls](docs/build-record/README.md#the-three-ai-controls): limits on what data it sees (synthetic
demo data and repo content only), human review before work proceeds, and a committed record of what it did.
Stages:

1. [Idea](docs/build-record/README.md#idea)
2. [Definition](docs/build-record/README.md#definition)
3. [Planning](docs/build-record/README.md#planning)
4. [Build](docs/build-record/README.md#build)
5. [Review](docs/build-record/README.md#review)
6. [Verification](docs/build-record/README.md#verification)
7. [Production](docs/build-record/README.md#production)

## Measured facts

Measured on this repo, not simulated:

- dbt models: [[NUMBER: dbt model count]]
- dbt tests: [[NUMBER: dbt test count]]
- Python tests: [[NUMBER: Python test count]]
- CI status: [[NUMBER: CI status on main]]

## Data catalog

Every business term, source, model, seed, and column, defined once: [`CATALOG.md`](CATALOG.md), generated
from the dbt descriptions by `uv run catalog`.

## Links

- Tableau Public dashboard (simulated): [[LINK: Tableau Public dashboard URL]]
- Story page on howdoidata.com: [[LINK: howdoidata.com story page URL]]
- Demos page: [[LINK: howdoidata.com Demos page URL]]
- Repo: [github.com/howdoidata/retail_analytics](https://github.com/howdoidata/retail_analytics)

## Repo layout

| Path | Contents |
|---|---|
| `src/retail_analytics/cli.py` | The one-command run (`uv run build`): generate, `dbt build`, then export |
| `src/retail_analytics/generator/` | Synthetic source-data generator (`uv run generate`) |
| `src/retail_analytics/catalog.py` | Data catalog generator and check (`uv run catalog`) |
| `src/retail_analytics/export.py` | The marts as CSV for the dashboard (`uv run export`) |
| `dbt/` | dbt-duckdb project: `models/staging`, `models/intermediate`, `models/marts`, `seeds`, `macros` |
| `scripts/` | Helper scripts |
| `tests/` | Python tests |
| `docs/` | [Data contracts](docs/data-contracts.md), [build record](docs/build-record/README.md) |
| `CATALOG.md` | Generated data catalog (`uv run catalog`) |
| `data/raw/`, `data/export/` | Generated CSVs (not committed) |
| `data/retail_analytics.duckdb` | DuckDB database built by `uv run build` (not committed) |

## Quick start

Prerequisites: [git](https://git-scm.com/) and [uv](https://docs.astral.sh/uv/). On the first `uv run`, uv
installs Python 3.12 (if it is missing) and the locked dependencies.

```bash
git clone https://github.com/howdoidata/retail_analytics.git
cd retail_analytics
uv run build
```

`uv run build` is the one-command run:

1. It writes the six synthetic source CSVs to `data/raw/` (seed 42, or `--seed N`), replacing any already there.
2. It runs `dbt build` on every layer (staging, intermediate, marts) with its tests, into
   `data/retail_analytics.duckdb`, and exits non-zero if any model or test fails.
3. It writes the three marts to `data/export/*.csv`, the files the dashboard reads.

The three views are the mart tables `fct_signups_by_channel`, `fct_visit_funnel_by_channel`, and
`fct_customer_cohorts` in that file (schema `main`; the other layers are in the `staging` and `intermediate`
schemas), and the three CSVs carry the same rows. `uv run generate [--seed N]` writes only the CSVs;
`uv run dbt build --project-dir dbt --profiles-dir dbt` builds the CSVs already in `data/raw/` without
regenerating them; `uv run export` repeats only the last step, so the same database always gives
byte-identical files.

Developer checks:

```bash
uv run ruff check .                                     # lint
uv run pytest                                           # Python tests
uv run dbt parse --project-dir dbt --profiles-dir dbt   # compile the dbt project
uv run catalog --check                                  # CATALOG.md complete and current (uv run catalog rewrites it)
```

CI runs these checks, then `uv run generate` and `uv run build` (which ends in the export), on every push to
`main` and every pull request.

Standards and review rules: [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).

---

How Do I Data is the independent analytics practice of Antonio Galvan, based in Austin, Texas, and founded in 2025. Antonio is a U.S. Navy veteran and former Electronics Technician who spent over a decade building and leading analytics teams across finance, go-to-market, and customer analytics: building the financial models behind investment and cost decisions, and turning analysis into recommendations for executives, operators, and owners.

A How Do I Data demo project
