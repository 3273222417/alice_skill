#!/bin/bash
# recon_passive.sh — Passive Subdomain Enumeration + DNS + Live Detection + CMS Scan
# Usage: ./recon_passive.sh <domain> <output_dir> [--bruteforce]
#
# Phases covered:
#   1    Passive subdomain collection (assetfinder, subfinder, findomain, amass, jldc)
#   1.2  DNS bruteforce with puredns (OPTIONAL — only with --bruteforce flag)
#   2    DNS resolution + live detection + screenshots (gowitness)
#   2.1  WAF detection (wafw00f)
#   2.2  CVE lookup by IP (sdlookup)
#   2.3  CMS detection + scan (WPScan / Droopescan / joomscan.py)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# --- Args ---
DOMAIN="${1:?Usage: $0 <domain> <output_dir> [--bruteforce]}"
OUT="${2:?Usage: $0 <domain> <output_dir> [--bruteforce]}"
BRUTEFORCE=false
[[ "${3:-}" == "--bruteforce" ]] && BRUTEFORCE=true

mkdir -p "$OUT"/{subs,dns,vulns,screenshots}

ensure_httpx_go || exit 1

# ============================================================
# PHASE 1 — Subdomain Enumeration
# ============================================================

if phase_done "1_subs" "$OUT"; then
  ok "PHASE 1 already done — skipping ($(count_lines "$OUT/subs/all.txt") subdomains)"
