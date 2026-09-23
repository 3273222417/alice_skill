# Installation

## 1. Requirements

- Node.js 18 or newer.
- A TikHub API Token.
- macOS is recommended because the setup script stores tokens in Keychain.

## 2. Install The Skill

This repository root is the installable Skill folder. It contains `SKILL.md`, `scripts/`, `docs/`, and `assets/` directly at the top level.

Codex Skill Installer:

`$skill-installer install https://github.com/slalomboy/hotspot-radar-workflow-skill/tree/v0.1.4`

After installing, restart Codex so the new Skill can be discovered.

Manual install:

1. Clone or download this repository.
2. Copy the repository folder into your Codex skills directory.
3. Confirm the installed folder contains `SKILL.md` and `scripts/`.
4. Restart Codex.

The package should include:

- `SKILL.md`
- `README.md`
- `INSTALL.md`
- `FIRST-RUN-CHECKLIST.md`
- `assets/workflow-overview.svg`
- `assets/keyword-expansion.svg`
- `scripts/first-run-check.mjs`
- `scripts/setup-tikhub-token.mjs`
- `scripts/run-topic-checklist.mjs`
- `scripts/run-gate1-topic-validation.mjs`
- `scripts/build-gate1a-owner-review.mjs`
- `scripts/tikhub-token.mjs`

## 3. First-Run Check

Run:

`npm run first-run`

or:

`node scripts/first-run-check.mjs`

If it reports `总体状态：尚未就绪`, follow the printed next step.

## 4. Configure TikHub Token

Open:

`https://user.tikhub.io/dashboard/api`

Copy your API Token, then run:

`npm run setup-token`

or:

`node scripts/setup-tikhub-token.mjs`

The interactive prompt hides token input in terminals that support `stty -echo`.

## 5. Verify

Run:

`npm run first-run`

Ready state:

`总体状态：可真实抓取`
