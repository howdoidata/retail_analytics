---
id: SPEC-howdoidata-site
companions:
  - demo-story.md
  - llm-landing-page.md
  - ../../data-contracts.md
---

> **Build record, Definition stage.** Public copy as of 2026-11-02; source spec is the authority.
> Edited down for a public repo. Companions committed here: [demo-story.md](demo-story.md),
> [llm-landing-page.md](llm-landing-page.md), and the data contracts at
> [docs/data-contracts.md](../../data-contracts.md). Other companions named below (site pages, copy,
> editorial rules, GitHub repos, UX design) belong to the website and are not part of this repo.
> Previous stage: [Idea](../idea.md). Walkthrough: [build record](../README.md).

# howdoidata.com: site pages, content, and flagship demo story

## Why

A vision to realize: howdoidata.com presents Antonio Galvan's analytics practice as a product of four building blocks, each backed by a public demo. Consulting clients (SMBs buying all four blocks; enterprise data teams buying one) need to see what they would get, recruiters need one clear page about the builder, and AI engines need one consistent story to repeat. The site is mostly pages and copy, and the Squarespace site itself demonstrates no skill, so the proof comes from a fictional company's story told alongside real demo data and code.

## Capabilities

- **CAP-1** Home page
  - **intent:** A visitor sees the canonical short form and the four blocks (headline + fixed name) and can reach each block page, Demos, and About.
  - **success:** Home shows the short form verbatim and four block links using the headline + fixed name pairs in `site-pages.md`; every listed link resolves.
- **CAP-2** Four block pages
  - **intent:** A prospective client reads, per block, the "How do I…" questions it answers, what it covers, and proof of the work.
  - **success:** Four pages exist at fixed-name URLs; each opens with "How do I…" questions and carries at least one approved past-work line or linked demo with a status label; no claim breaks `editorial-rules.md`.
- **CAP-3** Flagship demo story page
  - **intent:** A prospective client follows one fictional outdoor gear shop's marketing lead and their acquisition question through four chapters, one per block, each showing the real demo output from that stage.
  - **success:** The page opens in the demo page format, has four chapters in block order, each shows an artifact from the flagship repo, every number is measured or labeled simulated, and it links to the repo and dashboard.
- **CAP-4** Story excerpts on block pages
  - **intent:** Each block page shows its demo story chapter as proof and links to the full story.
  - **success:** All four block pages show their chapter's beat and artifact plus a link to CAP-3, and they go live in the same release as CAP-3.
- **CAP-5** Flagship retail demo (`retail_analytics`)
  - **intent:** A public repo builds the data behind the story: messy online-store and marketing source data → tested, layered models → three acquisition views by channel (sign-ups, visit funnel, cohorts) → a public dashboard.
  - **success:** From a clean clone, one documented run regenerates the CSVs and builds the dbt models on DuckDB with tests passing, at the volume in `data-contracts.md`; CI is green; the Tableau Public dashboard is live and labeled simulated; the README follows the demo page format.
- **CAP-6** Demos index
  - **intent:** A visitor or AI engine sees every demo with its block and how far along it is.
  - **success:** Each listed demo shows name, block, status label (Delivered / Built / In development), and a working link; at launch it lists f1_analytics (Built) and retail_analytics (In development).
- **CAP-7** About the Builder page
  - **intent:** A recruiter arriving from the resume or LinkedIn reads who Antonio is.
  - **success:** The page carries the About text verbatim from `canonical-copy.md` and is linked from the resume and LinkedIn.
- CAP-8 (Contact page) was retired; the Contact page is left as-is.
- **CAP-9** AI-readable identity
  - **intent:** AI engines find one consistent story about Antonio and How Do I Data.
  - **success:** llms.txt is live; Person JSON-LD validates; the canonical story string is identical in JSON-LD, llms.txt, About, LinkedIn, and GitHub.
- **CAP-10** GitHub presence
  - **intent:** GitHub shows only work that backs the site's claims.
  - **success:** The repo state matches `github-repos.md`: only the listed repos are public, the listed deletions are done, both adopted README drafts are applied, and the profile/`sameAs` choice is made.
