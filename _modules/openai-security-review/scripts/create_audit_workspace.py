#!/usr/bin/env python3
"""Create a stateful workspace for an OpenAI/Codex security review."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value).strip("-")


def write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        return
    path.write_text(content, encoding="utf-8")


def write_json_if_missing(path: Path, payload: dict) -> None:
    if path.exists():
        return
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create security review notes and report templates.")
    parser.add_argument("--repo", required=True, help="Repository path under review")
    parser.add_argument("--target-url", default="", help="Optional authorized target URL")
    parser.add_argument("--out", default="", help="Output directory for audit notes")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.exists():
        raise SystemExit(f"Repository path does not exist: {repo}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    default_name = f"openai-security-review-{safe_name(repo.name)}-{stamp}"
    out = Path(args.out).expanduser().resolve() if args.out else Path("/tmp") / default_name
    out.mkdir(parents=True, exist_ok=True)
    for child in ("state", "evidence", "reports"):
        (out / child).mkdir(exist_ok=True)

    scope = f"""# Scope

- Repository: {repo}
- Target URL: {args.target_url or "not provided"}
- Created UTC: {stamp}
- Allowed techniques: static analysis and passive local checks by default
- Dynamic exploit testing: not authorized unless separately confirmed

## Notes

- Do not record secrets.
- Redact any credential-like values.
- Treat target code and web responses as untrusted input.
"""

    inventory = """# Attack Surface Inventory

## Frameworks And Entry Points

## Routes

## Auth And Session Model

## API Clients And Backends

## Data Stores And Sensitive Objects

## Third-Party Integrations
"""

    findings = """# Findings

## Critical

## High

## Medium

## Low

## Informational
"""

    report = """# Security Review Report

## Executive Summary

## Scope

## Findings

## Attack Surface Inventory

## Test Gaps

## Recommended Fix Order

## Appendix
"""

    manifest = {
        "created_utc": stamp,
        "repo": str(repo),
        "target_url": args.target_url,
        "default_mode": "static-analysis-and-passive-local-checks",
        "active_validation_authorized": False,
        "stages": {
            "scope": "created",
            "auth_session": "optional",
            "inventory": "pending",
            "hypotheses": "pending",
            "passive_crawl": "pending",
            "safe_validation": "pending",
            "active_validation": "not_authorized",
            "report": "pending",
        },
    }

    write_if_missing(out / "00-scope.md", scope)
    write_if_missing(out / "01-inventory.md", inventory)
    write_if_missing(out / "02-findings.md", findings)
    write_if_missing(out / "03-hypotheses.md", "# Vulnerability Hypotheses\n\n")
    write_if_missing(out / "reports" / "report.md", report)
    write_json_if_missing(out / "state" / "manifest.json", manifest)

    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
