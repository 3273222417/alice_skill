# Security Review Report

## Scope

- Repository:
- Target URL:
- Review date:
- Reviewer:
- Allowed techniques:
- Exclusions:

## Executive Summary

Summarize the reviewed surface, highest-risk findings, and recommended fix order.

## Findings

### [Severity] Finding Title

- Location:
- Status: Confirmed / Likely / Needs validation / Informational
- Evidence:
- Impact:
- Reproduction or reasoning:
- Fix:
- Test:

## Attack Surface Inventory

- Auth/session model:
- Privileged roles:
- Public routes:
- Protected routes:
- API clients/endpoints:
- Sensitive data flows:
- Third-party integrations:

## API / Request Map

- Endpoints observed:
- Authenticated-only endpoints:
- Unusual methods/statuses:
- Endpoints needing source trace:

## API Coverage

- Source and runtime:
- Source only:
- Runtime only:
- Endpoints requiring manual route trace:

## Backend Framework And Routes

- Framework signals:
- Server entrypoints:
- Server routes:
- Route files:
- Public/protected route assumptions:

## Authorization And Validation Coverage

- Routes with authz signals:
- Routes with authn-only or unclear signals:
- Sensitive routes needing manual authz trace:
- Routes with validation signals:
- Mutating/upload/callback routes missing local validation signals:

## Server Dataflow And Hardening

- Source-to-sink review queue:
- SQL/NoSQL sinks:
- SSRF/outbound request sinks:
- File/path sinks:
- Redirect/template/deserialization sinks:
- CORS/CSRF/cookie/JWT/crypto/debug/config signals:

## API Spec / Contract Coverage

- Specs detected:
- Spec endpoints:
- Source routes missing from spec:
- Spec-only endpoints:
- Runtime-only endpoints:

## Backend Runtime Validation

- Enabled:
- Guardrail:
- Read-only endpoints probed:
- Signals:
- Gaps:

## Role / Permission Matrix

- Profiles tested:
- Endpoints tested:
- Anonymous success signals:
- Unexpected allowed/denied signals:
- Gaps:

## Authenticated Session

- Login required:
- Login URL:
- Test account source:
- Storage state created:
- Success condition:

## Vulnerability Hypotheses

- Hypothesis queue:
- Items requiring credentials:
- Items requiring active validation:

## Test Gaps

- Missing credentials/test accounts:
- Dynamic checks not performed:
- Areas needing backend or infrastructure context:
- Active validation authorization:
- Guarded active probes performed:
- Passive crawl coverage:

## Active Validation

- Authorization recorded:
- Active plan created:
- Probe classes:
- Probes sent:
- Issues/signals:
- Stop conditions or exclusions:

## Recommended Fix Order

1. Critical/high exploitable issues
2. Access control and auth correctness
3. Secret/token handling
4. XSS/injection and input validation
5. Headers, dependency, and hardening work

## Appendix

- Commands run:
- Files inspected:
- Assumptions:
- Workspace manifest:
- Evidence files:
