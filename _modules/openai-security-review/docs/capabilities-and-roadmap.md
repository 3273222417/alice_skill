# Capabilities and Roadmap

[English](capabilities-and-roadmap.md) | [简体中文](capabilities-and-roadmap.zh-CN.md)

This document summarizes what `openai-security-review` can do today and how its security-review coverage should evolve.

The project is built for authorized defensive review of local repositories, local/staging web applications, and explicitly approved targets. Its default posture is static analysis, passive observation, and read-only validation. Active probes are narrow, guarded, and opt-in.

## Current Capabilities

### 1. Workflow Orchestration

- Unified scheduler through `scripts/osr.mjs`.
- JSON configuration through `references/osr.config.example.json`.
- Stage selection with `--only`, `--skip`, and `--dry-run`.
- Stateful audit workspaces with `state/`, `evidence/`, `reports/`, and Markdown notes.
- Consolidated report generation through `scripts/generate_report.py`.

### 2. Static Attack-Surface Inventory

- Repository inventory for security-sensitive files and patterns.
- Detection of auth/session/token/cookie references.
- Detection of role, permission, admin, tenant, organization, owner, and policy references.
- Detection of API clients, route-like files, redirects/callbacks, file handling, DOM/XSS sinks, SSRF-like URL fetchers, and secret-like config.
- Redaction of secret-like values in snippets and reports.

### 3. Backend Analysis

- Backend framework fingerprinting for common Node.js, Python, Java/Kotlin, Go, Ruby, PHP, and .NET patterns.
- Server route mapping for common framework route declarations.
- Route-level authentication and authorization signal analysis.
- Input validation coverage checks for mutating and high-risk routes.
- Source-to-sink review queue for request input near SQL/NoSQL, command, outbound request, file path, redirect, template, and deserialization sinks.
- Server-specific checks for CORS, CSRF, cookies, JWT handling, weak crypto, debug leakage, secret-like configuration, path traversal, SSRF fetchers, redirects, Docker posture, and dependency manifests.
- API spec mapping for OpenAPI, Swagger, and GraphQL schema files.

### 4. Browser And Runtime Observation

- Playwright runtime as a standard project dependency.
- Authenticated login helper using credentials from environment variables.
- Passive same-origin crawl with non-read HTTP methods blocked.
- Runtime API/request map from observed same-origin `fetch`, `xhr`, and API-like traffic.
- Console warning/error collection and page metadata capture.
- Safe read-only validation for headers, source maps, HTML signals, and obvious error leakage.

### 5. API And Permission Coverage

- Source API map from API-like strings, fetch/axios calls, route files, and method hints.
- Source/runtime API coverage comparison.
- Role/permission matrix for anonymous and authenticated profiles.
- Environment-backed headers for bearer-token test profiles.
- Same-origin read-only endpoint checks for `GET`, `HEAD`, and `OPTIONS`.

### 6. Guarded Active Validation

- Active-validation plan creation with explicit authorization.
- Guarded active probes requiring both config authorization and runtime confirmation.
- Low-risk probes for CORS, redirect parameters, benign reflection, verbose errors, and public debug/config exposure.
- Local-target default; non-local targets require explicit remote allowance.

### 7. Reporting

- Consolidated Markdown report with scope, stage status, auth state, backend sections, hypotheses, findings, inventories, API coverage, permission matrix, validation results, active validation, and evidence files.
- Finding template with severity, status, location, evidence, impact, reasoning, fix, and test.
- Hypothesis queue that combines static inventory and backend analysis signals.

## Current Boundaries

- The system creates review queues and evidence. It does not claim exploitability without confirmation.
- Static dataflow is heuristic and proximity-based, not a full taint engine.
- Route parsing is framework-pattern based, not a complete AST parser for every language.
- Browser crawling is path-dependent and may miss workflows requiring complex interaction.
- Active probes are intentionally narrow and do not submit forms, mutate data, brute force, fuzz, or run destructive payloads.
- Secrets are redacted, but users should still avoid running reviews on repositories they are not authorized to inspect.

## Future Roadmap

### Phase 1: Precision And Test Fixtures

Goal: make current backend parsing more stable and measurable.

- Add fixture apps for Express, NestJS, FastAPI, Django, Spring Boot, Gin, Rails, Laravel, and Next.js API routes.
- Add snapshot tests for generated JSON state files.
- Add regression tests for false positives on pure frontend repositories.
- Add CI checks for `npm run check`, skill validation, and fixture snapshots.

