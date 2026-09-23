#!/bin/bash
# recon_active.sh — URL Discovery + Parameter Mining + JS Analysis + Content Discovery
# Usage: ./recon_active.sh <domain> <output_dir>
#
# Phases covered:
#   3    URL and parameter discovery (waybackurls, gau, katana, hakrawler, paramspider, gf)
#   4    JavaScript analysis (source maps, secrets, git exposed, sensitive files)
#   5    Content discovery (feroxbuster)
#
# Requires: $OUT/dns/urls.txt and $OUT/dns/live.txt from the passive phase

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# --- Args ---
DOMAIN="${1:?Usage: $0 <domain> <output_dir>}"
OUT="${2:?Usage: $0 <domain> <output_dir>}"

# Verify passive phase ran first
if [ ! -f "$OUT/dns/urls.txt" ] || [ ! -f "$OUT/dns/live.txt" ]; then
  err "Passive phase output not found. Run recon_passive.sh first."
  exit 1
fi

mkdir -p "$OUT"/{urls,js,content}

ensure_httpx_go || exit 1

# ============================================================
# PHASE 3 — URL and Parameter Discovery
# ============================================================

if phase_done "3_urls" "$OUT"; then
  ok "PHASE 3 already done — skipping ($(count_lines "$OUT/urls/clean.txt") URLs)"
else
  log "PHASE 3 — URL and parameter discovery"

  touch "$OUT/urls/historical.txt" "$OUT/urls/clean.txt" "$OUT/urls/params.txt"

  # 3.1 Historical URLs — parallel with tracked PIDs
  PIDS_URLS=()

  if has_tool waybackurls; then
    cat "$OUT/dns/urls.txt" | waybackurls 2>/dev/null | anew "$OUT/urls/historical.txt" >/dev/null &
    PIDS_URLS+=($!)
  fi

  if has_tool gau; then
    cat "$OUT/dns/urls.txt" | gau --threads 5 --timeout 15 \
      --blacklist png,jpg,gif,css,woff,woff2,svg,ico,ttf,eot 2>/dev/null \
      | anew "$OUT/urls/historical.txt" >/dev/null &
    PIDS_URLS+=($!)
  fi

  # 3.2 Active crawling with Katana (parallel with historical)
  if has_tool katana; then
    cat "$OUT/dns/urls.txt" | katana \
      -jc -jsl -hl --no-sandbox \
      -c 10 -p 5 -rd 3 -rl 15 \
      -silent 2>/dev/null \
      | anew "$OUT/urls/historical.txt" >/dev/null &
    PIDS_URLS+=($!)
  fi

  # 3.3 Hakrawler — endpoints with parameters (parallel)
  if has_tool hakrawler; then
    cat "$OUT/dns/urls.txt" | hakrawler -subs -d 3 -t 8 2>/dev/null \
      | grep "=" \
      | anew "$OUT/urls/params.txt" >/dev/null &
    PIDS_URLS+=($!)
  fi

  for pid in "${PIDS_URLS[@]}"; do
    wait "$pid" 2>/dev/null || true
  done

  # Deduplicate
  if has_tool uro; then
    cat "$OUT/urls/historical.txt" | uro 2>/dev/null | sort -u > "$OUT/urls/clean.txt"
  else
    sort -u "$OUT/urls/historical.txt" > "$OUT/urls/clean.txt"
  fi

  # 3.4 Paramspider
  if has_tool paramspider; then
    log "Paramspider on live hosts..."
    awk '{print $1}' "$OUT/dns/live.txt" | head -30 | while IFS= read -r host; do
      python3 "$(which paramspider)" -d "$host" --quiet 2>/dev/null || true
    done | anew "$OUT/urls/params.txt" >/dev/null
  fi

  # gf patterns — classify URLs by vulnerability type
  if has_tool gf; then
    log "Classifying URLs with gf patterns..."
    for pattern in xss sqli redirect ssrf lfi rce idor; do
      cat "$OUT/urls/clean.txt" "$OUT/urls/params.txt" 2>/dev/null \
        | gf "$pattern" 2>/dev/null \
        | sort -u > "$OUT/urls/gf_${pattern}.txt" || true
    done
  fi

  URLS_TOTAL=$(count_lines "$OUT/urls/clean.txt")
  PARAMS_TOTAL=$(count_lines "$OUT/urls/params.txt")
  ok "Unique URLs: $URLS_TOTAL | URLs with parameters: $PARAMS_TOTAL"

  mark_done "3_urls" "$OUT"
