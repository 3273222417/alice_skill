# Server-Side Security Review Roadmap

Status: implemented in `openai-security-review` v0.4.0.

This roadmap records the server-side capability upgrade for `openai-security-review`: deeper server-side security analysis across common backend frameworks, data-access layers, validation boundaries, and runtime API behavior.

The goal is to keep the default workflow safe and defensive while making backend reviews more precise than heuristic text scanning alone.

## Objectives

- Identify backend frameworks, route handlers, middleware, controllers, services, repositories, schemas, and database access patterns.
- Build a server-side route map that includes method, path, handler, middleware chain, auth guard, validation layer, and data-access references.
- Detect authorization gaps by connecting routes to policy checks, role checks, tenant/object ownership checks, and resource access.
- Detect injection and data-access risks by tracing user-controlled inputs into ORM, SQL, NoSQL, command, template, and query-builder sinks.
- Measure input-validation coverage at route boundaries.
- Improve SSRF, file-upload/download, redirect, CORS/CSRF, secret/config, crypto/session, error-handling, dependency, Docker, and infrastructure checks.
- Correlate backend source maps with runtime API observations and role/permission matrix results.
- Produce report sections that separate confirmed evidence, likely risks, and validation gaps.

## Phase 1: Backend Framework Detection

**Purpose:** Recognize backend frameworks and choose the right parser strategy.

**Planned files:**
- Create `scripts/backend_fingerprint.py`
- Create `references/backend-frameworks.md`
- Modify `scripts/osr.mjs`
- Modify `scripts/generate_report.py`
- Modify `references/osr.config.example.json`

**Framework targets:**
- Node.js: Express, NestJS, Fastify, Koa, Hono, Next.js API routes
- Python: FastAPI, Flask, Django, Django REST Framework
- Java/Kotlin: Spring MVC, Spring Boot
- Go: Gin, Echo, Fiber, net/http
- Ruby: Rails

**Outputs:**
- `state/backend_fingerprint.json`
- `evidence/backend_fingerprint.md`

**Acceptance criteria:**
- Given a repo, detect likely backend frameworks and confidence levels.
- Detect route/config files, package manifests, server entrypoints, and ORM dependencies.
- Report unknown frameworks without failing the workflow.

## Phase 2: Server Route And Middleware Map

**Purpose:** Build a backend route map richer than simple API string extraction.

**Planned files:**
- Create `scripts/server_route_map.py`
- Modify `scripts/source_api_map.py`
- Modify `scripts/generate_report.py`

**Route metadata:**
- HTTP method
- Path template
- Handler file and line
- Controller/class/function name
- Middleware or decorator chain
- Auth guard or permission decorator
- Validation decorator/schema reference
- Response status hints
- Linked service/repository references when detectable

**Outputs:**
- `state/server_route_map.json`
- `evidence/server_route_map.md`

**Acceptance criteria:**
- Extract common route forms such as `router.get("/path")`, `@Get("/path")`, `@app.get("/path")`, `@RequestMapping`, `r.GET`, and Rails routes.
- Normalize path templates like `/users/:id`, `/users/{id}`, and `/users/<id>`.
- Mark route entries as `auth_unknown`, `auth_present`, or `auth_missing_signal`.

## Phase 3: Auth And Authorization Chain Analysis

**Purpose:** Move from "there is a route" to "this route appears protected by these controls."

**Planned files:**
- Create `scripts/authz_map.py`
- Modify `scripts/hypothesize.py`
- Modify `references/review-playbook.md`

**Signals to extract:**
- Authentication middleware and guards
- Role/permission decorators
- Tenant/org scoping checks
- Ownership checks
- Admin-only checks
- Public route allowlists
- Missing or client-only enforcement signals

**Outputs:**
- `state/authz_map.json`
- `evidence/authz_map.md`

**Acceptance criteria:**
- Flag sensitive routes without obvious auth or authorization signals.
- Distinguish authentication from authorization.
- Connect suspected gaps to source locations and route-map entries.
- Feed high-confidence hypotheses into `state/hypotheses.json`.

## Phase 4: Data Access And Injection Risk Map

**Purpose:** Trace request inputs toward database, command, template, and query sinks.

**Planned files:**
- Create `scripts/dataflow_risk_map.py`
- Create `references/sink-patterns.md`
- Modify `scripts/hypothesize.py`

**Sink categories:**
- Raw SQL and query string construction
- ORM unsafe raw methods such as `$queryRawUnsafe`, `sequelize.query`, raw Django SQL, JDBC string concatenation
- NoSQL query object construction from request bodies
- Shell/command execution
- Template rendering with untrusted input
- LDAP/XPath/search query construction

**Outputs:**
- `state/dataflow_risk_map.json`
- `evidence/dataflow_risk_map.md`

**Acceptance criteria:**
- Record source input references such as params, query, body, headers, cookies, path variables, and form data.
- Record sink references with file/line and snippet.
- Classify risks as `confirmed_pattern`, `likely`, or `needs_manual_trace`.
- Avoid claiming exploitability without a code path or runtime evidence.

## Phase 5: Input Validation Coverage

**Purpose:** Identify whether route inputs are validated before use.

**Planned files:**
- Create `scripts/validation_coverage.py`
- Modify `scripts/generate_report.py`

