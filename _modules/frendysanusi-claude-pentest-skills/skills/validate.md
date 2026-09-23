# Validation Methodology — 6-Gate Quality Gate

Every finding must pass all 6 gates to achieve VALIDATED status. This process kills false positives and ensures report quality.

## Gate Definitions

### Gate 1: Reproducible PoC

**Question:** Is there a complete, executable proof of concept?

**PASS requires:**
- Full HTTP request: method, URL, headers, body — with auth headers and tokens redacted per CLAUDE.md Safety Rule 7 (redaction is *not* a fail condition; unredacted live credentials are)
- Specific payload used (not "I injected a payload")
- Clear steps anyone can follow

**FAIL examples:**
- "I believe this endpoint is vulnerable to SQLi"
- "The parameter appears to be injectable"
- Finding described in words with no concrete request

**Action on FAIL:** REJECT — send back to hunter with: "Provide the exact HTTP request that demonstrates this vulnerability"

---

### Gate 2: HTTP Evidence

**Question:** Is there captured HTTP evidence showing the vulnerability?

**PASS requires:**
- The HTTP request that triggers the vulnerability (credentials redacted per CLAUDE.md Safety Rule 7)
- The HTTP response that demonstrates it — status code, headers, body excerpt (with `Set-Cookie`, issued tokens, and any reflected secrets redacted)
- Clear indication of what in the response proves the vulnerability

**FAIL examples:**
- Request exists but no response was captured
- Response shown but doesn't clearly demonstrate the vulnerability
- Screenshot instead of actual HTTP data
- Request or response pasted with live `Authorization`, `Cookie`, `Set-Cookie`, Bearer / JWT, or API-key values (send back as NEEDS-WORK — "Redact credentials before resubmitting")

**Action on FAIL:** REJECT or NEEDS-WORK — "Capture the full HTTP response. Show specifically which part of the response demonstrates the vulnerability."

---

### Gate 3: Impact Verified

**Question:** Is the impact concrete and demonstrable, not theoretical?

**PASS requires:**
- Specific impact statement: "Can read any user's email address via IDOR on /api/users/{id}"
- Demonstrated, not hypothetical: "Extracted the admin user's password hash" (not "could potentially extract data")
- Appropriate severity for the actual demonstrated impact

**FAIL examples:**
- "This may lead to data exposure"
- "An attacker could potentially gain access"
- "This could be chained with other vulnerabilities" (without the chain demonstrated)

**Action on FAIL:** REJECT or downgrade severity — "Demonstrate the actual impact. What specific data can be accessed or what specific action can be performed?"

---

### Gate 4: In-Scope

**Question:** Is the vulnerable endpoint within the authorized scope?

**PASS requires:**
- URL/domain is listed in `engagements/<target>/scope.md` under "In-Scope"
- URL/domain is NOT listed under "Out-of-Scope"

**FAIL examples:**
- Endpoint is on a different domain not listed in scope
- Endpoint is on an excluded path
- Third-party service (CDN, analytics, SSO provider) not explicitly in scope

**Action on FAIL:** REJECT unconditionally. No exceptions, no "but it's related" arguments.

---

### Gate 5: Real Vulnerability

**Question:** Is this an actual exploitable security issue?

**PASS requires:**
- A real attack scenario exists
- The vulnerability can be exploited by a realistic attacker
- The issue goes beyond informational/best-practice

**FAIL examples — NOT vulnerabilities:**
- Missing security headers without a demonstrated exploit path
- Server version disclosure without a known exploitable CVE
- Self-XSS (requires victim to attack themselves)
- Logout CSRF (minimal security impact)
- Clickjacking on pages with no sensitive actions
- GraphQL introspection enabled without an auth bypass
- Rate limiting "weakness" without demonstrated abuse

**Action on FAIL:** REJECT — "This is an informational observation, not an exploitable vulnerability. To qualify, demonstrate a realistic attack scenario."

---

### Gate 6: Client Reproducible

**Question:** Can someone else reproduce this finding by following the documented steps?

**PASS requires:**
- Steps are complete and self-contained
- Any required authentication is documented (how to log in, what credentials)
- Standard tools only (browser, curl, Burp) — no custom tooling without documentation
- Consistent reproduction (works reliably, not "sometimes")

**FAIL examples:**
- Race condition that succeeds <5% of the time with no documentation of timing
- Requires authenticated session but no login instructions provided
- Requires specific browser version or extension
- Works only from a specific IP or network

**Action on FAIL:** NEEDS-WORK — "Improve the reproduction steps: [specific instructions for what's missing]"

---

## Validation Process

For each UNVALIDATED finding:

1. Read the finding entry in `findings.md`
2. Read related entries in `payload-log.md` for context
3. Check `scope.md` for Gate 4
4. Run all 6 gates sequentially — **do not skip gates even if early gates pass**
5. Record the result:

```markdown
### Validation: F-<id> — <title>

| Gate | Result | Reasoning |
|------|--------|-----------|
| 1. Reproducible PoC | PASS/FAIL | <reasoning> |
| 2. HTTP Evidence | PASS/FAIL | <reasoning> |
| 3. Impact Verified | PASS/FAIL | <reasoning> |
| 4. In-Scope | PASS/FAIL | <reasoning> |
| 5. Real Vulnerability | PASS/FAIL | <reasoning> |
| 6. Client Reproducible | PASS/FAIL | <reasoning> |

**Verdict:** VALIDATED / REJECTED / NEEDS-WORK
**Rationale:** <summary>
```

6. Update the finding status in `findings.md`
7. Add validation notes to `notes.md`

## Status Definitions

- **VALIDATED**: All 6 gates PASS. Finding is confirmed and report-ready.
- **REJECTED**: One or more gates FAIL with no reasonable path to fixing. Finding is a false positive or not a real vulnerability.
- **NEEDS-WORK**: One or more gates FAIL but could pass with additional evidence or testing. Specific instructions provided for what to fix.
