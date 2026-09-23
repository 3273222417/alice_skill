# Hotspot Radar Workflow Skill

[中文](README.md) · [FIN-SV-004 finished capability](docs/en/productization-map.md)

[中文主入口](README.md) · [English documentation index](docs/en/README.md)

Hotspot Radar turns one content theme into an evidence-backed shortlist for human review. It expands search terms, normalizes candidate records, scores opportunity signals, removes repeated results, and produces a ten-item decision checklist.

It is designed for short-video creators and content teams that want a traceable research process instead of endless platform browsing. It is not a viral-hit predictor, scraper bypass, rewrite engine, or publishing tool.

**Current status:** `v0.1.4` is a fixed source version. Script checks and 19 deterministic tests are verified. **Next step:** install the fixed Tag, run the local first-run check, and configure a lawfully obtained third-party API token only when real retrieval is required.

## What problem does it solve?

Creators often search with too few keywords, overvalue raw likes, review the same candidates repeatedly, and lose the reasons behind a topic decision. This Skill keeps keyword sources, missing fields, evidence scores, risks, and the final human decision in a reproducible workflow.

## Install

```bash
git clone --branch v0.1.4 --depth 1 https://github.com/slalomboy/hotspot-radar-workflow-skill.git
cd hotspot-radar-workflow-skill
npm run check
npm test
```

The repository root is the installable Skill folder. A Codex Skill installer can use the fixed path:

```text
$skill-installer install https://github.com/slalomboy/hotspot-radar-workflow-skill/tree/v0.1.4
```

## First call

Run `npm run first-run`. Without a token, the command must explain that real retrieval is unavailable rather than fabricating results. After the user configures a valid TikHub token in secure storage, run:

```bash
npm run topic -- "AI automation projects"
```

The useful output is a set of keyword nodes, normalized candidates, evidence scores, and an owner checklist marked `do / observe / skip`.

## Workflow and evidence

The workflow expands a theme into enabled search terms, calls the configured provider, preserves missing values, samples comments for demand signals, applies an opportunity score, removes prior results, and asks a human to make the final decision. Scores support review; they do not promise reach or conversion.

## Verified scope

- Node.js syntax checks pass for the workflow scripts.
- 19/19 deterministic tests pass.
- Repository-root Skill layout and no-token failure behavior are covered.

Real provider availability, current platform rules, pricing, quotas, and data rights remain runtime facts.

## Limitations, privacy, and third-party ownership

Do not commit API tokens, cookies, account credentials, downloaded videos, or customer information. The Skill does not bypass login or access controls, republish source videos, rewrite another creator line by line, or publish content. TikHub and Douyin remain third parties with separate terms.

## License and provenance

Original repository code and documentation use the [MIT License](https://github.com/slalomboy/hotspot-radar-workflow-skill/blob/v0.1.4/LICENSE). The license does not grant rights to TikHub services, platform data, or creator content.

Continue with the [English quick start](docs/en/quickstart.md), [usage guide](docs/en/usage.md), or [limitations](docs/en/limitations.md).
