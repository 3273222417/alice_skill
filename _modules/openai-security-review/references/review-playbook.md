# Review Playbook

This playbook adapts the useful shape of Shannon's pipeline into a safe Codex workflow. Default to static analysis and passive local verification. Active validation requires explicit authorization, a recorded plan, and a second confirmation before any probe is sent.

## Scope Checklist

- Repository path and branch/commit under review
- Target URL, if any
- Whether the target is local, staging, or production
- Explicit authorization and allowed techniques
- Authentication requirements and test accounts, if provided
- Login mechanism and allowed test credentials source
- Output location for notes/report

## Unified Scheduler

Prefer the scheduler for repeatable runs:

```bash
cd <skill-dir>
npm run scan -- --config ./osr.config.json
```

Start from `references/osr.config.example.json`. Use:

- `--dry-run` to preview commands
- `--skip auth,crawl` for static-only review
- `--only inventory,hypotheses,report` for a focused subset
- `--only backend` for server-side static analysis
- `--confirm-active` only after the user explicitly authorizes guarded active probes

If authorization is unclear, ask before any dynamic check. Never test a third-party target without explicit permission.

## Recon Commands

Use fast local inspection first:

```bash
rg --files
rg -n "auth|login|logout|session|token|jwt|cookie|permission|role|admin|tenant|org" .
rg -n "dangerouslySetInnerHTML|innerHTML|eval\\(|new Function|postMessage|localStorage|sessionStorage" .
rg -n "fetch\\(|axios|request\\(|XMLHttpRequest|baseURL|proxy|cors|csrf" .
rg -n "redirect|callback|returnUrl|next=|url=|href=|window\\.location" .
rg -n "process\\.env|VITE_|NEXT_PUBLIC_|REACT_APP_|API_KEY|SECRET|TOKEN|PASSWORD" .
```

Read package manifests and config:

- `package.json`, lockfiles, `.npmrc`
- Vite/Next/Webpack config
- API client modules
- router files and route guards
- auth/session providers
- env examples and Docker/config files

Or generate an inventory automatically:

```bash
python3 <skill-dir>/scripts/inventory.py --repo /path/to/repo --workspace /tmp/openai-security-review
```

Then generate a baseline hypothesis queue:

```bash
python3 <skill-dir>/scripts/hypothesize.py --workspace /tmp/openai-security-review
```

## Frontend Review Focus

- Token storage: prefer HttpOnly cookies for sessions; flag long-lived tokens in localStorage/sessionStorage.
- Route guards: verify privileged routes cannot be reached only by client-side hiding.
- API clients: check auth headers, base URL switching, retry behavior, error leaks, and tenant/org scoping.
- XSS: flag unsanitized HTML injection, markdown rendering, rich text, URL rendering, and unsafe `postMessage`.
- Redirects: validate return URLs, callbacks, OAuth redirects, and links derived from query params.
- File handling: check upload accept lists, previews, object URLs, download filename handling, and MIME assumptions.
- Secrets: public frontend env vars are not secret; report any real credential exposed to browser bundles.

## Backend/API Review Focus

When backend code is present, inspect:

- Authentication middleware on every protected endpoint
- Authorization checks on object access, mutations, admin actions, org/tenant boundaries
- Parameterized queries or ORM-safe query APIs
- Input validation at route boundaries
- CSRF protection when cookie-based sessions are used
- CORS origin allowlist and credential handling
- SSRF controls for URL fetchers, webhooks, importers, previews, and callbacks
- Rate limits on login, reset, invitation, and expensive endpoints
- Error handling that avoids leaking stack traces, tokens, and internal URLs

Automated backend stages:

```bash
python3 <skill-dir>/scripts/backend_fingerprint.py --repo /path/to/repo --workspace /tmp/openai-security-review
python3 <skill-dir>/scripts/server_route_map.py --repo /path/to/repo --workspace /tmp/openai-security-review
python3 <skill-dir>/scripts/authz_map.py --repo /path/to/repo --workspace /tmp/openai-security-review
python3 <skill-dir>/scripts/dataflow_risk_map.py --repo /path/to/repo --workspace /tmp/openai-security-review
python3 <skill-dir>/scripts/validation_coverage.py --repo /path/to/repo --workspace /tmp/openai-security-review
python3 <skill-dir>/scripts/server_security_checks.py --repo /path/to/repo --workspace /tmp/openai-security-review
python3 <skill-dir>/scripts/api_spec_map.py --repo /path/to/repo --workspace /tmp/openai-security-review
```

These write `state/backend_fingerprint.json`, `state/server_route_map.json`, `state/authz_map.json`, `state/dataflow_risk_map.json`, `state/validation_coverage.json`, `state/server_security_checks.json`, and `state/api_spec_map.json`. Treat them as review queues. Confirm each issue by tracing the effective middleware, route handler, validation layer, and deployment context.

Backend runtime validation is opt-in through `backend.runtimeValidation=true` in config. It sends only same-origin `GET`, `HEAD`, and `OPTIONS` requests, reuses authenticated storage-state cookies when configured, and writes `state/backend_runtime_validation.json`.

## Passive Dynamic Checks

Allowed by default only for local or explicitly authorized targets:

```bash
python3 <skill-dir>/scripts/safe_validate.py --target-url http://localhost:5173 --workspace /tmp/openai-security-review
```

Look for security headers, cache behavior, exposed source maps, obvious stack traces, and unexpected redirects. Do not send attack payloads by default.

## Passive Playwright Crawl

Use only for local/staging or explicitly authorized targets:

If the site requires login, first create an authenticated storage state with a dedicated test account:

```bash
export OSR_USERNAME="test@example.com"
export OSR_PASSWORD="test-account-password"

node <skill-dir>/scripts/auth_login.mjs \
  --workspace /tmp/openai-security-review \
  --login-url http://localhost:5173/login \
  --username-selector 'input[name="email"]' \
  --password-selector 'input[name="password"]' \
  --submit-selector 'button[type="submit"]' \
  --success-url-contains /dashboard
```

Do not put credentials in config files or shell history examples for real systems. Prefer short-lived test accounts and environment variables.

```bash
node <skill-dir>/scripts/passive_crawl.mjs \
  --url http://localhost:5173 \
  --workspace /tmp/openai-security-review \
  --max-pages 20 \
  --storage-state /tmp/openai-security-review/state/authenticated-storage-state.json
```

The crawler:

- navigates same-origin links only
- blocks non-read methods (`POST`, `PUT`, `PATCH`, `DELETE`, etc.)
- records page titles, response statuses, console warnings/errors, observed requests, and blocked requests
- does not submit forms, click buttons, mutate data, or send exploit payloads
- can reuse authenticated storage state created by `auth_login.mjs`
- writes `state/api_map.json` and `evidence/api_map.md` for observed same-origin API-like traffic

Treat JavaScript-loaded API requests as passive observations only. If the app mutates data on `GET`, stop and record the behavior as a risk.

## API / Request Map

Use `state/api_map.json` to identify:

- API-like `fetch`/`xhr` requests and `/api` paths
- method, path, origin, status counts, resource types, and source page
- endpoints requiring authenticated context
- endpoints that should be traced back to server-side authorization checks

Then correlate runtime observations with source-discovered API hints:

```bash
python3 <skill-dir>/scripts/source_api_map.py \
  --repo /path/to/repo \
  --workspace /tmp/openai-security-review
```

This writes:

- `state/source_api_map.json`: API-like source strings, methods, locations, and route files
- `state/api_coverage.json`: source/runtime overlap, source-only endpoints, and runtime-only endpoints
- `evidence/source_api_map.md` and `evidence/api_coverage.md`

Do not treat any single API map as complete. Passive crawling is path-dependent, source scanning is heuristic, and both should be combined with route/source review.

If OpenAPI, Swagger, or GraphQL specs are present, run:

```bash
python3 <skill-dir>/scripts/api_spec_map.py \
  --repo /path/to/repo \
  --workspace /tmp/openai-security-review
```

Use `backend.apiSpecPaths` in config when specs are generated or stored in non-obvious locations.

## Role / Permission Matrix

Use only with authorized local/staging targets and test profiles:

```bash
node <skill-dir>/scripts/role_matrix.mjs \
  --config ./osr.config.json \
  --url http://localhost:5173 \
  --workspace /tmp/openai-security-review
```

Configure `accessMatrix.profiles` with profile names and optional Playwright storage states. The matrix sends only read-only same-origin requests for `GET`, `HEAD`, and `OPTIONS` endpoints from the runtime/source API maps. It records status codes per profile and flags signals such as anonymous success on sensitive-looking paths or unexpected access based on `expectAccess` / `expectDenied`.

For bearer-token APIs, use `headersFromEnv` in the profile config so secret header values come from environment variables and are never printed.

## Authorized Active Validation

Active validation is off by default. Create a plan only after the user confirms authorization:

```bash
python3 <skill-dir>/scripts/active_validate.py \
  --workspace /tmp/openai-security-review \
  --target-url http://localhost:5173 \
  --classes auth,authz,xss,injection,ssrf \
  --i-am-authorized
```

For guarded active probes, use a second confirmation:

```bash
python3 <skill-dir>/scripts/active_probe.py \
  --workspace /tmp/openai-security-review \
  --target-url http://localhost:5173 \
  --classes cors,redirect,xss,error,exposure \
  --i-am-authorized \
  --confirm-active
```

The probe helper is intentionally narrow:

- sends only low-risk `GET`, `HEAD`, and `OPTIONS` style checks
- refuses non-local targets unless `--allow-remote` is explicitly supplied
- checks CORS, possible open redirect parameters, benign reflection markers, verbose error leakage, and public debug/config exposure
- records every probe in `state/active_probe.json` and `evidence/active_probe.md`
- does not brute force, submit forms, mutate data, exfiltrate data, or run destructive payloads

To go further, create a project-specific validator with reviewed payloads, test accounts, cleanup steps, and a written stop condition.

## Evidence Standards

Classify evidence:

- Confirmed: code path proves the issue or safe passive check confirms it.
- Likely: strong code evidence but runtime behavior not verified.
- Needs validation: plausible risk requiring app context, credentials, or dynamic testing.
- Informational: hardening or hygiene improvement.

Avoid reporting theoretical concerns without a concrete code path.

## Severity Guide

- Critical: unauthenticated data access, auth bypass, remote code execution, credential exposure, destructive privilege escalation.
- High: cross-tenant/object access, stored XSS in privileged context, exploitable injection, SSRF to sensitive services.
- Medium: reflected/self-XSS with constraints, weak session/token handling, missing CSRF in sensitive flows, permissive CORS with credentials.
- Low: missing hardening headers, verbose errors in non-production, dependency hygiene without reachable exploit evidence.

## Fix Strategy

Prefer small, testable remediations:

- Add server-side authorization checks, not only UI guards.
- Centralize input validation at boundaries.
- Replace string-built queries/commands with parameterized APIs.
- Sanitize HTML only when rich rendering is required; otherwise render as text.
- Move secrets out of client-exposed env vars.
- Add regression tests that fail before the fix and pass after.

## Report Generation

After writing findings into `02-findings.md`, generate the report:

```bash
python3 <skill-dir>/scripts/generate_report.py --workspace /tmp/openai-security-review
```