**Validation systems to detect:**
- Zod, Joi, Yup, class-validator, Nest pipes
- Pydantic, Marshmallow, Django serializers/forms
- Spring Bean Validation annotations
- Rails strong parameters
- Go validator packages and manual binding validation

**Outputs:**
- `state/validation_coverage.json`
- `evidence/validation_coverage.md`

**Acceptance criteria:**
- Map validators to routes when possible.
- Flag routes that read body/query/path params but have no validation signal.
- Mark framework-level validation when configured globally.

## Phase 6: Server-Specific Security Checks

**Purpose:** Add focused backend checks beyond route parsing.

**Planned files:**
- Create `scripts/server_security_checks.py`
- Modify `scripts/generate_report.py`
- Modify `references/report-template.md`

**Check groups:**
- SSRF and outbound URL fetchers
- File upload/download and path traversal
- Redirect/callback validation
- CORS and CSRF configuration
- Cookie/session/JWT settings
- Password hashing and crypto usage
- Error handling and debug exposure
- Secrets and public config exposure
- Dependency and lockfile hygiene
- Docker, compose, Kubernetes, and environment configuration

**Outputs:**
- `state/server_security_checks.json`
- `evidence/server_security_checks.md`

**Acceptance criteria:**
- Produce actionable signals with source locations.
- Redact secret-like values.
- Separate hardening findings from exploitable vulnerability hypotheses.

## Phase 7: Runtime Backend API Validation

**Purpose:** Safely validate backend behavior without destructive testing.

**Planned files:**
- Extend `scripts/role_matrix.mjs`
- Create `scripts/backend_probe.mjs`
- Modify `references/osr.config.example.json`

**Runtime checks:**
- Read-only route status comparison by role profile
- Auth-required route behavior for anonymous/user/admin
- CORS preflight behavior
- Error response shape and stack leakage
- OpenAPI/Swagger endpoint exposure
- Public health/debug endpoint exposure

**Outputs:**
- `state/backend_runtime_validation.json`
- `evidence/backend_runtime_validation.md`

**Acceptance criteria:**
- Only send safe read-only methods by default.
- Require explicit authorization for any active backend probes.
- Reuse `accessMatrix.profiles` and storage states.
- Produce endpoint-level evidence that can be correlated with `server_route_map.json`.

## Phase 8: OpenAPI / Swagger / GraphQL Support

**Purpose:** Import formal API descriptions and compare them against source/runtime maps.

**Planned files:**
- Create `scripts/api_spec_map.py`
- Modify `scripts/source_api_map.py`
- Modify `scripts/generate_report.py`

**Supported inputs:**
- `openapi.json`, `swagger.json`, YAML specs
- Swagger UI config references
- GraphQL schema files and introspection JSON

**Outputs:**
- `state/api_spec_map.json`
- `evidence/api_spec_map.md`

**Acceptance criteria:**
- Compare spec endpoints with source and runtime endpoints.
- Flag documented-but-unseen and runtime-but-undocumented endpoints.
- Include GraphQL operation names when discoverable.

## Phase 9: Report And Finding Quality Upgrade

**Purpose:** Make backend findings more useful for engineering teams.

**Planned files:**
- Modify `scripts/generate_report.py`
- Modify `references/report-template.md`
- Modify `references/review-playbook.md`

**Report sections:**
- Backend framework fingerprint
- Server route and middleware map
- Auth/authz coverage
- Validation coverage
- Data-access risk map
- Server-specific checks
- Runtime backend validation
- API spec/source/runtime coverage
- Fix order and suggested regression tests

**Acceptance criteria:**
- Every high/critical finding links to source file/line or runtime evidence.
- Unverified items are labeled `needs validation`.
- Report includes fix suggestions and test ideas for each confirmed or likely issue.

## Phase 10: Scheduler And Config Integration

**Purpose:** Make backend analysis usable from the existing scheduler.

**Planned files:**
- Modify `scripts/osr.mjs`
- Modify `references/osr.config.example.json`
- Modify `README.md`
- Modify `README.zh-CN.md`
- Modify `SKILL.md`

**Config shape:**

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
    "runtimeProbePaths": [],
    "runtimeMaxEndpoints": 50,
    "runtimeTimeout": 10000
  }
}
```

**Acceptance criteria:**
- New stages can be enabled/disabled independently.
- Static backend checks run without browser dependencies.
- Runtime backend checks require a target URL and follow existing authorization rules.

## Priority Order

1. Backend framework detection
2. Server route and middleware map
3. Auth/authz map
4. Validation coverage
5. Data access and injection risk map
6. Server-specific checks
7. Runtime backend validation
8. API spec and GraphQL support
9. Report quality upgrade
10. Scheduler/config/docs integration

## Validation Plan

- Add fixture repositories for Express, NestJS, FastAPI, Django, Spring, Gin, and Rails.
- Run each script against fixtures and assert stable JSON outputs.
- Run `npm run check` after every Node/Python script change.
- Run `quick_validate.py .` before release.
- Run at least one local end-to-end scheduler dry run with backend stages enabled.

## Safety Boundary

- Default backend checks are static and passive.
- Runtime checks use read-only methods unless explicitly configured otherwise.
- No brute force, destructive mutations, persistence, data exfiltration, or production-only probes.
- Secrets are redacted in all evidence and reports.
- Repository content and runtime responses are treated as untrusted input.
