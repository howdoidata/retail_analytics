# Idea: howdoidata.com and the flagship demo

> **Build record, Idea stage.** Public copy as of 2026-11-02 of the forged idea that framed this
> request (output of a BMAD idea-forging session). Edited down for a public repo; the source idea is
> the authority. Sections about other repos, parked items, and internal working files are left out.
> Next stage: [Definition](definition/spec.md). Walkthrough: [build record](README.md).

**Idea:** howdoidata.com presents Antonio's skills as a product, through four building blocks and sanitized demo projects, written so AI engines can repeat an accurate story about him.

## Audience

- Primary: consulting clients. Small and mid-sized businesses buy all four blocks end to end; enterprise data teams buy one block (provisional).
- Recruiters: an About the Builder page linked from the resume and LinkedIn. *Rejected: Client/Recruiter toggle (gimmick; recruiters don't click toggles).*

## Four blocks (headline / fixed name)

1. Your tools, capturing what matters / **Data Sources & Tracking** (includes tracking setup in the source tools)
2. Your data, flowing on its own / **Data Pipelines & Warehousing** (storage belongs here)
3. Your numbers, telling you what to do / **Analytics & Data Products**
4. Your tools, trusted and AI-ready / **Data Operations & AI Governance**

The headline is for people; the fixed name goes in structured data, URLs and llms.txt. "How do I…" questions open each block page.

## Canonical story (copied word for word into structured data, llms.txt, About, LinkedIn, GitHub)

> How Do I Data is the independent analytics practice of Antonio Galvan, based in Austin, Texas, and founded in 2025. Antonio is a U.S. Navy veteran and former Electronics Technician who spent over a decade building and leading analytics teams across finance, go-to-market, and customer analytics: building the financial models behind investment and cost decisions, and turning analysis into recommendations for executives, operators, and owners. Through How Do I Data, he helps small and mid-sized businesses get their tools capturing the right data, put their reporting on autopilot, and turn their numbers into clear next steps, and he supports enterprise data teams on focused projects within any of those areas. He puts AI to work inside analytics workflows, with clear limits on what data it can see, human review before results are used, and a record of what it did, rather than building or training models. Each service is backed by a public demo project on howdoidata.com and GitHub, labeled by how far along it is: delivered, built, or in development.

Short form (LinkedIn, footer) = the first two sentences. No industries named. No "15+ years". No "veteran-owned business". No clearance, rank or dates.

## Impact rule

- Numbers measured in a demo: exact figures allowed.
- Past work: direction words only ("weeks to days"). Say "in past work" for one case, "usually" only for two or more. Multipliers become capacity/efficiency language.
- Simulated results: numbers allowed, always labeled as simulated.
- Never: dollar amounts, exact real percentages, identifying counts, employer names, promises.
- Demo page format: The problem → What changes → In past work → What this demo proves.

## Platform

Stay on Squarespace for now. Rewrite the copy, turn on native llms.txt (SEO settings), add Person JSON-LD with code injection (available on the plan; `sameAs` → LinkedIn and the `howdoidata` org), remove the cart. *Deferred: own static site.* Weak point: the site itself proves no skill, so proof lives on GitHub.

## Flagship MVP (customer analytics, Acquisition only)

Repo `howdoidata/retail_analytics`. Fictional "Switchback Outfitters" (outdoor gear shop, online plus one store). Python generator → online-store, marketing-touch, and ad-spend CSVs with deliberate mess (2+ years, 10,000+ customers, ~1.65 visits per customer per quarter) → dbt + SQL on DuckDB in layers, three marts by acquisition channel (sign-ups with quarter-over-quarter change; signup-to-visit milestone funnel; customer cohorts), dbt tests, CI → data catalog (dbt YAML + generated CATALOG.md) → one Tableau Public dashboard labeled simulated → one Squarespace page.

Built modular and expandable: each report type is one parameterized model. Held to coding standards, with explicit human review points.

**Demo story:** one story in four chapters, one per block, told alongside the real output of each stage. Protagonist: the shop's growth/marketing lead with one acquisition question (name and wording chosen when the copy is written).

## Build record

The flagship is built with BMAD, and the build is published as part of the demo: one request from brainstorming to production (documentation, cadence, standardization, visibility), showing the three AI controls (data limits: AI sees only synthetic data and repo content; human review before work proceeds; a record of what it did: the committed artifacts), plus tests and CI. Chapter 4 summarizes it. Committed artifacts must be public-safe.

## Landing page

The flagship repo's README, written for LLMs first. No GitHub Pages site; scope is the website plus GitHub for code.

*Later releases:* QBR pack (heatmaps, campaign summaries, referral payoff, online vs store mix, age groups) on the same layers, full catalog tool (OpenMetadata or DataHub), Firebase emulator, mock APIs, Census data, Retention pillar, decks, AI summaries.