else
  log "PHASE 1 — Passive subdomain enumeration for $DOMAIN"

  # Parallel: assetfinder + subfinder + findomain + amass (with timeout)
  if has_tool assetfinder; then
    DOMAIN_ESC=$(echo "$DOMAIN" | sed 's/\./\\./g')
    echo "$DOMAIN" | assetfinder 2>/dev/null | grep -E "(^|\.)${DOMAIN_ESC}$" > "$OUT/subs/af.txt"
  fi &

  if has_tool subfinder; then
    subfinder -d "$DOMAIN" -silent > "$OUT/subs/sf.txt" 2>/dev/null
  fi &

  if has_tool findomain; then
    findomain -t "$DOMAIN" -q > "$OUT/subs/fd.txt" 2>/dev/null
  fi &

  if has_tool amass; then
    timeout 120 amass enum -passive -d "$DOMAIN" -o "$OUT/subs/amass.txt" 2>/dev/null
  fi &

  wait

  # JLDC API — public passive source, no rate limit
  # Uses sed instead of grep -P for macOS compatibility
  curl -s "https://jldc.me/anubis/subdomains/${DOMAIN}" 2>/dev/null \
    | sed 's/,/\n/g' | sed -n 's/.*"\([a-zA-Z0-9._-]*\.'"${DOMAIN}"'\)".*/\1/p' \
    | sort -u > "$OUT/subs/jldc.txt" 2>/dev/null || true

  # Consolidate all sources
  cat "$OUT"/subs/*.txt 2>/dev/null | sort -u > "$OUT/subs/all.txt"
  SUBS_COUNT=$(count_lines "$OUT/subs/all.txt")
  ok "Passive subdomains: $SUBS_COUNT"

  # Optional DNS bruteforce
  if $BRUTEFORCE; then
    SECLISTS=$(find_seclists "$(dirname "$OUT")")
    RESOLVERS=$(find_resolvers "$(dirname "$OUT")")
    if has_tool puredns && [ -n "$SECLISTS" ] && [ -n "$RESOLVERS" ]; then
      log "PHASE 1.2 — DNS bruteforce with puredns"
      puredns bruteforce \
        "$SECLISTS/Discovery/DNS/n0kovo_subdomains.txt" \
        "$DOMAIN" \
        --resolvers "$RESOLVERS" \
        --wildcard-tests 5 \
        --skip-wildcard-filter \
        --threads 200 \
        -q >> "$OUT/subs/all.txt" 2>/dev/null || true
      sort -u "$OUT/subs/all.txt" -o "$OUT/subs/all.txt"
      SUBS_COUNT=$(count_lines "$OUT/subs/all.txt")
      ok "Subdomains after bruteforce: $SUBS_COUNT"
    else
      warn "puredns, SecLists, or resolvers not found — skipping bruteforce"
    fi
  elif [ "$SUBS_COUNT" -lt 20 ]; then
    warn "Low subdomain count ($SUBS_COUNT) — consider running with --bruteforce"
  fi

  mark_done "1_subs" "$OUT"
fi

# ============================================================
# PHASE 2 — DNS Resolution + Live Detection + Screenshots
# ============================================================

if phase_done "2_live" "$OUT"; then
  ok "PHASE 2 already done — skipping ($(count_lines "$OUT/dns/urls.txt") live hosts)"
else
  log "PHASE 2 — DNS resolution + live detection"

  if has_tool dnsx && has_tool httpx; then
    cat "$OUT/subs/all.txt" \
      | dnsx -silent -a 2>/dev/null \
      | httpx -silent -ip -status-code -title -tech-detect -follow-redirects \
      | tee "$OUT/dns/live.txt"

    # Extract URLs and IPs
    awk '{print $1}' "$OUT/dns/live.txt" > "$OUT/dns/urls.txt"
    awk '{gsub(/\[|\]/,"",$2); print "http://" $2}' "$OUT/dns/live.txt" >> "$OUT/dns/urls.txt"
    sort -u "$OUT/dns/urls.txt" -o "$OUT/dns/urls.txt"
  else
    err "dnsx or httpx not found — PHASE 2 cannot proceed"
    exit 1
  fi

  LIVE_COUNT=$(count_lines "$OUT/dns/urls.txt")
  ok "Live hosts: $LIVE_COUNT"

  # Screenshots with gowitness
  if has_tool gowitness && [ "$LIVE_COUNT" -gt 0 ]; then
    log "Taking screenshots with gowitness..."
    gowitness scan file -f "$OUT/dns/urls.txt" \
      --screenshot-path "$OUT/screenshots" \
      --timeout 10 2>/dev/null || true
  fi

  # WAF Detection
  if has_tool wafw00f; then
    log "WAF detection..."
    awk '{print $1}' "$OUT/dns/live.txt" | head -20 \
      | xargs -P 5 -I@ wafw00f @ 2>/dev/null \
      | tee "$OUT/dns/waf_detection.txt" || true
    WAF_COUNT=$(grep -c 'is behind' "$OUT/dns/waf_detection.txt" 2>/dev/null || echo 0)
    ok "WAFs detected: $WAF_COUNT"
  fi

  # CVE lookup by IP
  if has_tool sdlookup; then
    log "CVE lookup by IP (sdlookup)..."
    awk '{gsub(/\[|\]/,"",$2); print $2}' "$OUT/dns/live.txt" | sort -u \
      | xargs -I@ sh -c 'echo @ | sdlookup -json 2>/dev/null | python3 -m json.tool' \
      > "$OUT/dns/sdlookup.txt" 2>/dev/null || true
  fi

  mark_done "2_live" "$OUT"
fi

# ============================================================
# PHASE 2.2 — CMS Detection + Scan
# ============================================================

if phase_done "2_cms" "$OUT"; then
  ok "PHASE 2.2 already done — skipping"
else
  log "PHASE 2.2 — CMS detection"

  grep -iE "\[WordPress\]|\[wp\]" "$OUT/dns/live.txt" 2>/dev/null | awk '{print $1}' | sort -u > "$OUT/vulns/cms_wordpress.txt" || true
  grep -i "\[Drupal\]" "$OUT/dns/live.txt" 2>/dev/null | awk '{print $1}' | sort -u > "$OUT/vulns/cms_drupal.txt" || true
  grep -i "\[Joomla\]" "$OUT/dns/live.txt" 2>/dev/null | awk '{print $1}' | sort -u > "$OUT/vulns/cms_joomla.txt" || true

  WP_COUNT=$(count_lines "$OUT/vulns/cms_wordpress.txt")
  DRUPAL_COUNT=$(count_lines "$OUT/vulns/cms_drupal.txt")
  JOOMLA_COUNT=$(count_lines "$OUT/vulns/cms_joomla.txt")

  ok "CMS detected — WordPress: $WP_COUNT | Drupal: $DRUPAL_COUNT | Joomla: $JOOMLA_COUNT"

  # WordPress scan
  if [ "$WP_COUNT" -gt 0 ]; then
    while IFS= read -r url; do
      host_safe=$(echo "$url" | sed 's|[:/]|_|g')
      if has_tool wpscan; then
        log "WPScan: $url"
        wpscan --url "$url" \
          --enumerate vp,vt,u,m \
          --plugins-detection aggressive \
          --random-user-agent \
          --no-banner 2>/dev/null \
          | tee "$OUT/vulns/wpscan_${host_safe}.txt" || true
      else
        log "wpscan_lite.py (fallback): $url"
        python3 "$SCRIPT_DIR/wpscan_lite.py" \
          --url "$url" \
          --output "$OUT/vulns/wpscan_${host_safe}.json" 2>/dev/null \
          | tee "$OUT/vulns/wpscan_${host_safe}.txt" || true
      fi
    done < "$OUT/vulns/cms_wordpress.txt"
  fi

  # Drupal scan
  if [ "$DRUPAL_COUNT" -gt 0 ] && has_tool droopescan; then
    while IFS= read -r url; do
      host_safe=$(echo "$url" | sed 's|[:/]|_|g')
      log "Droopescan: $url"
      droopescan scan drupal -u "$url" --threads 10 2>/dev/null \
        | tee "$OUT/vulns/droopescan_${host_safe}.txt" || true
    done < "$OUT/vulns/cms_drupal.txt"
  fi

  # Joomla scan
  if [ "$JOOMLA_COUNT" -gt 0 ]; then
    while IFS= read -r url; do
      host_safe=$(echo "$url" | sed 's|[:/]|_|g')
      log "JoomScan: $url"
      python3 "$SCRIPT_DIR/joomscan.py" \
        --url "$url" \
        --output "$OUT/vulns/joomscan_${host_safe}.json" 2>/dev/null \
        | tee "$OUT/vulns/joomscan_${host_safe}.txt" || true
    done < "$OUT/vulns/cms_joomla.txt"
  fi

  mark_done "2_cms" "$OUT"
fi

# ============================================================
# JSON Summary
# ============================================================

SUBS_TOTAL=$(count_lines "$OUT/subs/all.txt")
LIVE_TOTAL=$(count_lines "$OUT/dns/urls.txt")
WAF_TOTAL=$(grep -c 'is behind' "$OUT/dns/waf_detection.txt" 2>/dev/null || echo 0)
WP=$(count_lines "$OUT/vulns/cms_wordpress.txt")
DR=$(count_lines "$OUT/vulns/cms_drupal.txt")
JO=$(count_lines "$OUT/vulns/cms_joomla.txt")

emit_summary "{
  \"phase\": \"passive\",
  \"domain\": \"$DOMAIN\",
  \"subdomains\": $SUBS_TOTAL,
  \"live_hosts\": $LIVE_TOTAL,
  \"wafs_detected\": $WAF_TOTAL,
  \"cms\": {\"wordpress\": $WP, \"drupal\": $DR, \"joomla\": $JO},
  \"bruteforce\": $BRUTEFORCE,
  \"output_dir\": \"$OUT\"
}"
