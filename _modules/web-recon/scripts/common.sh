#!/bin/bash
# common.sh — Shared functions for web-recon scripts
# Compatible with: macOS (pdtm toolchain) + Kali Linux
# Sourced by recon_passive.sh, recon_active.sh, recon_vuln.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[*]${NC} $1" >&2; }
ok()   { echo -e "${GREEN}[+]${NC} $1" >&2; }
warn() { echo -e "${YELLOW}[!]${NC} $1" >&2; }
err()  { echo -e "${RED}[-]${NC} $1" >&2; }

# Check if a tool exists
has_tool() {
  command -v "$1" &>/dev/null
}

# Check tool and warn if missing
require_tool() {
  if ! has_tool "$1"; then
    warn "$1 not found — skipping"
    return 1
  fi
  return 0
}

# Checkpoint: check if phase already ran
phase_done() {
  local phase="$1"
  local out="$2"
  [ -f "$out/.phase_${phase}.done" ]
}

# Mark phase as completed
mark_done() {
  local phase="$1"
  local out="$2"
  touch "$out/.phase_${phase}.done"
}

# Count lines in a file (returns 0 if file does not exist)
count_lines() {
  [ -f "$1" ] && wc -l < "$1" | tr -d ' ' || echo "0"
}

# Locate SecLists — checks known paths first, then falls back to find
# Supports: macOS (home/Documents) + Kali Linux (/usr/share/seclists)
find_seclists() {
  local base="$1"
  for d in \
    "$base/SecLists" \
    "$HOME/SecLists" \
    "$HOME/Documents/Hacking/SecLists" \
    "/usr/share/seclists" \
    "/usr/share/SecLists" \
    "/opt/SecLists" \
    "/opt/seclists"; do
    [ -d "$d" ] && echo "$d" && return 0
  done
  local found
  found=$(find "$base" -maxdepth 3 -type d -iname "seclists" 2>/dev/null | head -1)
  [ -n "$found" ] && echo "$found" && return 0
  return 1
}

# Locate resolvers.txt — checks known paths first
find_resolvers() {
  local base="$1"
  for f in \
    "$base/resolvers.txt" \
    "$HOME/resolvers.txt" \
    "$HOME/tools/resolvers.txt" \
    "/usr/share/wordlists/resolvers.txt" \
    "/opt/resolvers.txt"; do
    [ -f "$f" ] && echo "$f" && return 0
  done
  local found
  found=$(find "$base" -maxdepth 3 -name "resolvers.txt" 2>/dev/null | head -1)
  [ -n "$found" ] && echo "$found" && return 0
  return 1
}

# Ensure httpx is the Go (ProjectDiscovery) version, not Python httpx
# Checks known installation paths for both macOS (pdtm) and Kali Linux
ensure_httpx_go() {
  local candidates=(
    "$HOME/.pdtm/go/bin/httpx"
    "$HOME/go/bin/httpx"
    "/usr/local/bin/httpx"
    "/usr/bin/httpx"
    "$(command -v httpx 2>/dev/null || true)"
  )

  for candidate in "${candidates[@]}"; do
    if [ -x "$candidate" ] && "$candidate" -version 2>&1 | grep -qi "projectdiscovery"; then
      export PATH="$(dirname "$candidate"):$PATH"
      return 0
    fi
  done

  err "httpx (ProjectDiscovery Go version) not found."
  err "Install options:"
  err "  macOS/pdtm : pdtm -i httpx"
  err "  Go install : go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest"
  err "  Kali Linux : apt install golang-httpx  (or use go install)"
  return 1
}

# Emit JSON summary to stdout for the Claude orchestrator to parse
emit_summary() {
  local json="$1"
  echo "---RECON_SUMMARY_JSON---"
  echo "$json"
  echo "---END_SUMMARY---"
}
