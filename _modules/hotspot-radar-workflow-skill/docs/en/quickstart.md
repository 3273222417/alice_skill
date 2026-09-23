# Quick start

[中文主入口](../../README.md) · [English docs](README.md)

## Requirements

- Node.js 18 or newer.
- A local Agent runtime that supports Skills.
- A TikHub token only for real retrieval.

## Install and test

```bash
git clone --branch v0.1.4 --depth 1 https://github.com/slalomboy/hotspot-radar-workflow-skill.git
cd hotspot-radar-workflow-skill
npm run check
npm test
npm run first-run
```

The final command should clearly report whether real retrieval is available. A missing token is a blocked external capability, not a successful empty result.

## Run a theme

After the user configures a valid token in secure storage:

```bash
npm run topic -- "AI automation projects"
```

Review the generated owner checklist before drafting content.
