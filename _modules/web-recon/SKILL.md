---
name: web-recon
description: >
  Full offensive reconnaissance skill for Web Pentest and Bug Bounty. Activate when the
  user mentions recon, reconnaissance, subdomain enumeration, attack surface mapping,
  bug bounty recon, or any variation of "start a pentest" on a domain/target.
  Covers: subdomain enumeration, DNS resolution, live detection, screenshots, URL/parameter
  discovery, JS analysis (source maps + secrets), content discovery, nuclei scan, CMS scan
  (WordPress/Drupal/Joomla), and intelligence report generation. All output is saved in a
  subdirectory named after the target within the current project directory.
domain: web-application-security
tags: [recon, subdomain-enumeration, bug-bounty, osint, web-pentest, nuclei, cms-scan]
x-alice-class: pentest
---# Web Recon — Offensive Kill Chain

## Architecture

The skill is divided into **3 bash scripts** with checkpoint/resume and real parallelism:

```
scripts/
├── common.sh           # Shared functions (logging, has_tool, phase_done, etc.)
├── recon_passive.sh    # PHASES 1 + 2 + 2.2 (subs, DNS, live, CMS)
├── recon_active.sh     # PHASES 3 + 4 + 5 (URLs, JS, content discovery)
└── recon_vuln.sh       # PHASES 6 + 7 + 8 (nuclei, open redirect, S3)
```

Each script:
- Accepts `<domain> <output_dir>` as args
- Uses checkpoints (`.phase_X.done`) — can be re-run without repeating completed phases
- Emits a JSON summary via `---RECON_SUMMARY_JSON---` markers for Claude to parse
- Executes subtasks in parallel internally (background jobs + wait)

---

## Tool Priority

### 1. CLI via Bash — always first
```
subfinder > assetfinder > findomain   (passive enumeration)
dnsx                                  (DNS resolution)
httpx (Go version)                    (live detection — NEVER Python httpx)
nuclei                                (vulnerability scan)
katana > hakrawler > waybackurls      (crawling / URL discovery)
feroxbuster > ffuf                    (content discovery)
wafw00f                               (WAF detection)
paramspider > arjun                   (parameter discovery)
```

### 2. Bundled scripts — executed automatically by phases
```
js_secret_scanner.py   → PHASE 4 (JS secret scanning)
wpscan_lite.py         → PHASE 2.2 (fallback if wpscan not installed)
joomscan.py            → PHASE 2.2 (Joomla scan)
```

### 3. Manual curl / wget — for one-off requests

### 4. MCPs — if available (Burp, Chrome, Postman, Notion)

### 5. Always verify tools before use
```bash
command -v <tool> || echo "WARNING: <tool> not found"
```
Never assume a tool is installed. Never install without explicit permission.

---

## Operational Rules

- **Never install tools** without explicit permission (brew, pip, npm, go install, apt, etc.)
- **Never delete files** without explicit permission
- **DNS Bruteforce**: optional — only with explicit `--bruteforce` flag or passive count < 20 subs
- **SecLists wordlists**: always use the smallest available (small → common → medium)
- **httpx**: scripts enforce Go version via `ensure_httpx_go()` in common.sh

---

## Execution

### SETUP — Variables and Progress Tracking

```bash
DOMAIN="target.com"

PROJECT=$(echo "$DOMAIN" \
  | sed -E 's/\.(com\.br|org\.br|net\.br|gov\.br|com|org|net|io|br|co\.uk|co|uk|fr|de|jp|au|us|ca)$//' \
  | sed 's/\./-/g' \
  | tr '[:upper:]' '[:lower:]')

OUT="$(pwd)/$PROJECT"
SCRIPTS="$HOME/.claude/skills/web-recon/scripts"

mkdir -p "$OUT"/{subs,dns,urls,js,content,vulns,screenshots}
```

Create progress tasks with TaskCreate:
```
"PHASE 1 — Subdomain Enumeration"
"PHASE 2 — DNS + Live Detection + CMS"
"PHASE 3 — URLs and Parameters"
"PHASE 4 — JavaScript Analysis"
"PHASE 5 — Content Discovery"
"PHASE 6 — Nuclei Scan"
"PHASE 7 — Open Redirect"
"PHASE 8 — S3 / Cloud Assets"
"PHASE 9 — Report"
```

Mark each task `in_progress` when starting, `completed` when done.

---

### BLOCK 1 — Passive Recon (Phases 1 + 2 + 2.2)

```bash
bash "$SCRIPTS/recon_passive.sh" "$DOMAIN" "$OUT"
# Add --bruteforce if user explicitly requested it
```

**What it runs:**
- PHASE 1: Parallel passive enumeration (assetfinder, subfinder, findomain, amass with 120s timeout, JLDC API) + optional puredns bruteforce
- PHASE 2: dnsx → httpx pipeline, gowitness screenshots, wafw00f WAF detection, sdlookup CVE lookup
- PHASE 2.2: CMS detection (httpx tech-detect), WPScan/wpscan_lite.py, droopescan, joomscan.py

Read the JSON summary from stdout and update tasks with counts.

---

### BLOCK 2 — Active Recon (Phases 3 + 4 + 5)

```bash
bash "$SCRIPTS/recon_active.sh" "$DOMAIN" "$OUT"
```

