# Flagship demo story

> **Build record, Definition stage.** Public copy as of 2026-11-02; source spec is the authority.
> Companion of the [spec](spec.md). Walkthrough: [build record](../README.md).

The flagship demo (`howdoidata/retail_analytics`), told as one story alongside its data. Customer analytics: which acquisition channels bring customers who keep coming back. The demo is built with BMAD, and that build is itself part of the story.

## Setting

- **Company:** Switchback Outfitters, a fictional outdoor gear shop selling online and in one store.
- **Protagonist:** the shop's growth/marketing lead, who mirrors the SMB buyer: has a question, can't trust the numbers. Name and exact question wording chosen when the story copy is written.
- **Question:** which channels bring customers who keep coming back? Answered by the visit funnel by channel in [`data-contracts.md`](../../data-contracts.md).
- All data is synthetic; every result shown is labeled simulated.

## Story page structure

Opens in the demo page format: **The problem → What changes → In past work → What this demo proves.** Then four chapters, one per block, in block order. Each chapter = short narrative beat + the real artifact produced at that stage + link to that block page.

| Ch | Block | Narrative beat | Artifact shown alongside |
|---|---|---|---|
| 1 | Data Sources & Tracking | The shop's tools capture data, but it's messy and can't answer the question | Generator output: store, marketing, and ad-spend CSVs with the deliberate mess visible (e.g. one customer as `JANE@x.com` and `jane@x.com `) |
| 2 | Data Pipelines & Warehousing | The data now cleans and loads itself | dbt + SQL on DuckDB models fixing each mess item, the tests proving it, a CI run |
| 3 | Analytics & Data Products | The numbers answer the question | Three views by channel (sign-ups, visit funnel, cohorts); Tableau Public dashboard (labeled simulated) |
| 4 | Data Operations & AI Governance | The marketing lead can trust it, and can see how it was built | The build record (below) and the data catalog |

Chapter map confirmed by the user.

Each block page excerpts its chapter (beat + artifact) and links to the full story. Story page and excerpts ship together, only once the artifacts exist.

## Build record (CAP-11)

The demo is built with BMAD. The request is traced from idea to production and published:

| Stage | What is shown |
|---|---|
| Idea | Brainstorming / forge output that framed the request |
| Definition | Spec (and PRD/architecture where used), data contracts |
| Planning | Stories and sprint status: the cadence |
| Build | AI-assisted implementation, each change tied to a story |
| Review | Human review points and AI review findings, with what was accepted or rejected |
| Verification | dbt tests, Python tests, CI on every change |
| Production | Documentation, the data catalog, standards the repo follows, and where progress is visible |

The three AI controls from the AI stance, shown concretely:
- **Data limits:** AI only ever sees synthetic demo data and repo content (assumed).
- **Human review:** named review points where Antonio approves before work proceeds.
- **Record:** committed BMAD artifacts (logs, specs, stories, review reports).

Shown in the repo (committed artifacts + a walkthrough doc) and summarized in Chapter 4. Every committed artifact must be public-safe.

## Build (MVP)

Python generator → store, marketing, and ad-spend CSVs with deliberate mess → dbt + SQL on DuckDB in layers (staging → customer visits → customers → three marts: sign-ups, visit funnel, cohorts), dbt tests, CI → data catalog (dbt YAML + generated `CATALOG.md`) → one Tableau Public dashboard labeled simulated → one story page. Shapes in [`data-contracts.md`](../../data-contracts.md).

- Public repo `github.com/howdoidata/retail_analytics`, README in demo page format from day one.
- Modular and expandable: each report type is one parameterized model; new grains, milestones, channels, and attribution rules are added on top without rewrites.
- Held to coding standards, with explicit human review points.
- Measured demo facts (test counts, model counts, run results) may be stated as exact figures.

## Later releases (out of MVP)

QBR pack (heatmaps, campaign summaries, referral payoff, online vs store mix, age groups) on the same layers, full catalog tool (OpenMetadata or DataHub), Firebase emulator, mock APIs, Census data, Retention pillar, decks, AI summaries. Each adds chapters or demos; none blocks the MVP story.
