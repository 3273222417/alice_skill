# Workflow

## 1. Theme Input

The user provides one broad theme:

`AI 自动化真实项目`

## 2. Keyword Expansion

The Skill expands the theme into enabled, candidate, and paused keywords.

Only enabled keywords are fetched in the current run.

## 3. Candidate Fetch

The Skill searches Douyin through TikHub and saves raw responses locally for traceability.

## 4. Normalization

Platform fields are normalized into a common candidate shape. Missing fields are marked as missing instead of faked as zero.

## 5. Evidence Sampling

The Skill fetches comments for top candidates when request budget allows. Comments help detect real user demand.

## 6. Opportunity Scoring

The score combines:

- interaction strength
- comment demand
- track relevance
- account fit
- transferability
- structure clarity
- freshness
- evidence completeness
- risk penalty

## 7. Same-Theme Deduplication

Previous checklist candidates are remembered by content ID and topic fingerprint.

The next run with the same theme excludes them.

## 8. Owner Checklist

The output is a 10-topic checklist, not a script package.

The user decides:

- `要做`
- `可观察`
- `不要做`

