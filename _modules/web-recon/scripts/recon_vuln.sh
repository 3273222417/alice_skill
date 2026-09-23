#!/bin/bash
# recon_vuln.sh — Nuclei Scan + Open Redirect + S3 Buckets
# Usage: ./recon_vuln.sh <domain> <output_dir>
#
# Phases covered:
#   6    Nuclei scan (CVEs, misconfigs, data exposure)
#   7    Open Redirect testing
#   8    S3 Buckets and Cloud Assets
#
# Requires: $OUT/dns/urls.txt and $OUT/urls/params.txt from the active phase

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# --- Args ---
DOMAIN="${1:?Usage: $0 <domain> <output_dir>}"
OUT="${2:?Usage: $0 <domain> <output_dir>}"

# Verify previous phases ran
if [ ! -f "$OUT/dns/urls.txt" ]; then
  err "Previous phase output not found. Run recon_passive.sh and recon_active.sh first."
  exit 1
fi

mkdir -p "$OUT/vulns"

ensure_httpx_go || exit 1

# ============================================================
# PHASE 6 — Nuclei Scan
# ============================================================

if phase_done "6_nuclei" "$OUT"; then
  ok "PHASE 6 already done — skipping ($(count_lines "$OUT/vulns/nuclei.txt") findings)"
else
  log "PHASE 6 — Nuclei Scan"

  touch "$OUT/vulns/nuclei.txt" "$OUT/vulns/nuclei_params.txt"

  if has_tool nuclei; then
    # Main scan: live hosts
    cat "$OUT/dns/urls.txt" | nuclei \
      -severity critical,high,medium \
      -tags exposure,config,default-login,auth-bypass,api,token,backup,cve \
      -rate-limit 30 \
      -concurrency 25 \
      -silent \
      -o "$OUT/vulns/nuclei.txt" \
      2>/dev/null || true

    # Scan on parameterized endpoints
    if [ -f "$OUT/urls/params.txt" ] && [ -s "$OUT/urls/params.txt" ]; then
      head -200 "$OUT/urls/params.txt" | nuclei \
        -severity critical,high,medium \
        -tags sqli,xss,ssrf,redirect,lfi \
        -rate-limit 20 \
        -silent \
        -o "$OUT/vulns/nuclei_params.txt" \
        2>/dev/null || true
    fi

    NUCLEI_COUNT=$(count_lines "$OUT/vulns/nuclei.txt")
    NUCLEI_PARAMS=$(count_lines "$OUT/vulns/nuclei_params.txt")
    ok "Nuclei findings: hosts=$NUCLEI_COUNT params=$NUCLEI_PARAMS"

    [ "$NUCLEI_COUNT" -gt 0 ] && warn "Review $OUT/vulns/nuclei.txt for critical/high findings"
  else
    warn "nuclei not found — skipping vulnerability scan"
  fi

  mark_done "6_nuclei" "$OUT"
fi

# ============================================================
# PHASE 7 — Open Redirect
# ============================================================

if phase_done "7_redirect" "$OUT"; then
  ok "PHASE 7 already done — skipping"
else
  log "PHASE 7 — Open Redirect testing"

  touch "$OUT/vulns/open_redirect.txt"

  if [ -f "$OUT/urls/gf_redirect.txt" ] && [ -s "$OUT/urls/gf_redirect.txt" ] && has_tool qsreplace; then
    head -100 "$OUT/urls/gf_redirect.txt" \
      | qsreplace 'https://evil.com' 2>/dev/null \
      | httpx -silent -follow-redirects -match-string "evil.com" 2>/dev/null \
      | tee "$OUT/vulns/open_redirect.txt" || true

    REDIR_COUNT=$(count_lines "$OUT/vulns/open_redirect.txt")
    ok "Confirmed open redirects: $REDIR_COUNT"
  else
    warn "No redirect URLs to test (gf_redirect.txt empty or qsreplace not found)"
  fi

  mark_done "7_redirect" "$OUT"
fi

# ============================================================
# PHASE 8 — S3 Buckets and Cloud Assets
# ============================================================

if phase_done "8_cloud" "$OUT"; then
  ok "PHASE 8 already done — skipping"
else
  log "PHASE 8 — S3 Buckets and Cloud Assets"

  touch "$OUT/vulns/s3_buckets.txt"

  # Expand subdomains with assetfinder (write to .tmp to avoid reading+writing same file)
  if has_tool assetfinder && [ -f "$OUT/subs/all.txt" ]; then
    cat "$OUT/subs/all.txt" | assetfinder --subs-only 2>/dev/null > "$OUT/subs/assetfinder_extra.tmp" || true
    if has_tool anew; then
      cat "$OUT/subs/assetfinder_extra.tmp" | anew "$OUT/subs/all.txt" >/dev/null || true
    else
      cat "$OUT/subs/assetfinder_extra.tmp" >> "$OUT/subs/all.txt"
      sort -u "$OUT/subs/all.txt" -o "$OUT/subs/all.txt"
    fi
    rm -f "$OUT/subs/assetfinder_extra.tmp"
  fi

  if has_tool httprobe && [ -f "$OUT/subs/all.txt" ]; then
    if has_tool anew; then
      cat "$OUT/subs/all.txt" | httprobe 2>/dev/null | anew "$OUT/dns/urls.txt" >/dev/null || true
    else
      cat "$OUT/subs/all.txt" | httprobe 2>/dev/null >> "$OUT/dns/urls.txt" || true
      sort -u "$OUT/dns/urls.txt" -o "$OUT/dns/urls.txt"
    fi
  fi

  # meg + gf s3-buckets
  if has_tool meg && has_tool gf; then
    mkdir -p "$OUT/vulns/meg_out"
    meg -d 1000 -v / "$OUT/dns/urls.txt" "$OUT/vulns/meg_out" 2>/dev/null || true
    gf s3-buckets "$OUT/vulns/meg_out/" 2>/dev/null | tee "$OUT/vulns/s3_buckets.txt" || true
  fi

  S3_COUNT=$(count_lines "$OUT/vulns/s3_buckets.txt")
  ok "S3 Buckets found: $S3_COUNT"

  mark_done "8_cloud" "$OUT"
fi

# ============================================================
# JSON Summary
# ============================================================

NUCLEI_TOTAL=$(count_lines "$OUT/vulns/nuclei.txt")
NUCLEI_PARAMS_TOTAL=$(count_lines "$OUT/vulns/nuclei_params.txt")
REDIR_TOTAL=$(count_lines "$OUT/vulns/open_redirect.txt")
S3_TOTAL=$(count_lines "$OUT/vulns/s3_buckets.txt")

# Count nuclei by severity
NUCLEI_CRIT=$(grep -ci "\[critical\]" "$OUT/vulns/nuclei.txt" 2>/dev/null || echo 0)
NUCLEI_HIGH=$(grep -ci "\[high\]" "$OUT/vulns/nuclei.txt" 2>/dev/null || echo 0)
NUCLEI_MED=$(grep -ci "\[medium\]" "$OUT/vulns/nuclei.txt" 2>/dev/null || echo 0)

emit_summary "{
  \"phase\": \"vuln\",
  \"domain\": \"$DOMAIN\",
  \"nuclei\": {\"total\": $NUCLEI_TOTAL, \"critical\": $NUCLEI_CRIT, \"high\": $NUCLEI_HIGH, \"medium\": $NUCLEI_MED},
  \"nuclei_params\": $NUCLEI_PARAMS_TOTAL,
  \"open_redirects\": $REDIR_TOTAL,
  \"s3_buckets\": $S3_TOTAL,
  \"output_dir\": \"$OUT\"
}"