fi

# ============================================================
# PHASE 4 — JavaScript Analysis
# ============================================================

if phase_done "4_js" "$OUT"; then
  ok "PHASE 4 already done — skipping"
else
  log "PHASE 4 — JavaScript analysis (secrets, source maps, git, sensitive files)"

  touch "$OUT/js/sourcemap_results.txt" "$OUT/js/secrets.json" "$OUT/js/git_exposed.txt" "$OUT/js/sensitive_files.txt"

  # 4.1 Source Map Hunter (parallel)
  # Search in known locations first, then fall back to find
  SOURCEMAP_HUNTER=""
  for sp in "$(dirname "$OUT")/sourcemap_hunter.py" "$HOME/sourcemap_hunter.py"; do
    [ -f "$sp" ] && SOURCEMAP_HUNTER="$sp" && break
  done
  [ -z "$SOURCEMAP_HUNTER" ] && SOURCEMAP_HUNTER=$(find "$(dirname "$OUT")" -maxdepth 4 -name "sourcemap_hunter.py" 2>/dev/null | head -1)

  if [ -n "$SOURCEMAP_HUNTER" ]; then
    {
      awk '{print $1}' "$OUT/dns/live.txt" | head -20 | while IFS= read -r url; do
        python3 "$SOURCEMAP_HUNTER" "$url" 2>/dev/null || true
      done > "$OUT/js/sourcemap_results.txt"
    } &
    PID_SM=$!
  else
    PID_SM=""
    warn "sourcemap_hunter.py not found — skipping source map analysis"
  fi

  # 4.2 JS Secret Scanner (parallel)
  JS_SCANNER="$SCRIPT_DIR/js_secret_scanner.py"
  if [ -f "$JS_SCANNER" ]; then
    {
      python3 "$JS_SCANNER" \
        --urls-file "$OUT/dns/urls.txt" \
        --output "$OUT/js/secrets.json" 2>/dev/null || true
    } &
    PID_SEC=$!
  else
    PID_SEC=""
    warn "js_secret_scanner.py not found — skipping JS secret scan"
  fi

  # 4.3 Git Exposed — goop (parallel)
  if has_tool goop; then
    {
      cat "$OUT/dns/urls.txt" \
        | xargs -P 5 -I@ sh -c 'goop "$1" -f 2>/dev/null && echo "[GIT EXPOSED] $1"' _ @ \
        | grep "GIT EXPOSED" > "$OUT/js/git_exposed.txt" 2>/dev/null || true
    } &
    PID_GIT=$!
  else
    PID_GIT=""
  fi

  # 4.4 Sensitive file exposure (parallel) — live hosts only, -ml 50 filters soft-404s
  {
    cat "$OUT/dns/urls.txt" | while IFS= read -r url; do
      for path in /.env /.env.production /.env.local /config.json /config.js \
                  /app/config.js /settings.json /database.json /firebase.json \
                  /api_keys.json /credentials.json /secrets.json \
                  /google-services.json /docker-compose.yml /manifest.json \
                  /package.json /.git/config /wp-config.php /phpinfo.php \
                  /server-status /.aws/credentials /backup.sql /dump.sql; do
        echo "${url}${path}"
      done
    done | httpx -silent -mc 200,206 -ml 50 -t 50 2>/dev/null > "$OUT/js/sensitive_files.txt" || true
  } &
  PID_SENS=$!

  # Wait for all parallel jobs
  for pid in "$PID_SM" "$PID_SEC" "$PID_GIT" "$PID_SENS"; do
    [ -n "$pid" ] && wait "$pid" 2>/dev/null || true
  done

  GIT_COUNT=$(count_lines "$OUT/js/git_exposed.txt")
  SENS_COUNT=$(count_lines "$OUT/js/sensitive_files.txt")
  ok "Git exposed: $GIT_COUNT | Sensitive files: $SENS_COUNT"

  [ "$GIT_COUNT" -gt 0 ] && err "CRITICAL: Exposed .git repository detected!"
  [ "$SENS_COUNT" -gt 0 ] && warn "HIGH: Sensitive files found"

  mark_done "4_js" "$OUT"
