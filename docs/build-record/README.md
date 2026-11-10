# Build record: from idea to production

This folder is the public trail of how `retail_analytics` gets built: one request followed from the first
idea to production, with the artifacts each stage produced. The build uses BMAD (an AI-assisted
planning and delivery method). It shows where AI did the work, where a human reviewed it, and how tests,
CI, and documentation keep the result standard and visible. All data in this repo is synthetic and every
result is simulated.

Each stage below says what it shows, links the artifacts, and carries a status:
`Recorded` (complete), `In progress` (partly recorded), or `Pending: <story>` (waits on that story).
How each story leaves its record: [convention.md](convention.md).

## The three AI controls

- **Data limits:** AI is given only synthetic demo data and repo content. Evidence that the data and repo
  content are synthetic and public: the assumption in the [spec](definition/spec.md#assumptions), the
  [generator](../../src/retail_analytics/generator) that simulates every source CSV, and the
  [public-safety check](convention.md#public-safety-check-before-commit) every commit passes.
- **Human review:** named review points where Antonio approves before work proceeds: the spec and each
  story's result, and every pull request before it merges to `main`. Evidence: the human decision for each
  story in the [Review](#review) stage.
- **Record:** what AI did is written down and committed: the idea, the spec, and one record per story
  with its review outcome and CI run (this folder). Evidence: the [story index](#story-index).

## Idea

**What is shown:** the forged idea that framed the request: who the site and demo are for, the four
blocks, the canonical story, the impact rule, and the flagship MVP.

- [Idea](idea.md)

**Status:** Recorded

## Definition

**What is shown:** the spec that turned the idea into capabilities with success checks, and the
companions the flagship repo is built from.

- [Spec](definition/spec.md): capabilities, constraints, non-goals. The flagship's own are CAP-5
  (demo), CAP-11 (this build record), CAP-12 (README landing page), and CAP-13 (data catalog).
- [Demo story](definition/demo-story.md): the company, the question, the four chapters, the build record.
- [LLM landing page](definition/llm-landing-page.md): what the README carries.
- [Data contracts](../data-contracts.md): source CSVs, deliberate mess, model layers, the three marts.

Key decisions, in short:

- The demo company is Switchback Outfitters, a fictional outdoor gear shop (online plus one store). All
  data is synthetic and every result is labeled simulated.
- One question, *which channels bring customers who keep coming back?*, answered by three views by
  acquisition channel: sign-ups, the visit funnel, and cohorts.
- Models are built in layers, and each report type is one parameterized model: periods, milestones,
  and cohort offsets are settings, not copied queries.
- Definitions live once, in dbt YAML, with a generated `CATALOG.md`; no hosted docs site.
- The repo's README is the landing page; no GitHub Pages site.
- Minimal CI landed with the first commit so every later change shows a green run.
- The dashboard is authored on contract-shaped sample extracts first and published on the real marts later.

**Status:** Recorded

## Planning

**What is shown:** the stories the request was split into and the cadence they land in. Every change to
this repo names its story.

| Story | Title |
|---|---|
| C-1 | Write down the flagship data contracts |
| C-2 | Create and scaffold the flagship repo with minimal CI |
| C-3 | Author the Tableau dashboard on sample extracts |
| D-1 | Set up the build-record trail and walkthrough skeleton |
| C-4 | Build the source CSV generator (Ch1) |
| C-5 | Build the dbt staging models that fix the mess (Ch2) |
| C-6 | Build the core customer layers |
| C-7 | Build the sign-ups by channel mart (Ch3) |
| C-8 | Build the visit funnel mart (Ch3) |
| C-9 | Build the customer cohorts mart (Ch3) |
| C-10 | Generate the data catalog and gate it in CI |
| C-11 | Draft the README landing page |
| C-12 | Run the full pipeline in CI |
| C-13 | Publish the dashboard on real mart data |
| C-14 | Fill measured facts and links into the README |
| D-2 | Close out the build record |
| C-15 | Link the README to the live story page |

The website's own stories (site pages, profiles) are planned alongside but change nothing in this repo.

**Status:** Recorded

## Build

**What is shown:** AI-assisted implementation, each change tied to a story through its branch, commit,
and pull request. Each story's record links the change.

- [Story index](#story-index)

**Status:** Pending: C-15

## Review

**What is shown:** the human review points and the AI review findings for each story, with what was
accepted or rejected and why. Recorded in each story's "Review outcome" section; each row below links it.

| Story | Human decision | AI review | Record |
|---|---|---|---|
| C-1 | Approved by Antonio at the story's done checkpoint; the data contracts are final | The spec's coherence and preservation self-checks passed; no findings recorded | [C-1](stories/C-1.md#review-outcome) |
| C-2 | Approved by Antonio after the repo went public and CI was green; no PR (initial commit to `main`), so approved outside GitHub | None recorded | [C-2](stories/C-2.md#review-outcome) |
| C-3 | Antonio answered the data-contract questions, authored and published the workbook, and moved the story to Done on 2026-11-10 | None recorded | [C-3](stories/C-3.md#review-outcome) |
| D-1 | Spec approved by Antonio before implementation; Antonio reviewed and merged PR #1 on 2026-11-03 | Three AI reviewers (blind diff, edge cases, verification gaps); findings accepted and fixed, or rejected with reasons | [D-1](stories/D-1.md#review-outcome) |
| C-4 | Antonio approved and merged PR #3 on 2026-11-03 | Three AI review passes before human review; accepted findings fixed in the PR | [C-4](stories/C-4.md#review-outcome) |
| C-5 | Antonio approved and merged PR #4 on 2026-11-03 | Three AI review passes before human review; accepted findings fixed in the PR | [C-5](stories/C-5.md#review-outcome) |
| C-6 | Spec approved by Antonio before implementation; Antonio merged batch PR #5 on 2026-11-03 | Three AI review passes before human review; accepted findings fixed in a follow-up C-6 commit | [C-6](stories/C-6.md#review-outcome) |
| C-7 | Antonio merged batch PR #6 on 2026-11-03 | Three AI review passes before commit; accepted fixes in `80decc0` | [C-7](stories/C-7.md#review-outcome) |
| C-8 | Antonio merged batch PR #6 on 2026-11-03 | Three AI review passes before commit; accepted fixes in `1f091b5` | [C-8](stories/C-8.md#review-outcome) |
| C-9 | Antonio merged batch PR #6 on 2026-11-03 | One AI review pass before commit; accepted fixes in `a280562` | [C-9](stories/C-9.md#review-outcome) |
| C-10 | Antonio merged batch PR #7 on 2026-11-03 | Three AI review passes before commit; accepted fixes in `0548cd8` | [C-10](stories/C-10.md#review-outcome) |
| C-11 | Antonio merged batch PR #7 on 2026-11-03 | Three AI review passes before commit; accepted fixes in `85caec2` | [C-11](stories/C-11.md#review-outcome) |
| C-12 | Antonio merged batch PR #8 on 2026-11-04 | One AI review pass before commit; accepted fixes in `df37c74` | [C-12](stories/C-12.md#review-outcome) |
| C-13 | Antonio merged batch PR #9 on 2026-11-09 and published the dashboard | One AI review pass before the part 1 commit; part 2 checked with a real build, its findings fixed in the part 2 commit | [C-13](stories/C-13.md#review-outcome) |
| C-14 | Antonio descoped the story to links on 2026-11-10 and directed the Done move; the README change waits for his review of the batch PR | None recorded | [C-14](stories/C-14.md#review-outcome) |
| D-2 | Spec approved by Antonio before implementation (2026-11-10); the change waits for his review of the batch PR | One AI review pass before commit; accepted fixes in the D-2 commit | [D-2](stories/D-2.md#review-outcome) |

**Status:** Recorded

## Verification

**What is shown:** Python tests, dbt tests, and CI on every change. Each row below is the run on the
story's last commit that changed more than its record (some records list earlier runs too) and links the
record's "CI run" section.

| Story | CI run | Result |
|---|---|---|
| [C-1](stories/C-1.md#ci-run) | None: no commit to this repo | Not applicable |
| [C-2](stories/C-2.md#ci-run) | [Run 41563210091](https://github.com/howdoidata/retail_analytics/actions/runs/41563210091) | Success |
| [C-3](stories/C-3.md#ci-run) | [Run 41670524253](https://github.com/howdoidata/retail_analytics/actions/runs/41670524253) for `a637232` (the data-contract answers; the workbook is outside the repo) | Success |
| [D-1](stories/D-1.md#ci-run) | [Run 41580294371](https://github.com/howdoidata/retail_analytics/actions/runs/41580294371) for `2ca9657` | Success |
| [C-4](stories/C-4.md#ci-run) | [Run 41678728655](https://github.com/howdoidata/retail_analytics/actions/runs/41678728655) for `cb29cc1` | Success |
| [C-5](stories/C-5.md#ci-run) | [Run 41686032559](https://github.com/howdoidata/retail_analytics/actions/runs/41686032559) for `395a370` | Success |
| [C-6](stories/C-6.md#ci-run) | [Run 41695307067](https://github.com/howdoidata/retail_analytics/actions/runs/41695307067) for `1c36c8c` | Success |
| [C-7](stories/C-7.md#ci-run) | [Run 41715802643](https://github.com/howdoidata/retail_analytics/actions/runs/41715802643) for `68130d0`, the batch PR #6 head; it checks `a280562`, the batch's last commit that changed more than the records | Success |
| [C-8](stories/C-8.md#ci-run) | [Run 41715802643](https://github.com/howdoidata/retail_analytics/actions/runs/41715802643) for `68130d0`, the batch PR #6 head; it checks `a280562`, the batch's last commit that changed more than the records | Success |
| [C-9](stories/C-9.md#ci-run) | [Run 41715802643](https://github.com/howdoidata/retail_analytics/actions/runs/41715802643) for `68130d0`, the batch PR #6 head; it checks `a280562`, the batch's last commit that changed more than the records | Success |
| [C-10](stories/C-10.md#ci-run) | [Run 41733917222](https://github.com/howdoidata/retail_analytics/actions/runs/41733917222) for `85caec2` (batch PR #7) | Success |
| [C-11](stories/C-11.md#ci-run) | [Run 41733917222](https://github.com/howdoidata/retail_analytics/actions/runs/41733917222) for `85caec2` (batch PR #7) | Success |
| [C-12](stories/C-12.md#ci-run) | [Run 41840887371](https://github.com/howdoidata/retail_analytics/actions/runs/41840887371) for `df37c74` | Success |
| [C-13](stories/C-13.md#ci-run) | [Run 42632239662](https://github.com/howdoidata/retail_analytics/actions/runs/42632239662) for `6909ed3` | Success |
| [C-14](stories/C-14.md#ci-run) | Pending batch PR | Pending batch PR |
| [D-2](stories/D-2.md#ci-run) | Pending batch PR | Pending batch PR |

- CI workflow: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) (lint, Python tests, `dbt parse`,
  data catalog check, then the full pipeline: `uv run generate`, then `uv run build`, which writes the CSVs
  to `data/raw/`, runs `dbt build` on every layer with its tests, and ends by exporting the marts to
  `data/export/`, re-exported once more to show the bytes do not change; C-12, C-13)
- Python tests: [`tests/`](../../tests)
- dbt tests: in the model YAML and [`dbt/tests/`](../../dbt/tests), run by `uv run build`

**Status:** Recorded

## Production

**What is shown:** the documentation, the data catalog, the standards the repo follows, and where
progress is visible.

- Landing page: [README](../../README.md)
- Standards and review rules: [CONTRIBUTING.md](../../CONTRIBUTING.md)
- Data catalog: [`CATALOG.md`](../../CATALOG.md), generated from the dbt descriptions by `uv run catalog` (C-10).
- Dashboard data: the last step of `uv run build`, and `uv run export` on its own, writes the three marts to
  [`data/export/`](../../data/export) as the CSV files the dashboard reads (C-13).
- Live dashboard: [Switchback Outfitters on Tableau Public](https://public.tableau.com/shared/R7XPC635J?:display_count=n&:origin=viz_share_link), all data simulated (C-3, C-13).

**Status:** Recorded

## Story index

One record per story in [`stories/`](stories), written in the pull request that carries the story (its own
or a [batch PR](convention.md#batch-pull-requests)).

| Story | Title | Record | Status |
|---|---|---|---|
| C-1 | Write down the flagship data contracts | [C-1](stories/C-1.md) | Done |
| C-2 | Create and scaffold the flagship repo with minimal CI | [C-2](stories/C-2.md) | Done |
| C-3 | Author the Tableau dashboard on sample extracts | [C-3](stories/C-3.md) | Done |
| D-1 | Set up the build-record trail and walkthrough skeleton | [D-1](stories/D-1.md) | Done |
| C-4 | Build the source CSV generator (Ch1) | [C-4](stories/C-4.md) | Done |
| C-5 | Build the dbt staging models that fix the mess (Ch2) | [C-5](stories/C-5.md) | Done |
| C-6 | Build the core customer layers | [C-6](stories/C-6.md) | Done |
| C-7 | Build the sign-ups by channel mart (Ch3) | [C-7](stories/C-7.md) | Done |
| C-8 | Build the visit funnel mart (Ch3) | [C-8](stories/C-8.md) | Done |
| C-9 | Build the customer cohorts mart (Ch3) | [C-9](stories/C-9.md) | Done |
| C-10 | Generate the data catalog and gate it in CI | [C-10](stories/C-10.md) | Done |
| C-11 | Draft the README landing page | [C-11](stories/C-11.md) | Done |
| C-12 | Run the full pipeline in CI | [C-12](stories/C-12.md) | Done |
| C-13 | Publish the dashboard on real mart data | [C-13](stories/C-13.md) | Done |
| C-14 | Fill measured facts and links into the README | [C-14](stories/C-14.md) | Done |
| D-2 | Close out the build record | [D-2](stories/D-2.md) | In review |