- **CAP-11** Idea-to-production build record
  - **intent:** A prospective client can follow the flagship demo request from brainstorm to production and see where AI worked, where a human reviewed, and how tests, CI, and documentation kept it standard and visible.
  - **success:** The flagship repo contains the committed BMAD artifacts for every stage in `demo-story.md` plus a walkthrough doc linking them; each story-level change shows its review outcome and a green CI run; Chapter 4 summarizes it and links there.
- **CAP-12** Flagship LLM landing page
  - **intent:** LLMs and crawlers reading the flagship repo's landing page get the full demo story: what the demo company and question are, the four chapters, the build record, and where the data and dashboard live.
  - **success:** The flagship repo's README carries every item listed in `llm-landing-page.md`, every number on it is measured or labeled simulated, and nothing on it contradicts howdoidata.com.

- **CAP-13** Flagship data catalog
  - **intent:** Anyone reading the flagship repo finds every business term, metric, model, and column defined once, versioned with the code.
  - **success:** Every source, model, and column has a dbt YAML description; business terms use shared doc blocks; a generated `CATALOG.md` is committed; CI fails when a description is missing or `CATALOG.md` is stale; the README and Chapter 4 link to it.

- **CAP-14** Site structure and navigation
  - **intent:** A visitor moves through a standard site: a clear site map, header, footer, and mobile navigation, consistent page templates, predictable URLs, SEO metadata, and accessible pages.
  - **success:** Every page appears in the site map and navigation in `EXPERIENCE.md`, styled per `DESIGN.md`, is built from its shared template, has a unique SEO title and meta description, passes WCAG 2.2 AA checks, and every retired URL 301-redirects to its replacement.

## Constraints

- Squarespace (native llms.txt in SEO settings; code injection available for JSON-LD); no own static site yet.
- Every claim of skill on a page links to a public demo or uses approved past-work wording; the site itself proves nothing.
- The impact rule, banned phrasing, and naming rules in `editorial-rules.md` govern all copy.
- Canonical story, short form, and About text are copied verbatim from `canonical-copy.md`.
- Fixed block names in URLs, structured data, and llms.txt; headlines are for people.
- The flagship company is a fictional outdoor gear shop (online plus one store); all its data is synthetic and every result is labeled simulated.
- The flagship story page and block excerpts ship only once the demo artifacts exist; the story never appears without real data.
- The flagship is built with BMAD, and every BMAD artifact committed to a public repo is public-safe: no secrets, internal names, or client or employer content.
- AI appears only as used inside analytics workflows with data limits, human review, and a record of what it did; never building or training models.
- Flagship code is modular and expandable (layered models; new grains, milestones, channels, and attribution rules added on top), held to coding standards, with explicit human review points.
- Flagship definitions live once, in dbt YAML; no hosted docs site.
- Each flagship report type is one parameterized model; periods, milestones, and cohort offsets are settings, not copied queries.
- No cart or commerce.
- Every site page is placed in the site map and navigation and built from shared page templates, with URL, SEO title, meta description, and accessibility checks; no one-off layouts, MVP included.

## Non-goals

- Own static site (deferred).
- Client/Recruiter toggle.
- Later demo releases: QBR pack (heatmaps, campaign summaries, referral payoff, online vs store mix, age groups) on the same model layers, full catalog tool (OpenMetadata or DataHub), Firebase emulator, mock APIs, Census data, Retention pillar, decks, AI summaries.
- Building or training ML models as a service.
- Naming industries served.
- Contact page changes (left as-is for now).
- A GitHub Pages site for the flagship repo; the website plus GitHub for code is the scope.

## Success signal

- A prospective SMB client lands on Home, opens a block page, follows the flagship story through four chapters each showing real demo output, then opens the build record and sees where AI worked and where Antonio reviewed it, without hitting a claim that breaks the impact rule.
- An AI engine asked about Antonio Galvan or How Do I Data has only one version of the story to find, because all its surfaces (site JSON-LD, llms.txt, About, LinkedIn, GitHub) carry it word for word.

## Assumptions

- The data-limit control is met because AI only sees synthetic demo data and repo content; the committed BMAD artifacts are the record.
- Until CAP-3 ships, block pages use f1_analytics and approved past-work lines as proof and list the flagship demo as In development.