fi

# ============================================================
# PHASE 5 — Content Discovery
# ============================================================

if phase_done "5_content" "$OUT"; then
  ok "PHASE 5 already done — skipping ($(count_lines "$OUT/content/all_dirs.txt") paths)"
else
  log "PHASE 5 — Content discovery"

  # Filter priority hosts (admin, api, dev, etc.)
  grep -iE "(admin|api|dev|stage|test|cms|portal|dashboard|internal|app)" \
    "$OUT/dns/live.txt" 2>/dev/null | awk '{print $1}' | head -10 > "$OUT/content/priority_hosts.txt" || true

  PRIORITY_COUNT=$(count_lines "$OUT/content/priority_hosts.txt")

  if [ "$PRIORITY_COUNT" -eq 0 ]; then
    # Fall back to first 5 live hosts
    head -5 "$OUT/dns/urls.txt" > "$OUT/content/priority_hosts.txt"
    PRIORITY_COUNT=$(count_lines "$OUT/content/priority_hosts.txt")
  fi

  if [ "$PRIORITY_COUNT" -gt 0 ] && has_tool feroxbuster; then
    # Auto-select smallest available wordlist
    SECLISTS=$(find_seclists "$(dirname "$OUT")" || echo "")
    WORDLIST=""
    if [ -n "$SECLISTS" ]; then
      for wl in \
        "$SECLISTS/Discovery/Web-Content/raft-small-directories.txt" \
        "$SECLISTS/Discovery/Web-Content/common.txt" \
        "$SECLISTS/Discovery/Web-Content/raft-medium-directories.txt"; do
        [ -f "$wl" ] && WORDLIST="$wl" && break
      done
    fi

    if [ -n "$WORDLIST" ]; then
      log "Wordlist: $(basename "$WORDLIST") | Hosts: $PRIORITY_COUNT"
      while IFS= read -r url; do
        feroxbuster -u "$url" \
          -w "$WORDLIST" \
          -s 200,201,204,301,302,307,401,403 \
          -t 30 --silent --no-state \
          -o "$OUT/content/$(echo "$url" | sed 's|[:/]|_|g').txt" 2>/dev/null || true
      done < "$OUT/content/priority_hosts.txt"
    else
      warn "No SecLists wordlist found — skipping feroxbuster"
    fi
  elif ! has_tool feroxbuster; then
    warn "feroxbuster not found"
  fi

  # Consolidate results (exclude priority_hosts.txt and all_dirs.txt from merge)
  find "$OUT/content" -name "*.txt" ! -name "priority_hosts.txt" ! -name "all_dirs.txt" -exec cat {} + 2>/dev/null \
    | grep -v "^#" | sort -u > "$OUT/content/all_dirs.txt" 2>/dev/null || true
  DIRS_COUNT=$(count_lines "$OUT/content/all_dirs.txt")
  ok "Discovered paths: $DIRS_COUNT"

  mark_done "5_content" "$OUT"
fi

# ============================================================
# JSON Summary
# ============================================================

URLS_TOTAL=$(count_lines "$OUT/urls/clean.txt")
PARAMS_TOTAL=$(count_lines "$OUT/urls/params.txt")
GIT_TOTAL=$(count_lines "$OUT/js/git_exposed.txt")
SENS_TOTAL=$(count_lines "$OUT/js/sensitive_files.txt")
DIRS_TOTAL=$(count_lines "$OUT/content/all_dirs.txt")

# gf pattern counts
GF_JSON="{"
for p in xss sqli redirect ssrf lfi rce idor; do
  c=$(count_lines "$OUT/urls/gf_${p}.txt")
  GF_JSON="$GF_JSON\"$p\":$c,"
done
GF_JSON="${GF_JSON%,}}"

emit_summary "{
  \"phase\": \"active\",
  \"domain\": \"$DOMAIN\",
  \"urls_unique\": $URLS_TOTAL,
  \"urls_with_params\": $PARAMS_TOTAL,
  \"git_exposed\": $GIT_TOTAL,
  \"sensitive_files\": $SENS_TOTAL,
  \"content_paths\": $DIRS_TOTAL,
  \"gf_patterns\": $GF_JSON,
  \"output_dir\": \"$OUT\"
}"
