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

- **Data limits:** AI only ever sees synthetic demo data and repo content. Nothing real goes in, so
  nothing real can come out.
- **Human review:** named review points where Antonio approves before work proceeds: the spec and each
  story's result, and every pull request before it merges to `main`.
- **Record:** what AI did is written down and committed: the idea, the spec, and one record per story
  with its review outcome and CI run (this folder).

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

**Status:** In progress

## Build

**What is shown:** AI-assisted implementation, each change tied to a story through its branch, commit,
and pull request. Each story's record links the change.

- [Story index](#story-index)

**Status:** In progress

## Review

**What is shown:** the human review points and the AI review findings for each story, with what was
accepted or rejected and why. Recorded in each story's "Review outcome" section.

- [Story index](#story-index)

**Status:** In progress

## Verification

**What is shown:** Python tests, dbt tests, and CI on every change. Each story's record links its CI run.

- CI workflow: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) (lint, Python tests, `dbt parse`)
- Python tests: [`tests/`](../../tests)
- The full pipeline in CI (generate, build, test) lands with C-12.

**Status:** In progress

## Production

**What is shown:** the documentation, the data catalog, the standards the repo follows, and where
progress is visible.

- Landing page: [README](../../README.md)
- Standards and review rules: [CONTRIBUTING.md](../../CONTRIBUTING.md)
- Data catalog (`CATALOG.md`): lands with C-10.
- Live dashboard: lands with C-13.

**Status:** Pending: D-2

## Story index

One record per story in [`stories/`](stories), written in the story's own pull request.

| Story | Title | Record | Status |
|---|---|---|---|
| C-1 | Write down the flagship data contracts | [C-1](stories/C-1.md) | Done |
| C-2 | Create and scaffold the flagship repo with minimal CI | [C-2](stories/C-2.md) | Done |
| C-3 | Author the Tableau dashboard on sample extracts | [C-3](stories/C-3.md) | In progress |
| D-1 | Set up the build-record trail and walkthrough skeleton | [D-1](stories/D-1.md) | In review |
