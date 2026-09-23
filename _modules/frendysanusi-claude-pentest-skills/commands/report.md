# /report [--full | --finding <id>]

Generate a markdown penetration test report.

## Usage

```
/report --finding F-001      Generate report for a single finding
/report --full               Generate complete engagement report
/report                      (no args) Same as --full
```

## Preconditions

### For `--finding <id>`
- The specified finding must exist in `findings.md`
- The finding must have status VALIDATED
- If UNVALIDATED: "Finding F-<id> has not been validated. Run `/validate F-<id>` first."
- If REJECTED: "Finding F-<id> was rejected during validation. Cannot generate report for rejected findings."

### For `--full`
- At least one VALIDATED finding must exist
- If no VALIDATED findings: "No validated findings available. Run `/validate` to check your findings."

## Procedure

### Step 1: Load Skill

Load `skills/report.md` — Report templates and writing guidelines.

No agent persona is activated for reporting — use neutral, professional tone.

### Step 2: Load State

Read all engagement state files:
- `engagements/<target>/scope.md` — Scope details for report header
- `engagements/<target>/findings.md` — All findings (filter to VALIDATED only for report)
- `engagements/<target>/coverage.md` — Test coverage for methodology section
- `engagements/<target>/tech-stack.md` — Identified technologies
- `engagements/<target>/payload-log.md` — Payload statistics
- `engagements/<target>/notes.md` — Any additional observations

### Step 3: Generate Report

#### `--finding` Mode
1. Load the specific finding from `findings.md`
2. Generate using the Per-Finding Template from `skills/report.md`
3. Calculate CVSS 3.1 score using the scoring guide
4. Include CWE and WSTG references
5. Output the finding report in markdown

#### `--full` Mode
1. Collect all VALIDATED findings, sorted by severity (Critical → Low)
2. Generate using the Full Report Template from `skills/report.md`
3. Populate all sections:
   - Executive summary (1 paragraph, business language)
   - Scope (from scope.md)
   - Methodology (from coverage.md, mapped to WSTG categories)
   - Findings summary table
   - Detailed findings (per-finding template for each)
   - Remediation priority matrix
   - Test coverage appendix
4. Output the complete report in markdown

### Step 4: Output

Display the report in the conversation. Offer to save:
```
Report generated. Would you like me to save it to:
  engagements/<target>/report-<date>.md
```

## Report Quality Checks

Before outputting, verify:
- [ ] All CVSS scores are calculated and included
- [ ] All findings have CWE identifiers
- [ ] All findings have reproduction steps
- [ ] Executive summary is written in business language (no jargon)
- [ ] Remediation recommendations are specific and actionable
- [ ] No UNVALIDATED or REJECTED findings are included
- [ ] Methodology section accurately reflects what was tested
