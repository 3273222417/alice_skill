# OpenAI Security Review Skill for Codex

[English](README.md) | [简体中文](README.zh-CN.md)

A Codex-native security review skill for authorized repositories and web applications. It combines source analysis, browser-based observation, API coverage, role/permission checks, guarded active probes, and Markdown reporting.

> For authorized defensive testing only. This project does not run brute force, destructive requests, data exfiltration, or mutation-heavy exploit payloads.

For the full capability map and future roadmap, see [Capabilities and Roadmap](docs/capabilities-and-roadmap.md).

## Features

- Stateful audit workspaces with notes, evidence, JSON state, and reports.
- Static attack-surface mapping for routes, API clients, auth/session logic, roles, tokens, redirects, file handling, SSRF-like URL fetchers, XSS sinks, and secret-like configuration.
- Backend framework fingerprinting, server route mapping, authz signal analysis, validation coverage, source-to-sink review queues, server hardening checks, and API spec coverage.
- Vulnerability hypothesis generation from source signals.
- Playwright login with test credentials loaded from environment variables.
- Safe read-only validation for security headers, HTML signals, source maps, and obvious error leakage.
- Passive same-origin Playwright crawling with non-read methods blocked.
- Runtime API/request mapping from observed `fetch`, `xhr`, and `/api` traffic.
- Source API mapping from API-like strings, fetch/axios calls, route files, and method hints.
- Source/runtime API coverage comparison.
- Role/permission matrix checks for anonymous, user, admin, or tenant profiles.
- Explicit active-validation planning.
- Guarded active probes that require both config authorization and runtime confirmation.
- Consolidated Markdown reports.

## Repository Layout

```text
.
  README.md
  README.zh-CN.md
  LICENSE
  SKILL.md
  agents/openai.yaml
  docs/
  package.json
  references/osr.config.example.json
  references/review-playbook.md
  references/report-template.md
  scripts/
```

## Installation

Install the skill from GitHub:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Why-WU/codex-security-review \
  --path . \
  --name openai-security-review
