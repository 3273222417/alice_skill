# /validate [finding-id]

Run the 6-gate strict quality gate on unvalidated findings.

## Usage

```
/validate              Validate all UNVALIDATED findings
/validate F-001        Validate a specific finding
```

## Preconditions

1. **Active engagement exists** with `findings.md` containing at least one UNVALIDATED finding.
2. If no UNVALIDATED findings exist: "No unvalidated findings. Run `/hunt <vuln-class>` to discover vulnerabilities."

## Procedure

### Step 1: Load Agent and Skill

1. Load `agents/validator-agent.md` — Adopt the Validator Agent persona
2. Load `skills/validate.md` — Validation methodology

### Step 2: Load State

Read engagement state:
- `engagements/<target>/findings.md` — Get unvalidated findings
- `engagements/<target>/scope.md` — For Gate 4 (in-scope check)
- `engagements/<target>/payload-log.md` — For context on payload attempts
- `engagements/<target>/notes.md` — For prior observations

### Step 3: Select Findings

- If `finding-id` specified: Validate only that finding
- If no argument: Validate all findings with status UNVALIDATED

### Step 4: Run Validation

For each selected finding, execute all 6 gates from `skills/validate.md`:

1. Gate 1: Reproducible PoC
2. Gate 2: HTTP Evidence
3. Gate 3: Impact Verified
4. Gate 4: In-Scope
5. Gate 5: Real Vulnerability
6. Gate 6: Client Reproducible

### Step 5: Update State

For each finding validated:
- Update status in `findings.md`: VALIDATED, REJECTED, or NEEDS-WORK
- Add validation rationale to `notes.md`

### Step 6: Summary

```markdown
## Validation Results

| Finding | Title | Previous | New Status | Failed Gates |
|---------|-------|----------|-----------|-------------|
| F-001 | SQLi in /api/search | UNVALIDATED | VALIDATED | — |
| F-002 | XSS in /profile | UNVALIDATED | REJECTED | Gate 5: Self-XSS |
| F-003 | IDOR in /api/users | UNVALIDATED | NEEDS-WORK | Gate 6: Missing auth steps |

**Validated:** <count>
**Rejected:** <count>
**Needs Work:** <count>

<If VALIDATED findings exist:>
Run /report --full to generate the engagement report.

<If NEEDS-WORK findings exist:>
Address the feedback above, then run /validate again.
```
