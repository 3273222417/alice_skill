# Usage

## Simple Mode

Run one command with one theme:

`npm run topic -- "AI 自动化真实项目"`

Equivalent direct command:

`node scripts/run-topic-checklist.mjs "AI 自动化真实项目"`

## What Happens

The workflow runs:

1. First-run check.
2. Keyword expansion.
3. Douyin candidate search through TikHub.
4. Data normalization.
5. Comment evidence sampling.
6. Content opportunity scoring.
7. Same-theme deduplication.
8. Owner checklist generation.

## Output

The main user-facing output is:

`reports/gate-1/<run-id>-owner-review-checklist.md`

Users mark each candidate:

- `要做`
- `可观察`
- `不要做`

## Same Theme Deduplication

Returned candidates are recorded in:

`data/gate-1/owner-review-history.json`

The next run with the same normalized theme excludes previous candidate IDs and near-duplicate topic fingerprints.

If fewer than 10 new candidates remain, the report says so instead of refilling with old candidates.

## Advanced Mode

Run the lower-level fetch and scoring pipeline:

`node scripts/run-gate1-topic-validation.mjs topic-ai-001 "AI 自动化真实项目"`

Then build the owner checklist:

`node scripts/build-gate1a-owner-review.mjs topic-ai-001 reports/gate-1/topic-ai-001-owner-review-checklist.md`