### Phase 2: Structured Parsers

Goal: reduce regex limitations where language tooling is available.

- Parse JavaScript/TypeScript route files with AST tooling.
- Parse Python decorators and Pydantic/FastAPI models more precisely.
- Parse Java/Kotlin annotations and Spring Security expressions.
- Parse Go router groups and middleware chains.
- Normalize route parameters across `:id`, `{id}`, `<id>`, and framework-specific forms.

### Phase 3: Middleware And Policy Chain Mapping

Goal: connect routes to effective protection layers.

- Track Express/Fastify/Koa global and router-level middleware.
- Track NestJS guards, interceptors, pipes, and decorators.
- Track FastAPI dependencies and router-level dependencies.
- Track Spring Security filters, annotations, and route matchers.
- Distinguish public routes, authenticated routes, and authorization-enforced routes.

### Phase 4: Deeper Dataflow Analysis

Goal: move beyond file/proximity hints toward traceable source-to-sink paths.

- Track variable assignments and function calls within route handlers.
- Link controllers to services, repositories, and database access layers.
- Classify sinks as parameterized, sanitized, allowlisted, or unsafe.
- Add framework-specific sink rules for Prisma, TypeORM, SQLAlchemy, Django ORM, Hibernate/JPA, GORM, ActiveRecord, and Eloquent.
- Add confidence levels such as `confirmed_pattern`, `likely`, and `needs_manual_trace`.

### Phase 5: Validation And Schema Coverage

Goal: make route-boundary validation coverage more concrete.

- Map request schemas to routes.
- Detect global validation pipelines.
- Extract allowed fields, required fields, enum constraints, size constraints, file type limits, and custom validators.
- Flag routes that read body/query/path data before validation.
- Suggest missing validation tests.

### Phase 6: Runtime Coverage Expansion

Goal: improve read-only dynamic evidence without increasing risk.

- Correlate backend runtime probes with source route map entries.
- Support authenticated cookie reuse from Playwright storage state in backend probes.
- Add read-only health, version, OpenAPI, Swagger, GraphQL, and debug exposure checks.
- Add route status comparison across role profiles using source routes, API specs, and runtime observations.
- Add stop conditions for unexpected redirects, mutation-on-GET behavior, and unstable targets.

### Phase 7: API Contract And GraphQL Depth

Goal: make API contract review useful for larger services.

- Parse OpenAPI YAML with a proper YAML parser when available.
- Support Swagger UI config discovery.
- Parse GraphQL introspection JSON.
- Compare GraphQL Query/Mutation operations with resolver files.
- Report documented-but-unimplemented, implemented-but-undocumented, and runtime-only endpoints.

### Phase 8: Report Quality And Remediation

Goal: turn review output into engineering-ready work.

- Generate finding candidates with clearer evidence grading.
- Add suggested fixes and regression tests for common issue families.
- Add fix-order prioritization by severity, reachability, and confidence.
- Export reports as Markdown, JSON, and SARIF-like machine-readable output.
- Add optional issue templates for GitHub/GitLab trackers.

### Phase 9: Distribution And UX

Goal: make the project easier to install and run outside one Codex workspace.

- Add a thin CLI wrapper while keeping the Codex skill as the primary interface.
- Add `init` command to create `osr.config.json` interactively.
- Add `doctor` command for runtime and Playwright checks.
- Add examples for common review modes: frontend-only, backend-only, authenticated web app, API-only, and role-matrix review.
- Add release tags and changelog.

### Phase 10: Safety And Governance

Goal: keep deeper capability aligned with defensive use.

- Keep destructive, brute-force, credential attack, and data-exfiltration behaviors out of the project.
- Require explicit authorization and runtime confirmation for any active probe.
- Keep runtime probes read-only by default.
- Redact secrets in state, evidence, and reports.
- Add a security policy for responsible disclosure of issues found in this tool.

## Near-Term Priority

1. Fixture-based tests for backend stages.
2. Middleware/policy chain mapping for Node.js and Python frameworks.
3. Improved route-to-validation mapping.
4. Better API spec parsing and GraphQL support.
5. Runtime correlation between route maps, role matrix, backend probes, and API coverage.
6. Report improvements with fix and test suggestions.
