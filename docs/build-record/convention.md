# Build-record convention

Every story that changes this repo leaves one record file. This is how. The walkthrough that collects the
records is [README.md](README.md).

## When

- The record is written **in the pull request that carries the story**, as
  `docs/build-record/stories/<story-id>.md` (for example `stories/C-4.md`), copied from
  [`stories/_template.md`](stories/_template.md). That is either the story's own PR or a batch PR (below).
- The same PR adds one row to the [story index](README.md#story-index) in the walkthrough, and updates a
  stage's status line if the story completes or advances that stage.
- Facts that only exist after the PR is opened (the PR link, the CI run, the review outcome) are added in a
  follow-up commit on the same branch before merge. After merge, a record changes only to correct a fact or
  to move its status on (for example In progress to Done, in both the record and its index row). That later
  PR says so. A record is never back-dated.

### Batch pull requests

Several stories may share one batch PR. Each story is still its own commit (or commits) on the batch
branch, and every commit message names its story id.

- Each story keeps its own record and index row. Until the batch PR exists, the record's `## Change` and
  `## CI run` sections say "pending batch PR".
- Once the batch PR is open, one follow-up commit fills in every record in the batch: the batch PR link
  and the CI run for the PR's last commit that changed more than the records. Each record still names its
  own story's commits.
- The review outcome is per story: findings are recorded in the record of the story they concern.

## Required sections

Each record has these headings, in this order (checked by `tests/test_build_record.py`):

1. `## Story spec`: the story id, title, and its description quoted from the plan, edited only for public
   safety. Link the spec capability it serves.
2. `## Change`: the PR link, or the commit if there was no PR (say why). One line on what changed.
3. `## Review outcome`: the human decision (who, approved or changes requested, at which review point) and
   the AI review findings, each accepted or rejected with a one-line reason. If nothing was recorded, say
   "None recorded." Never leave the section empty.
4. `## CI run`: the link to the PR's CI run (see below) and its result. If the change made no
   commit to this repo, say so.
5. `## Status`: `Done`, `In review`, or `In progress`, plus what remains. State status as it is; never claim
   an approval that has not been given.

## Recording review findings

Use one table row per finding:

| Source | Finding | Decision | Reason |
|---|---|---|---|
| AI review / human | What was found, in one line | Accepted / Rejected | Why, in one line |

Summarize; don't paste review transcripts. A finding that would itself break the public-safety check is
recorded only as "public-safety edit" with no detail.

## CI link

Copy the run URL from the PR's checks (`gh pr checks <pr>`) or the Actions tab. Use the run for the PR's
last commit that changed more than the record (for a batch PR, more than the records); the follow-up commit that only fills in the record is checked
by its own run on the PR. The run on the PR's final head commit must be green before merge. Only a green run counts as verification; a red run is recorded with what fixed it.

## Public-safety check before commit

Everything in this folder is public. Before each commit, read the diff and check that it contains:

- no secrets, tokens, keys, or email addresses (clearly fictional sample values on example domains,
  such as `x.com`, are allowed);
- no local file paths and no names of private repositories or internal working files;
- no names of employers or clients, and nothing about where an analysis shape came from;
- no internal scoring or evidence identifiers from the site's planning;
- no features the fictional shop doesn't have (see the constraints in the [spec](definition/spec.md));
- no real data: the shop is fictional and every number is synthetic or labeled simulated.

A grep over the diff for the terms behind each item is the minimum; any hit is either removed or explained
in the PR.
