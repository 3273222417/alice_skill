---
name: web-report
description: >
  Web penetration testing report generation skill. Activate when the user wants to write, generate,
  or finalize a report for a web pentest or bug bounty engagement. Consolidates outputs from
  web-recon, web-exploitation, and web-postexploitation skills into a structured technical and
  executive report. Produces findings in standardized format (name, criticality, CVSS, description,
  impact, recommendation, evidence). Default mode: combined technical + executive report.
  Publishes to Notion via MCP when available.
domain: web-application-security
tags: [report, pentest-report, web-pentest, bug-bounty, cvss, executive-report, technical-report, notion]
x-alice-class: pentest
---# Web Report — Technical & Executive Report Generation

## Architecture

This skill is Claude-driven. It reads output directories from prior skills, organizes all confirmed
findings, writes the full report in the correct format, reviews it twice, and publishes to Notion.

```
Input directories (any combination):
  $RECON_OUT    — web-recon output (nuclei findings, live hosts, JS secrets, CMS results)
  $EXPLOIT_OUT  — web-exploitation output (sqli/, xss/, lfi/, ssrf/, auth/, findings/)
  $POSTEX_OUT   — web-postexploitation output (if applicable)
  $EVIDENCE_DIR — screenshots directory (gowitness/, manual captures)
```

---

## Initial Setup

```bash
TARGET="https://target.com"
DOMAIN="target.com"
CLIENT="Client Company Name"
ENGAGEMENT="Web Application Penetration Test"
TESTER="[Your Name / Company]"
DATE="$(date +%Y-%m-%d)"

RECON_OUT="$(pwd)/target"
EXPLOIT_OUT="$(pwd)/target-exploit"
POSTEX_OUT="$(pwd)/target-postex"       # leave empty if not applicable
EVIDENCE_DIR="$(pwd)/target/evidence"

# Report mode — default: combined (recommended)
REPORT_MODE="combined"  # options: combined | technical | executive
```

Create progress tasks with TaskCreate:
```
"PHASE 1 — Finding Triage & Consolidation"
"PHASE 2 — Evidence Collection & Organization"
"PHASE 3 — Report Writing"
"PHASE 4 — Review #1 (completeness and technical accuracy)"
"PHASE 5 — Review #2 (clarity, language, formatting)"
"PHASE 6 — Notion Publication"
```

---

## Report Modes

| Mode | Target audience | What it includes |
|------|----------------|-----------------|
| `combined` (default) | Mixed — technical and management | Full technical detail + executive sections with plain-language explanations. Recommended when audience is unknown. |
| `technical` | Security team, developers | Full technical detail, commands, payloads, reproduction steps |
| `executive` | C-level, managers, non-technical | Summary, business impact, risk ratings, no raw payloads or commands |

**When mode is not specified: always use `combined`.**

---

## PHASE 1 — Finding Triage & Consolidation

Read all confirmed findings from prior skill outputs:

```bash
# web-recon findings
cat "$RECON_OUT/vulns/nuclei.txt" 2>/dev/null          # nuclei confirmed findings
cat "$RECON_OUT/js/secrets.json" 2>/dev/null           # JS secrets
cat "$RECON_OUT/vulns/cms_*.txt" 2>/dev/null           # CMS vulnerabilities

# web-exploitation findings
cat "$EXPLOIT_OUT/findings/sqli_confirmed.txt" 2>/dev/null
cat "$EXPLOIT_OUT/findings/xss_confirmed.txt" 2>/dev/null
cat "$EXPLOIT_OUT/findings/lfi_confirmed.txt" 2>/dev/null
cat "$EXPLOIT_OUT/findings/ssrf_confirmed.txt" 2>/dev/null
cat "$EXPLOIT_OUT/findings/open_redirect.txt" 2>/dev/null
cat "$EXPLOIT_OUT/findings/jwt_endpoints.txt" 2>/dev/null
cat "$EXPLOIT_OUT/findings/cookie_issues.txt" 2>/dev/null
cat "$EXPLOIT_OUT/findings/clickjacking.txt" 2>/dev/null

# List all screenshots
ls "$EVIDENCE_DIR/" 2>/dev/null
ls "$RECON_OUT/screenshots/" 2>/dev/null
```

Build a consolidated finding list, grouped by severity:
```
CRITICAL  — RCE, SQLi with data extraction, SSRF→cloud metadata, Authentication bypass (full account takeover)
HIGH      — SQLi (no output), Stored XSS, SSTI, XXE, LFI with sensitive file read, JWT algorithm confusion, File upload
MEDIUM    — Reflected XSS, IDOR, CSRF on sensitive action, Open redirect, Broken auth (partial), Insecure deserialization
LOW       — Clickjacking, Missing security headers, Information disclosure, DOM XSS (limited impact)
INFO      — Best practice recommendations, exposed JS source maps, verbose error messages
```

