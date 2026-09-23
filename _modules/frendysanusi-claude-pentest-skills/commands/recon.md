# /recon <target>

Map the attack surface of an authorized target.

## Usage

```
/recon example.com
/recon https://app.example.com
```

## Preconditions

1. **Scope must exist.** Check for `engagements/<target>/scope.md`. If not found:
   - Display: "No scope defined for `<target>`. Run `/scope <target>` first."
   - **Stop.**

2. **Verify target matches scope.** The target must be listed as in-scope.

## Procedure

### Step 1: Load Agent and Skill

1. Load `agents/recon-agent.md` — Adopt the Recon Agent persona
2. Load `skills/recon.md` — Reconnaissance methodology

### Step 2: Load Current State

Read engagement state files:
- `engagements/<target>/scope.md` — Scope boundaries and constraints
- `engagements/<target>/tech-stack.md` — Any previously identified technologies
- `engagements/<target>/coverage.md` — Any previously completed recon
- `engagements/<target>/notes.md` — Any prior observations

If recon was partially completed before, resume from where it left off (check coverage.md).

### Step 3: Execute Recon Phases

Follow `skills/recon.md` phases 1 through 5:

1. **Technology Fingerprinting** → Update `tech-stack.md`
2. **Endpoint Discovery** → Update `coverage.md` endpoint table
3. **Input Vector Mapping** → Update `coverage.md` with input vectors per endpoint
4. **Authentication Mechanism ID** → Update `tech-stack.md` auth section
5. **Infrastructure & WAF Detection** → Update `tech-stack.md` CDN/WAF section

### Step 4: Produce Recon Summary

Generate the structured recon summary as defined in `skills/recon.md`:
- Attack surface overview
- High-value targets
- Recommended hunt order

### Step 5: Update State

- Mark WSTG-INFO categories as tested in `coverage.md`
- Add any notable observations to `notes.md`
- Confirm all state files are updated

### Step 6: Next Steps

Suggest the next command:
```
Recon complete for <target>.
Discovered <X> endpoints, <Y> input vectors.
Tech stack: <summary>

Suggested next step: /hunt <recommended-vuln-class>
```

## Resuming Partial Recon

If the user runs `/recon` again on a target with existing recon data:
1. Show what phases are already complete
2. Ask: "Resume from Phase X, or start fresh?"
3. If resuming, skip completed phases
4. If starting fresh, clear and rebuild state files (confirm with user first)