**What it runs:**
- PHASE 3: Parallel historical URLs (waybackurls, gau with blacklist, katana, hakrawler), paramspider, gf patterns
- PHASE 4: Parallel JS analysis (sourcemap_hunter, js_secret_scanner, goop git exposed, sensitive file exposure with -ml 50)
- PHASE 5: feroxbuster with auto-selected wordlist (smallest available)

Read the JSON summary and update tasks. If secrets or .git found, flag as critical finding.

---

### BLOCK 3 — Vulnerability Scan (Phases 6 + 7 + 8)

```bash
bash "$SCRIPTS/recon_vuln.sh" "$DOMAIN" "$OUT"
```

**What it runs:**
- PHASE 6: nuclei scan on live hosts + parameterized endpoints
- PHASE 7: Open redirect via qsreplace + httpx
- PHASE 8: S3 bucket detection via assetfinder + httprobe + meg + gf

Read the JSON summary and update tasks with findings by severity.

---

### BLOCK 4 — Intelligence Report (Phase 9)

Consolidate all JSON summaries and output files into a report:

```
## RECON REPORT — [DOMAIN] — [DATE]
## Project: $PROJECT  |  Output: $OUT

### Attack Surface
- Unique subdomains: X
- Live HTTP hosts: X
- URLs with parameters: X
- CMS detected: [list]

### Critical Findings (exploitation priority)
1. [CRITICAL] JS Secrets: [file, type]
2. [CRITICAL] .git exposed: [hosts]
3. [HIGH] Nuclei findings: [summary by severity]
4. [HIGH] Sensitive files: [list]
5. [HIGH] CMS vulnerabilities: [wpscan/droopescan/joomscan findings]
6. [MEDIUM] XSS/SQLi URLs: [count by type]

### Next Vectors (ordered by impact)
1. Secrets → validate and attempt API/service access
2. .git exposed → goop to recover source code
3. SQLi params → sqlmap -m sqli.txt --batch --random-agent
4. XSS params → dalfox pipe / airixss pipeline
5. Open redirect → chain with SSRF or phishing
6. .env files → credentials for direct access
7. Outdated CMS → exploit detected CVEs

### Infrastructure
- Unique IPs: [list]
- Technologies detected: [httpx tech-detect]
- Potential CVEs (sdlookup): [list]
```

If Notion MCP is available, publish the report with `mcp__Notion__notion-create-pages`.

---

## Evidence Capture

Capture screenshots and save outputs to `$OUT/evidence/` throughout recon. Submit evidence to Notion when MCP is available.

```bash
mkdir -p "$OUT/evidence"

# Terminal screenshot (macOS)
screencapture -x "$OUT/evidence/recon_$(date +%Y%m%d_%H%M%S)_$DESCRIPTION.png"

# Terminal screenshot (Linux)
scrot "$OUT/evidence/recon_$(date +%Y%m%d_%H%M%S)_$DESCRIPTION.png"

# gowitness automatically screenshots all live subdomains
# Output goes to $OUT/screenshots/ via PHASE 2 of the script
```

**What to capture per phase:**
- Phase 1: final subdomain list (`subs/all_subs.txt` — word count visible)
- Phase 2: gowitness screenshots (automatic), httpx output with status codes, WAF detected
- Phase 4: JS secrets found (full scanner output including secret values)
- Phase 5: feroxbuster — sensitive endpoints discovered (admin panels, APIs, backups)
- Phase 6: nuclei — findings output with severity

**Submit to Notion:**
```
mcp__Notion__notion-create-pages  — create recon page with evidence attached
mcp__Notion__notion-update-page   — add image/text blocks per phase
```

---

## MCP Integration (when available)

### Burp Suite (`mcp__burp__*`)
When connected: replay/manipulate suspicious requests, confirm SQLi/XSS/LFI, capture evidence.

### Chrome Browser (`mcp__claude-in-chrome__*`)
For JS-heavy/SPA apps: navigate, inspect DOM/cookies/localStorage, capture network requests, read console logs.
> Always call `tabs_context_mcp` before any browser automation.

### Postman (`mcp__postman__*`)
Only if target exposes a REST/GraphQL API: import endpoints, IDOR/auth tests, document requests.

### Notion (`mcp__Notion__*`)
Publish final report and create subpages for each critical/high finding.

---

## Execution Modes

| Mode | When to use | What runs |
|------|-------------|-----------|
| `--quick` | Wide-scope bug bounty | Passive (no bruteforce) + nuclei |
| `--full` | Authorized pentest | All 3 blocks + report |
| `--js-only` | Specific target, frontend analysis | PHASE 4 of recon_active.sh only |
| `--passive` | OSINT without touching target | PHASE 1.1 + historical URLs only |

---

## Operational Notes

- **Checkpoint/resume**: If a script fails mid-run, re-running skips completed phases (`.phase_X.done`)
- **Token efficiency**: Scripts run everything via Bash and emit only JSON summary — do not read full tool output
- **Rate limiting**: In production bug bounty, reduce threads/rate-limit to avoid triggering alerts
- **WAF bypass via Host header**: `httpx -l ips.txt -H "Host: target.com" -status-code -path /`
- **Proxy through Burp**: `cat $OUT/dns/urls.txt | httpx -silent -proxy http://127.0.0.1:8080`
