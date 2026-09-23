#!/usr/bin/env python3
"""Run read-only/passive validation checks against an authorized target URL."""

from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

REQUIRED_HEADERS = [
    "content-security-policy",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
]


def fetch(url: str, method: str = "GET", timeout: int = 10) -> dict:
    request = urllib.request.Request(url, method=method, headers={"User-Agent": "openai-security-review/1.0"})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            body = response.read(400_000) if method == "GET" else b""
            return {
                "ok": True,
                "url": response.geturl(),
                "status": response.status,
                "headers": {key.lower(): value for key, value in response.headers.items()},
                "body": body.decode("utf-8", errors="replace"),
            }
    except urllib.error.HTTPError as error:
        body = error.read(200_000) if method == "GET" else b""
        return {
            "ok": False,
            "url": url,
            "status": error.code,
            "headers": {key.lower(): value for key, value in error.headers.items()},
            "body": body.decode("utf-8", errors="replace"),
            "error": str(error),
        }
    except Exception as error:  # noqa: BLE001 - command-line diagnostic output
        return {"ok": False, "url": url, "status": None, "headers": {}, "body": "", "error": str(error)}


def analyze_headers(headers: dict, scheme: str) -> list[dict]:
    issues: list[dict] = []
    for header in REQUIRED_HEADERS:
        if header not in headers:
            issues.append({"severity": "low", "kind": "missing_header", "header": header})
    if scheme == "https" and "strict-transport-security" not in headers:
        issues.append({"severity": "low", "kind": "missing_header", "header": "strict-transport-security"})
    csp = headers.get("content-security-policy", "")
    if "'unsafe-inline'" in csp or "'unsafe-eval'" in csp:
        issues.append({"severity": "medium", "kind": "weak_csp", "header": "content-security-policy", "detail": "CSP allows unsafe-inline or unsafe-eval"})
    return issues


def analyze_html(base_url: str, html: str) -> dict:
    source_map_refs = sorted(set(re.findall(r"sourceMappingURL=([^\s\"')]+)", html)))
    script_srcs = sorted(set(re.findall(r"<script[^>]+src=[\"']([^\"']+)[\"']", html, flags=re.I)))
    same_origin_scripts = [urljoin(base_url, src) for src in script_srcs]
    stack_trace_markers = [marker for marker in ("webpack", "vite", "stack trace", "at Object.", "__vite") if marker.lower() in html.lower()]
    return {
        "source_map_refs": source_map_refs,
        "script_srcs": same_origin_scripts,
        "stack_trace_markers": stack_trace_markers,
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# Passive Validation",
        "",
        f"- Target: {payload['target_url']}",
        f"- Final URL: {payload.get('final_url', '')}",
        f"- Status: {payload.get('status')}",
        "",
        "## Header Findings",
    ]
    if payload["issues"]:
        for issue in payload["issues"]:
            detail = issue.get("detail") or issue.get("header") or issue["kind"]
            lines.append(f"- {issue['severity']}: {issue['kind']} - {detail}")
    else:
        lines.append("- No header issues found by passive checks.")

    lines.extend(["", "## HTML Signals"])
    html = payload.get("html_signals", {})
    for key, values in html.items():
        lines.append(f"- {key}: {len(values)}")
        for value in values[:20]:
            lines.append(f"  - `{value}`")
    lines.append("")
    return "\n".join(lines)


def update_manifest(workspace: Path) -> None:
    manifest_path = workspace / "state" / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.setdefault("stages", {})["safe_validation"] = "completed"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run safe read-only validation checks.")
    parser.add_argument("--target-url", required=True, help="Authorized target URL")
    parser.add_argument("--workspace", default="", help="Audit workspace")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds")
    args = parser.parse_args()

    parsed = urlparse(args.target_url)
    if parsed.scheme not in {"http", "https"}:
        raise SystemExit("Only http and https target URLs are supported.")

    head = fetch(args.target_url, method="HEAD", timeout=args.timeout)
    get = fetch(args.target_url, method="GET", timeout=args.timeout)
    headers = get.get("headers") or head.get("headers") or {}
    payload = {
        "target_url": args.target_url,
        "final_url": get.get("url") or head.get("url"),
        "status": get.get("status") or head.get("status"),
        "head_error": head.get("error"),
        "get_error": get.get("error"),
        "headers": headers,
        "issues": analyze_headers(headers, parsed.scheme),
        "html_signals": analyze_html(args.target_url, get.get("body", "")),
    }

    workspace = Path(args.workspace).expanduser().resolve() if args.workspace else None
    if workspace:
        (workspace / "state").mkdir(parents=True, exist_ok=True)
        (workspace / "evidence").mkdir(parents=True, exist_ok=True)
        (workspace / "state" / "passive_validation.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (workspace / "evidence" / "passive_validation.md").write_text(render_markdown(payload), encoding="utf-8")
        update_manifest(workspace)

    print(json.dumps({"status": payload["status"], "issues": len(payload["issues"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
