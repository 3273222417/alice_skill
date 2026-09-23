# /scope <target>

Define and authorize the target scope for a penetration testing engagement. This is the **mandatory first step** — all other commands refuse to run without an active scope.

## Usage

```
/scope example.com
/scope https://app.example.com
/scope 192.168.1.100:8080
```

## Procedure

### Step 1: Parse Target

Normalize the target identifier:
- Extract the primary domain or IP
- Use as the engagement directory name (sanitize: replace `/` with `_`, remove protocol)

### Step 2: Gather Scope Details

Prompt the user for the following information. Do not proceed until all required fields are provided:

**Required:**
1. **In-scope URLs/domains** — Exact URLs, domains, or IP ranges authorized for testing
2. **Out-of-scope exclusions** — Any URLs, domains, paths, or IP ranges explicitly excluded
3. **Authorization confirmation** — User must explicitly confirm: *"I confirm I have written authorization to test these targets"*

**Optional (ask but allow skipping):**
4. **Engagement name** — Descriptive name (defaults to target domain)
5. **Rate limits** — Maximum requests per second (default: no specific limit, use common sense)
6. **Restricted hours** — Time windows when testing is not allowed
7. **Sensitive endpoints** — Paths to handle with extra care (e.g., production payment flows)
8. **Test account credentials** — Any provided test accounts (store in scope.md, never in version control)

### Step 3: Create Engagement Directory

Create `engagements/<target>/` with the following files:

#### `scope.md`
```markdown
# Scope — <target>

**Engagement:** <name>
**Target:** <target>
**Start Date:** <YYYY-MM-DD>
**Authorization:** Confirmed by user

## In-Scope
- <list of authorized URLs/domains/IPs>

## Out-of-Scope
- <list of excluded URLs/domains/paths>

## Constraints
- **Rate Limit:** <value or "None specified">
- **Restricted Hours:** <value or "None">
- **Sensitive Endpoints:** <list or "None">

## Test Accounts
- <credentials or "None provided">

## Notes
<any additional context>
```

#### `findings.md`
```markdown
# Findings — <target>

| ID | Title | Severity | CVSS | Endpoint | Vuln Class | Status | Date |
|----|-------|----------|------|----------|------------|--------|------|

---

<!-- Detailed finding entries below -->
```

#### `payload-log.md`
```markdown
# Payload Testing Log — <target>

| Timestamp | Endpoint | Vuln Class | Payload | Result | Notes |
|-----------|----------|------------|---------|--------|-------|
```

#### `coverage.md`
```markdown
# Test Coverage — <target>

## OWASP WSTG Coverage

| Category | ID Range | Tested | Date | Notes |
|----------|----------|--------|------|-------|
| Information Gathering | WSTG-INFO-01 to 10 | No | | |
| Configuration & Deploy | WSTG-CONF-01 to 11 | No | | |
| Identity Management | WSTG-IDNT-01 to 05 | No | | |
| Authentication | WSTG-ATHN-01 to 10 | No | | |
| Authorization | WSTG-ATHZ-01 to 04 | No | | |
| Session Management | WSTG-SESS-01 to 09 | No | | |
| Input Validation | WSTG-INPV-01 to 19 | No | | |
| Error Handling | WSTG-ERRH-01 to 02 | No | | |
| Cryptography | WSTG-CRYP-01 to 04 | No | | |
| Business Logic | WSTG-BUSL-01 to 09 | No | | |
| Client-Side | WSTG-CLNT-01 to 13 | No | | |

## Endpoint Coverage

| Endpoint | Vuln Classes Tested | Date | Status |
|----------|-------------------|------|--------|
```

#### `tech-stack.md`
```markdown
# Technology Stack — <target>

## Web Server
_Not yet identified_

## Application Framework
_Not yet identified_

## JavaScript Libraries
_Not yet identified_

## Database
_Not yet identified_

## CDN / WAF
_Not yet identified_

## Authentication Mechanism
_Not yet identified_

## Notable Headers
_Not yet identified_

## Additional Notes
```

#### `notes.md`
```markdown
# Engagement Notes — <target>

**Started:** <YYYY-MM-DD>

---
```

### Step 4: Confirm

Display a summary table of the scope and confirm readiness:

```
Scope defined for <target>
  In-scope:     <count> targets
  Out-of-scope: <count> exclusions
  Constraints:  <summary>

Engagement directory: engagements/<target>/
Ready to proceed with /recon <target>
```

## Scope Verification

Other commands call this check before executing:

1. Read `engagements/<target>/scope.md`
2. Verify the request URL/domain is listed under "In-Scope"
3. Verify it is NOT listed under "Out-of-Scope"
4. If ambiguous → **STOP and ask the user**
5. If out-of-scope → **REFUSE the request, explain why**