---

## PHASE 2 — Evidence Organization

### Screenshot cataloging

```bash
# List and describe all evidence
ls -lt "$EVIDENCE_DIR/" 2>/dev/null
ls -lt "$RECON_OUT/screenshots/" 2>/dev/null   # gowitness screenshots

# For each finding, identify its evidence file(s)
# Naming convention: <severity>_<finding_type>_<description>.<ext>
# Example:
#   critical_sqli_login_page_error.png
#   high_xss_stored_comment_field.png
#   high_lfi_etc_passwd.png
```

For each screenshot/evidence file, write a 1-2 sentence explanation:
- **What** is visible in the screenshot
- **Why** it demonstrates the vulnerability (what makes it a confirmed finding vs. a hypothesis)

### Submitting screenshots to Notion

When Notion MCP is available:
```
1. Create finding page: mcp__Notion__notion-create-pages
2. For each screenshot: describe it in the evidence block (Notion does not support direct image upload via API — note the local file path and describe it clearly)
3. If images need to be hosted: upload to an image hosting service and embed the URL
```

---

## PHASE 3 — Report Writing

### Document structure

```
COVER PAGE
  - Client name
  - Engagement type
  - Date
  - Tester name / company

EXECUTIVE SUMMARY  (always present, even in technical mode)
  - Overview of tested scope
  - Total vulnerabilities by severity (table)
  - Overall risk score
  - 3-5 key findings in plain language
  - General priority recommendation

METHODOLOGY (technical / combined)
  - Tools used
  - Phases executed
  - Scope limitations and notes

VULNERABILITY SUMMARY (table)
  | # | Name | Criticality | CVSS | Endpoint | Status |
  |---|------|-------------|------|----------|--------|

DETAILED FINDINGS (one section per finding)

CONCLUSION

APPENDIX — Tools and References
```

---

## Finding Template — Required Format

**Apply this template for every confirmed finding. Write each field as a full paragraph.**

```
### [CRITICALITY] — [Vulnerability Name]

**Criticality:** Critical / High / Medium / Low / Informational
**CVSS Score:** X.X (Critical/High/Medium/Low)
**CVSS Vector:** CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
**Affected endpoint:** https://target.com/endpoint?param=value
**Method:** GET / POST / PUT
**Vulnerable parameter:** param_name

---

**Description**

[1 robust paragraph — minimum 4-6 sentences. Explain WHAT the vulnerability is, HOW it works
technically, WHY this endpoint is vulnerable, and what code/configuration characteristic makes
it exploitable. In combined/executive mode: open with a plain-language analogy before the
technical detail.]

---

**Impact / Observation**

[1 robust paragraph — minimum 4-6 sentences. Explain WHAT an attacker CAN do by exploiting this
vulnerability, what data or systems are at risk, what the business impact is (not just technical),
and how likely real exploitation is. Note if the vulnerability is exploitable remotely, without
authentication, or chainable with others.]

---

**Recommendation / Remediation**

[1 robust paragraph — minimum 4-6 sentences. Explain WHAT must be done to fix it, with enough
technical specificity for a developer to implement. Include primary fix + defense in depth
(multiple control layers). Mention recommended fix timeline based on criticality.]

---

**Evidence**

[For each screenshot or PoC:]

*Figure X — [descriptive title]*
`File: evidence/critical_sqli_login.png`

> [2-4 sentences explaining WHAT is happening in the image: what was sent, what the server
> returned, what this proves. Language clear enough for a non-technical person to understand
> that a real problem occurred.]

[If PoC in code:]
\`\`\`http
GET /endpoint?id=1' OR 1=1-- HTTP/1.1
Host: target.com
...
\`\`\`
*The above demonstrates [what was done]. The server response confirms [what was observed].*
```

---

## CVSS Reference Table (web findings)

Use these as baseline — adjust based on actual exploitability and scope:

