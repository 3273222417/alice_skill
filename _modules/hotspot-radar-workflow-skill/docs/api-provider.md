# API Provider

This Skill currently uses TikHub as the default data provider for Douyin candidate search and comment evidence.

## Default Base URL

`https://api.tikhub.io`

Use another base URL only if you understand and trust that provider. Never send a TikHub token to an unapproved domain.

## Token Sources

The resolver checks in this order:

1. `TIKHUB_API_KEY` environment variable.
2. macOS Keychain service `hotspot_radar_tikhub_api_token` with the current user.
3. Legacy macOS Keychain service `ai_anget_tikhub_api_token` with account `dalin`.

## Endpoints Used

### Douyin Search

`POST /api/v1/douyin/search/fetch_general_search_v2`

Purpose:

- Search Douyin content by expanded keyword.
- Return candidate videos and basic metadata.

Important fields expected by the normalizer:

- `aweme_id` or `group_id`
- `desc`
- `author`
- `statistics.digg_count`
- `statistics.comment_count`
- `statistics.collect_count`
- `statistics.share_count`
- `create_time`

### Douyin Comments

`GET /api/v1/douyin/app/v3/fetch_video_comments`

Purpose:

- Fetch a small sample of comments for high-ranking candidates.
- Estimate user demand and evidence completeness.

Important fields expected:

- `data.comments`
- `cid`
- `text`
- `digg_count`
- `create_time`

## Cost And Quota

The default request budget is 25 per run. A typical run uses search requests for enabled keywords and comment requests for top candidates.

Always check your provider pricing and permission scope before using this workflow at scale.

## Provider Adapter Boundary

The current scripts are written around TikHub, but the workflow expects provider outputs to be normalized into a common content candidate shape:

- platform
- content ID
- URL
- author
- title or description
- publish time
- likes
- comments
- favorites
- shares
- source keyword
- missing data markers
- raw response path

