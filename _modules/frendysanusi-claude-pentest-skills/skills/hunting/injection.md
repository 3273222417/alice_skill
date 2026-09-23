# Hunting Skill: Injection Vulnerabilities

Covers: SQL Injection, NoSQL Injection, Command Injection, Server-Side Template Injection (SSTI), XML External Entity (XXE)

## Sub-Class Resolution

| Sub-Class | Payload File | Tool Delegation |
|-----------|-------------|-----------------|
| `sqli` | `payloads/sqli.md` | sqlmap (after manual confirmation) |
| `nosqli` | `payloads/nosqli.md` | — |
| `cmdi` | `payloads/cmdi.md` | commix (after manual confirmation) |
| `ssti` | `payloads/ssti.md` | — |
| `xxe` | `payloads/xxe.md` | — |

## Methodology

### Step 1: Identify Injection Points

From `tech-stack.md` and `coverage.md`, prioritize endpoints with:
- **URL parameters** used in database queries (search, filter, sort, ID lookups)
- **POST body parameters** (login forms, registration, comment submission)
- **JSON API endpoints** (especially those with MongoDB backends for NoSQLi)
- **XML-accepting endpoints** (SOAP, file upload, API endpoints with `Content-Type: application/xml`)
- **Parameters reflected in error messages** (potential SSTI)
- **Parameters passed to system commands** (file operations, PDF generation, email sending)

### Step 2: Determine Sub-Class Priority

Based on tech stack:
- **PHP/MySQL**: SQLi, CMDi, SSTI (Twig/Smarty)
- **Node.js/MongoDB**: NoSQLi, SSTI (EJS/Pug), CMDi
- **Java/Spring**: SQLi, SSTI (Freemarker/Thymeleaf), XXE
- **Python/Flask**: SQLi, SSTI (Jinja2), CMDi
- **Any XML processing**: XXE first

### Step 3: Test Each Sub-Class

For each endpoint × sub-class combination:

1. **Load the payload file** for the sub-class
2. **Send detection payloads** (5-8 from the payload file)
3. **Log each payload** to `payload-log.md` BEFORE analyzing the response
4. **Analyze responses** for:
   - SQL errors (syntax errors, ODBC errors, MySQL/PG error messages)
   - Time delays (for blind injection — must be >5 seconds to rule out network latency)
   - Different response lengths/content (boolean-based blind)
   - Template engine output (e.g., `49` from `{{7*7}}`)
   - XML parsing errors or file content in response
   - Command output in response or OOB callbacks
5. **If detection positive**: Proceed to exploitation payloads to demonstrate impact
6. **If detection blocked**: Try bypass payloads from the payload file
7. **If confirmed**: Record as UNVALIDATED finding in `findings.md` with full evidence

### Step 4: Tool Delegation

**SQLMap** — use ONLY after manual detection confirms SQLi:
```bash
sqlmap -u "<url-with-parameter>" --batch --level=3 --risk=2
```

**Commix** — use ONLY after manual detection confirms CMDi:
```bash
commix --url="<url>" --data="<post-data>" --batch
```

### Step 5: Update Coverage

After testing each endpoint for each sub-class:
- Update `coverage.md` with the endpoint and vuln classes tested
- Mark relevant WSTG categories:
  - WSTG-INPV-05 (SQL Injection)
  - WSTG-INPV-12 (Command Injection)
  - WSTG-INPV-18 (Server-Side Template Injection)
  - WSTG-INPV-07 (XML Injection / XXE)

## Finding Template

```markdown
### F-<id>: <Sub-Class> in <endpoint>

**Severity:** Critical/High
**CVSS 3.1:** <vector>
**WSTG ID:** WSTG-INPV-<XX>
**Endpoint:** <method> <url>
**Status:** UNVALIDATED

**Request:**
<full HTTP request — redact `Authorization`, `Cookie`, Bearer / JWT / API-key values per CLAUDE.md Safety Rule 7>

**Response (relevant excerpt):**
<response showing the vulnerability — redact `Set-Cookie`, issued tokens, and any reflected credentials or secrets>

**Impact:**
<concrete impact statement>
```