| Vulnerability | CVSS Base | Criticality | Vector |
|----------------|-----------|-------------|--------|
| RCE (unauthenticated) | 9.8 | Critical | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |
| SQLi (data extraction) | 9.8 | Critical | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |
| SSRF → cloud metadata | 9.1 | Critical | AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:L/A:N |
| Auth bypass (full ATO) | 9.8 | Critical | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |
| SSTI → RCE | 9.8 | Critical | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |
| File upload → RCE | 9.8 | Critical | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |
| XXE (file read) | 7.5 | High | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N |
| LFI (sensitive files) | 7.5 | High | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N |
| JWT algorithm confusion | 9.1 | Critical | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N |
| JWT weak secret | 8.8 | High | AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N |
| Stored XSS | 8.8 | High | AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:H/A:N |
| IDOR (sensitive data) | 8.1 | High | AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N |
| Insecure deserialization | 8.8 | High | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |
| Broken auth (partial) | 7.5 | High | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N |
| SQLi (blind, no output) | 8.6 | High | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N |
| SSRF (internal network) | 8.6 | High | AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N |
| Reflected XSS | 6.1 | Medium | AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N |
| CSRF (sensitive action) | 6.5 | Medium | AV:N/AC:L/PR:N/UI:R/S:U/C:N/I:H/A:N |
| Open redirect | 6.1 | Medium | AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N |
| CRLF injection | 6.1 | Medium | AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N |
| Host header injection | 7.2 | High | AV:N/AC:L/PR:N/UI:N/S:C/C:L/I:L/A:N |
| Clickjacking | 4.7 | Medium | AV:N/AC:L/PR:N/UI:R/S:C/C:N/I:L/A:N |
| Missing security headers | 3.1 | Low | AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N |
| Information disclosure | 5.3 | Medium | AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N |
| Exposed JS source map | 5.3 | Medium | AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N |
| Exposed .git repository | 7.5 | High | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N |

> **Adjust CVSS based on context**: if authentication is required (PR:L or PR:H), if the scope changes (S:C vs S:U), or if chaining is needed (AC:H).

---

## PHASE 4 & 5 — Double Review

**Review #1 — Technical accuracy:**
- Every finding has: name, criticality, CVSS score + vector, affected endpoint, description, impact, recommendation, evidence
- CVSS scores are consistent with the actual exploitability demonstrated
- Evidence correctly described — screenshots match their finding
- Reproduction steps are accurate and testable
- No finding is listed without confirmed exploitation evidence

**Review #2 — Language, clarity, and formatting:**
- All text is clear and consistent in language and style
- Executive sections use no jargon without explanation
- No spelling or grammatical errors
- Paragraphs are 4-6 sentences minimum and substantive
- Table of findings is complete and sorted by CVSS (highest first)
- All evidence files are correctly referenced (file paths or Notion links)

**After both reviews:** explicitly confirm: *"Report reviewed twice. No pending items identified."*

---

## PHASE 6 — Notion Publication

When `mcp__Notion__*` is available:

```
1. Create parent page: mcp__Notion__notion-create-pages
   Title: "Pentest Report — [CLIENT] — [DATE]"
   Content: Executive Summary + Finding Summary Table

2. For each finding (Critical/High/Medium):
   Create subpage: mcp__Notion__notion-create-pages (child of parent)
   Title: "[CVSS] [CRITICALITY] — [Vulnerability Name]"
   Content: Full finding in template format

3. Create appendix page with:
   - Tools used
   - Scope and methodology
   - Raw output references (file paths)
```

---

## Executive Summary Template

```
## Executive Summary

This report presents the results of the penetration test conducted against [TARGET] from
[START_DATE] to [END_DATE], performed by [TESTER]. The objective of the engagement was to
identify security vulnerabilities in the web application and assess the potential impact of
their exploitation.

**Assessed scope:** [list of in-scope URLs/endpoints]

**Overall result:** X vulnerabilities were identified: Y critical, Z high, W medium, and V low
severity. [1-2 sentences summarizing the most severe finding and its business impact.]

**Severity distribution:**
| Severity      | Count |
|---------------|-------|
| Critical      | X     |
| High          | X     |
| Medium        | X     |
| Low           | X     |
| Informational | X     |

**Key findings:**
1. [Name] — [1 business-impact sentence]
2. [Name] — [1 business-impact sentence]
3. [Name] — [1 business-impact sentence]

**Priority recommendation:** [1-2 sentences on what to fix first and why, in language accessible
to management.]
```

---

## MCP Integration

### Notion (`mcp__Notion__*`)
- `notion-create-pages` — create main page and subpages per finding
- `notion-update-page` — update pages with additional evidence after review
- `notion-create-comment` — add review observations

---

## Operational Notes

- **Completeness before publishing**: never publish the report without both reviews completed
- **Evidence required**: every Critical/High finding must have at least 1 screenshot or documented PoC
- **CVSS adjusted to context**: the base score is a reference — adjust PR, AC and S based on the actual case
- **Combined language**: in `combined` mode, each finding opens with 1 business-language sentence before technical details
- **Confidentiality**: the report is a confidential document delivered to the client — credentials, hashes and sensitive data obtained during the test are included as proof of exploitation; the client is responsible for secure handling of the document