```

Restart Codex, then install the runtime dependencies:

```bash
cd ~/.codex/skills/openai-security-review
npm install
npm run setup
```

If Chromium is missing:

```bash
npx playwright install chromium
```

## Quick Start

Ask Codex:

```text
Use openai-security-review to audit /path/to/repo. The target URL is http://localhost:5173.
```

For repeatable runs, use the scheduler:

```bash
cd ~/.codex/skills/openai-security-review
cp references/osr.config.example.json ./osr.config.json
```

Edit `osr.config.json`:

```json
{
  "target": {
    "repo": "/path/to/repo",
    "url": "http://localhost:5173"
  },
  "workspace": {
    "path": "/tmp/openai-security-review-demo"
  }
}
```

Preview the workflow:

```bash
npm run scan -- --config ./osr.config.json --dry-run
```

Run the review:

```bash
npm run scan -- --config ./osr.config.json
```

The final report is written to:

```text
<workspace>/reports/report.md
```

## Authentication

If the application requires login, enable `auth`:

```json
{
  "auth": {
    "enabled": true,
    "loginUrl": "http://localhost:5173/login",
    "usernameEnv": "OSR_USERNAME",
    "passwordEnv": "OSR_PASSWORD",
    "usernameSelector": "input[name=\"email\"]",
    "passwordSelector": "input[name=\"password\"]",
    "submitSelector": "button[type=\"submit\"]",
    "successUrlContains": "/dashboard"
  }
}
```

Set credentials with environment variables:

```bash
export OSR_USERNAME="test@example.com"
export OSR_PASSWORD="test-account-password"
npm run scan -- --config ./osr.config.json
```

Credentials are not written to config files, evidence files, or reports.

## API Mapping And Coverage

The workflow can produce:

- `state/api_map.json`: runtime requests observed by Playwright.
- `state/source_api_map.json`: API hints discovered from source code.
- `state/api_coverage.json`: source/runtime overlap, source-only endpoints, and runtime-only endpoints.

Markdown evidence is written to:

```text
evidence/api_map.md
evidence/source_api_map.md
evidence/api_coverage.md
```

## Backend Analysis

Enable the backend stages in `osr.config.json`:

```json
{
  "backend": {
    "enabled": true,
    "frameworkHints": [],
    "fingerprint": true,
    "routeMap": true,
    "authzMap": true,
    "dataflowRiskMap": true,
    "validationCoverage": true,
    "serverChecks": true,
    "apiSpecMap": true,
    "apiSpecPaths": [],
    "runtimeValidation": false,
    "runtimeProbePaths": []
  }
}
```

The backend stages generate server framework, route, authz, validation, dataflow, hardening, and API contract state files. JavaScript and TypeScript scanning is scoped to server-like paths and framework signals, such as `server/`, `backend/`, `routes/`, `controllers/`, `middleware/`, `pages/api/`, and Next.js `app/**/route.ts`.

Run only the backend stages:

```bash
npm run scan -- --config ./osr.config.json --only backend
```

Backend runtime validation is opt-in. It sends only same-origin `GET`, `HEAD`, and `OPTIONS` requests and never sends request bodies.

## Role / Permission Matrix

Enable `accessMatrix` to compare read-only endpoint responses across profiles:

```json
{
  "accessMatrix": {
    "enabled": true,
    "maxEndpoints": 50,
    "includeSourceOnly": true,
    "includeUnknownSourceAsGet": false,
    "profiles": [
      {
        "name": "anonymous"
      },
      {
        "name": "admin",
        "storageState": "/tmp/openai-security-review-demo/state/authenticated-storage-state.json",
        "expectAccess": true
      }
    ],
    "paths": []
  }
}
```

The matrix only sends same-origin read-only requests for `GET`, `HEAD`, and `OPTIONS` endpoints. It records status codes per profile and highlights signals such as unexpected anonymous success or unexpected denial.

For bearer-token APIs, use environment-backed headers:

```json
{
  "name": "admin-api",
  "headersFromEnv": {
    "Authorization": "OSR_ADMIN_AUTH_HEADER"
  },
  "expectAccess": true
}
```

Then:

```bash
export OSR_ADMIN_AUTH_HEADER="Bearer test-token"
```

## Guarded Active Probes

Active probes are off by default. To enable them:

```json
{
  "active": {
    "enabled": true,
    "authorized": true,
    "executeSafeProbes": true,
    "probeClasses": ["cors", "redirect", "xss", "error", "exposure"],
    "allowRemote": false,
    "timeout": 10
  }
}
```

Run with runtime confirmation. In interactive runs, the scheduler shows two options after the static/passive stages finish: `ACTIVE` or `NOT ACTIVE` (default). In non-interactive runs, pass `--confirm-active` explicitly:

```bash
npm run scan -- --config ./osr.config.json --confirm-active
```

Guarded probes cover:

- CORS arbitrary-origin checks.
- Benign open-redirect parameter checks.
- Benign reflection marker checks.
- Verbose error/debug leakage checks.
- Public config/debug exposure checks.

They do not brute force, submit forms, mutate data, or run destructive payloads. Non-local targets are refused unless `allowRemote` is explicitly enabled.

## Useful Commands

Run static source mapping and report generation:

```bash
npm run scan -- --config ./osr.config.json --only workspace,inventory,hypotheses,source-map,report
```

Skip browser-based stages:

```bash
npm run scan -- --config ./osr.config.json --skip auth,crawl,access-matrix,active
```

Run guarded active probes after explicit authorization in non-interactive mode:

```bash
npm run scan -- --config ./osr.config.json --confirm-active
```

Validate the runtime:

```bash
npm run check
```

## Output Files

Typical workspace output:

```text
00-scope.md
01-inventory.md
02-findings.md
03-hypotheses.md
state/
  manifest.json
  attack_surface.json
  hypotheses.json
  passive_validation.json
  passive_crawl.json
  api_map.json
  source_api_map.json
  api_coverage.json
  backend_fingerprint.json
  server_route_map.json
  authz_map.json
  dataflow_risk_map.json
  validation_coverage.json
  server_security_checks.json
  api_spec_map.json
  backend_runtime_validation.json
  role_matrix.json
  active_validation.json
  active_probe.json
evidence/
  passive_validation.md
  passive_crawl.md
  api_map.md
  source_api_map.md
  api_coverage.md
  backend_fingerprint.md
  server_route_map.md
  authz_map.md
  dataflow_risk_map.md
  validation_coverage.md
  server_security_checks.md
  api_spec_map.md
  backend_runtime_validation.md
  role_matrix.md
  active_validation_plan.md
  active_probe.md
reports/
  report.md
```

## Safety Model

- Use only on systems you own or are explicitly authorized to test.
- Prefer local or staging environments.
- Use dedicated test accounts and synthetic data.
- Keep credentials in environment variables.
- Passive crawl blocks non-read methods.
- Role matrix uses same-origin read-only requests.
- Active probes require config authorization and runtime confirmation.
- Review project-specific validators separately before use.
