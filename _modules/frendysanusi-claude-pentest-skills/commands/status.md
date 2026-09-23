# /status

Display the engagement progress dashboard. Read-only — does not modify any state files.

## Usage

```
/status
/status <target>
```

If `<target>` is omitted and only one engagement exists, use that. If multiple engagements exist, list them and ask which one.

## Procedure

### Step 1: Identify Active Engagement

- List directories under `engagements/`
- If none exist: display "No active engagements. Run `/scope <target>` to start."
- If one exists: use it
- If multiple exist: list them with start dates, ask user to specify

### Step 2: Read State Files

Read all state files from `engagements/<target>/`:
- `scope.md` — Scope summary
- `findings.md` — Finding count and status breakdown
- `coverage.md` — Test coverage stats
- `payload-log.md` — Payload attempt stats
- `tech-stack.md` — Identified technologies
- `notes.md` — Recent notes

### Step 3: Compute Metrics

Calculate:
- **Endpoints discovered** (from tech-stack.md and coverage.md)
- **WSTG categories tested** vs total 11 categories
- **Findings by status**: UNVALIDATED / VALIDATED / REJECTED / NEEDS-WORK
- **Findings by severity**: Critical / High / Medium / Low
- **Payload attempts**: total, success rate (POTENTIAL-FINDING / total)
- **Coverage percentage**: tested endpoint×vuln-class combinations vs total possible

### Step 4: Display Dashboard

```markdown
## Engagement Status — <target>

**Started:** <date> | **Scope:** <in-scope count> targets | <out-of-scope count> exclusions

### Reconnaissance
| Metric | Value |
|--------|-------|
| Endpoints Discovered | <count> |
| Tech Stack Identified | <Yes/Partial/No> |
| WSTG Info Gathering | <Complete/Partial/Not Started> |

### Hunt Progress
| WSTG Category | Status | Endpoints Tested |
|---------------|--------|-----------------|
| Information Gathering | <status> | <count> |
| Configuration & Deploy | <status> | <count> |
| Identity Management | <status> | <count> |
| Authentication | <status> | <count> |
| Authorization | <status> | <count> |
| Session Management | <status> | <count> |
| Input Validation | <status> | <count> |
| Error Handling | <status> | <count> |
| Cryptography | <status> | <count> |
| Business Logic | <status> | <count> |
| Client-Side | <status> | <count> |

### Findings
| Status | Count |
|--------|-------|
| UNVALIDATED | <count> |
| VALIDATED | <count> |
| REJECTED | <count> |
| NEEDS-WORK | <count> |

### Severity Breakdown (Validated Only)
| Severity | Count |
|----------|-------|
| Critical | <count> |
| High | <count> |
| Medium | <count> |
| Low | <count> |

### Payload Testing
| Metric | Value |
|--------|-------|
| Total Attempts | <count> |
| Potential Findings | <count> |
| Success Rate | <percentage> |

### Suggested Next Steps
<Based on current state, suggest what to do next:>
- If no recon done: "Run `/recon <target>` to map the attack surface"
- If recon done but no hunting: "Run `/hunt <suggested-class>` to start testing"
- If unvalidated findings exist: "Run `/validate` to quality-check your findings"
- If validated findings exist: "Run `/report --full` to generate the engagement report"
```
