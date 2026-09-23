# Report Generation Methodology

## Report Modes

### Per-Finding Mode (`/report --finding <id>`)
Generates a single finding write-up, useful during testing.

### Full Report Mode (`/report --full`)
Generates a complete penetration test report with all VALIDATED findings.

---

## Per-Finding Template

```markdown
## [Finding ID] — [Title]

| | |
|---|---|
| **Severity** | Critical / High / Medium / Low / Informational |
| **CVSS 3.1** | [Vector String] ([Score]) |
| **CWE** | CWE-[ID] — [Name] |
| **WSTG** | [WSTG-ID] |
| **Affected Endpoint** | [Method] [URL] |
| **Status** | Validated |
| **Date Found** | [YYYY-MM-DD] |

### Description

[2-3 sentences explaining the vulnerability in plain language. What is the vulnerability, where does it exist, and what causes it.]

### Proof of Concept

**Request:**
```http
GET /api/users/42 HTTP/1.1
Host: target.example
Authorization: Bearer [REDACTED-JWT len=412]
Cookie: session=[REDACTED]
[... other headers / body ...]
```

**Response (relevant excerpt):**
```http
HTTP/1.1 200 OK
Set-Cookie: session=[REDACTED]
[... portion of the body that demonstrates the vulnerability; redact any reflected secrets ...]
```

> **Redaction requirement (CLAUDE.md Safety Rule 7):** Before including HTTP evidence in a delivered report, replace the values of `Authorization`, `Cookie`, `Set-Cookie`, `Proxy-Authorization`, `X-API-Key`, `X-Auth-Token`, `X-CSRF-Token`, and any Bearer / JWT / session-token or API-key field with `[REDACTED]`. Preserve the header/field name and token *shape* (prefix, length) where useful so the reviewer can tell what was there. Apply the same rule to any secret reflected in the response body. The PoC must still prove the vulnerability — just without live credentials on the page.

**Steps to Reproduce:**
1. [Step-by-step instructions that a third party can follow]
2. [Include authentication steps if needed — describe how to obtain a valid credential, do not embed one]
3. [Include any specific tools or configuration required]

### Impact

[Concrete impact statement. What can an attacker achieve? Be specific — "can read any user's personal data including email, phone, and address" not "may lead to data exposure".]

### Remediation

[Specific technical fix. Include code examples where possible.]

**References:**
- [OWASP reference URL]
- [CWE reference URL]
- [Any relevant framework documentation]
```

---

## Full Report Template

```markdown
# Penetration Test Report — [Target Name]

| | |
|---|---|
| **Prepared for** | [Client / Target Owner] |
| **Prepared by** | [Tester Name] |
| **Date** | [YYYY-MM-DD] |
| **Engagement Period** | [Start Date] — [End Date] |

---

## Executive Summary

[1 paragraph, business-language summary. State: what was tested, the overall security posture (strong/moderate/weak), the number and severity of findings, and the most critical risk. Written for a non-technical audience.]

| Severity | Count |
|----------|-------|
| Critical | [Count] |
| High | [Count] |
| Medium | [Count] |
| Low | [Count] |

**Overall Risk Level:** Critical / High / Medium / Low

---

## Scope

| | |
|---|---|
| **Target** | [URL/domain] |
| **In-Scope** | [List of authorized targets] |
| **Out-of-Scope** | [List of exclusions] |
| **Constraints** | [Rate limits, restricted hours, etc.] |

---

## Methodology

Testing was conducted following the **OWASP Web Security Testing Guide (WSTG) v4.2** methodology, covering the following categories:

| WSTG Category | Tested | Notes |
|---------------|--------|-------|
| Information Gathering (WSTG-INFO) | Yes/Partial/No | |
| Configuration & Deployment (WSTG-CONF) | Yes/Partial/No | |
| Identity Management (WSTG-IDNT) | Yes/Partial/No | |
| Authentication (WSTG-ATHN) | Yes/Partial/No | |
| Authorization (WSTG-ATHZ) | Yes/Partial/No | |
| Session Management (WSTG-SESS) | Yes/Partial/No | |
| Input Validation (WSTG-INPV) | Yes/Partial/No | |
| Error Handling (WSTG-ERRH) | Yes/Partial/No | |
| Cryptography (WSTG-CRYP) | Yes/Partial/No | |
| Business Logic (WSTG-BUSL) | Yes/Partial/No | |
| Client-Side (WSTG-CLNT) | Yes/Partial/No | |

**Tools Used:**
- Burp Suite (web proxy and scanner)
- curl (manual HTTP requests)
- sqlmap (SQL injection testing)
- commix (command injection testing)
- Custom scripts (as documented per finding)

---

## Findings Summary

| ID | Title | Severity | CVSS 3.1 |
|----|-------|----------|----------|
[Table of all VALIDATED findings, sorted by severity (Critical → Low)]

---

## Detailed Findings

[Per-finding template for each VALIDATED finding, in severity order]

---

## Remediation Priority Matrix

| Priority | Finding | Effort | Impact |
|----------|---------|--------|--------|
| 1 (Immediate) | [Critical findings] | [Est. effort] | [Business impact] |
| 2 (Short-term) | [High findings] | [Est. effort] | [Business impact] |
| 3 (Medium-term) | [Medium findings] | [Est. effort] | [Business impact] |
| 4 (Long-term) | [Low findings] | [Est. effort] | [Business impact] |

---

## Appendix: Test Coverage

[Populated from coverage.md — which endpoints were tested for which vulnerability classes]
```

---

## CVSS 3.1 Scoring Guide

Common web vulnerability CVSS scores for reference:

| Vulnerability | Typical CVSS | Vector |
|--------------|-------------|--------|
| RCE (unauthenticated) | 9.8 Critical | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |
| SQLi (data extraction) | 8.6-9.8 Critical | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:L |
| SSTI (RCE) | 9.8 Critical | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |
| Stored XSS | 6.1-8.0 Medium-High | AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N |
| IDOR (data access) | 6.5-7.5 Medium-High | AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N |
| SSRF (internal access) | 6.5-9.1 Medium-Critical | AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N |
| Reflected XSS | 6.1 Medium | AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N |
| CSRF (state change) | 4.3-6.5 Medium | AV:N/AC:L/PR:N/UI:R/S:U/C:N/I:L/A:N |
| Open Redirect | 3.4-4.7 Low | AV:N/AC:L/PR:N/UI:R/S:U/C:N/I:L/A:N |
| Missing header (no exploit) | Informational | N/A |

## Writing Guidelines

- **Use definitive language** for validated findings: "is vulnerable", not "may be vulnerable"
- **Include CWE identifiers** for each finding
- **Reference WSTG test case IDs** where applicable
- **Keep descriptions accessible** — technical enough for developers, clear enough for managers
- **Impact statements must be concrete** — quantify where possible (number of affected users, type of exposed data)
- **Remediation must be actionable** — specific code changes, configuration updates, or library upgrades
