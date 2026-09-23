# /hunt <vuln-class>

Test for a specific vulnerability class against target endpoints using curated payloads.

## Usage

```
/hunt injection
/hunt sqli
/hunt xss
/hunt auth-access
/hunt server-side
/hunt client-side
/hunt session
/hunt business-logic
/hunt config
```

## Valid Arguments

### Vuln-Class Groups
| Group | Skill File | Includes |
|-------|-----------|----------|
| `injection` | `skills/hunting/injection.md` | SQLi, NoSQLi, CMDi, SSTI, XXE |
| `auth-access` | `skills/hunting/auth-access.md` | IDOR, JWT, OAuth, auth bypass, priv esc |
| `server-side` | `skills/hunting/server-side.md` | SSRF, path traversal, file upload, deserialization, smuggling |
| `client-side` | `skills/hunting/client-side.md` | XSS, CSRF, open redirect |
| `session` | `skills/hunting/session.md` | Session fixation, cookie security, token weakness |
| `business-logic` | `skills/hunting/business-logic.md` | Race conditions, workflow bypass, logic flaws |
| `config` | `skills/hunting/config.md` | Headers, CORS, TLS, info disclosure, default creds |
| `ai-llm` | `skills/hunting/ai-llm.md` | Prompt injection, LLM tool abuse, system prompt leakage |

### Specific Sub-Classes
`sqli`, `xss`, `ssrf`, `ssti`, `xxe`, `cmdi`, `path-traversal`, `idor`, `jwt`, `oauth`, `nosqli`, `deserialization`, `file-upload`, `open-redirect`, `csrf`, `request-smuggling`, `race-condition`, `prompt-injection`

Sub-classes resolve to their parent group's skill + the specific payload file.

## Preconditions

1. **Scope must exist.** Check `engagements/<target>/scope.md`. If not found → stop, require `/scope`.
2. **Recon recommended.** If `tech-stack.md` is empty, warn: "Recon not yet performed. Run `/recon <target>` first for better targeting. Proceed anyway? (y/n)"

## Procedure

### Step 1: Resolve Vuln-Class

Map the argument to skill and payload files:

| Input | Skill File | Payload File(s) |
|-------|-----------|-----------------|
| `injection` | `skills/hunting/injection.md` | `payloads/sqli.md`, `nosqli.md`, `cmdi.md`, `ssti.md`, `xxe.md` |
| `sqli` | `skills/hunting/injection.md` | `payloads/sqli.md` |
| `xss` | `skills/hunting/client-side.md` | `payloads/xss.md` |
| `ssrf` | `skills/hunting/server-side.md` | `payloads/ssrf.md` |
| `idor` | `skills/hunting/auth-access.md` | `payloads/idor.md` |
| `jwt` | `skills/hunting/auth-access.md` | `payloads/jwt.md` |
| `prompt-injection` | `skills/hunting/ai-llm.md` | `payloads/prompt-injection.md` |
| ... | (follows same pattern) | ... |

### Step 2: Load Files

1. Load `agents/hunter-agent.md` — Adopt the Hunter Agent persona
2. Load the resolved skill file
3. Load the resolved payload file(s)
4. Read engagement state: `scope.md`, `tech-stack.md`, `coverage.md`, `payload-log.md`

### Step 3: Execute Hunt

Follow the methodology in the skill file:
1. Identify relevant endpoints from recon data
2. Select and prioritize payloads
3. **Log each payload to `payload-log.md` BEFORE analyzing the response**
4. Send payloads and analyze responses
5. Record potential findings as UNVALIDATED in `findings.md`
6. Update `coverage.md`

### Step 4: Summary

```
Hunt complete: <vuln-class>
  Endpoints tested: <count>
  Payloads sent: <count>
  Potential findings: <count> (UNVALIDATED)
  Blocked by WAF: <count>

  <If findings:>
  Run /validate to quality-check findings.
  
  <If no findings:>
  No vulnerabilities detected for this class.
  Suggested: /hunt <next-untested-class>
```

## Error Handling

- **Invalid vuln-class**: List valid options and ask user to choose
- **No endpoints in recon data**: Suggest running `/recon` first
- **All endpoints already tested for this class**: Show coverage and suggest a different class
