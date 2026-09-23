#!/usr/bin/env python3
"""Assess authentication and authorization signals for discovered server routes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from backend_common import ensure_workspace, is_server_candidate, iter_source_files, read_json, read_text, route_risk_tags, safe_snippet, update_manifest, write_json

AUTHN_RE = re.compile(r"\b(authenticated|auth|login|session|jwt|passport|currentUser|principal|identity|requireUser)\b", re.I)
AUTHZ_RE = re.compile(r"\b(authorize|authorization|permission|policy|role|roles|tenant|owner|scope|can\(|ability|PreAuthorize|RequireAuthorization|RolesAllowed|Gate::|can:)\b", re.I)
PUBLIC_RE = re.compile(r"\b(public|anonymous|allowAnonymous|permitAll|skipAuth|noAuth)\b", re.I)
AUTH_FILE_RE = re.compile(r"(auth|permission|policy|guard|middleware|rbac|abac|tenant|owner)", re.I)
MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


def route_context(repo: Path, route: dict, radius: int = 14) -> str:
    path = repo / route.get("file", "")
    text = read_text(path)
    if not text:
        return route.get("snippet", "")
    lines = text.splitlines()
    line_no = int(route.get("line") or 1)
    start = max(0, line_no - radius - 1)
    end = min(len(lines), line_no + radius)
    return "\n".join(lines[start:end])


def classify_route(repo: Path, route: dict) -> dict:
    context = route_context(repo, route)
    method = (route.get("method") or "UNKNOWN").upper()
    tags = sorted(set(route.get("riskTags") or route_risk_tags(method, route.get("path", ""))))
    sensitive = bool(set(tags) & {"admin", "auth", "tenant", "user_data", "payment", "file", "webhook"}) or method in MUTATING
    authn_signals = sorted(set(route.get("authSignals", []) + AUTHN_RE.findall(context)))
    authz_signals = sorted(set(AUTHZ_RE.findall(context)))
    public_signals = sorted(set(PUBLIC_RE.findall(context)))

    if public_signals and not sensitive:
        status = "public_intended"
        severity = "info"
        issue = ""
    elif authz_signals:
        status = "authz_signal_present"
        severity = "info"
        issue = ""
    elif authn_signals and sensitive:
        status = "authn_only_or_unclear"
        severity = "medium"
        issue = "Route has authentication-like signals but no nearby role, owner, tenant, scope, or policy signal."
    elif sensitive:
        status = "no_auth_signal"
        severity = "high" if method in MUTATING or "admin" in tags or "payment" in tags else "medium"
        issue = "Sensitive or mutating route has no nearby authentication or authorization signal."
    else:
        status = "no_local_signal_low_context"
        severity = "info"
        issue = ""

    return {
        "method": method,
        "path": route.get("path", ""),
        "file": route.get("file", ""),
        "line": route.get("line", 0),
        "frameworkHint": route.get("frameworkHint", ""),
        "tags": tags,
        "status": status,
        "severity": severity,
        "authnSignals": authn_signals[:20],
        "authzSignals": authz_signals[:20],
        "publicSignals": public_signals[:20],
        "issue": issue,
        "snippet": route.get("snippet", ""),
    }


def global_auth_assets(repo: Path) -> list[dict]:
    assets = []
    for rel, path in iter_source_files(repo):
        if not AUTH_FILE_RE.search(rel):
            continue
        text = read_text(path)
        if not text:
            continue
        if not is_server_candidate(rel, path, text):
            continue
        signal_count = len(AUTHN_RE.findall(text)) + len(AUTHZ_RE.findall(text))
        if signal_count == 0:
            continue
        assets.append({"path": rel, "signalCount": signal_count, "sample": safe_snippet(next((line for line in text.splitlines() if AUTHN_RE.search(line) or AUTHZ_RE.search(line)), ""))})
    return sorted(assets, key=lambda item: (-item["signalCount"], item["path"]))[:100]


def build(repo: Path, workspace: Path) -> dict:
    route_map = read_json(workspace / "state" / "server_route_map.json")
    routes = [classify_route(repo, route) for route in route_map.get("routes", [])]
    issues = [route for route in routes if route.get("issue")]
    summary = {}
    for route in routes:
        summary[route["status"]] = summary.get(route["status"], 0) + 1
    return {
        "repo": str(repo),
        "routeCount": len(routes),
        "summary": dict(sorted(summary.items())),
        "routes": routes,
        "issues": issues,
        "globalAuthAssets": global_auth_assets(repo),
    }


def render_markdown(payload: dict) -> str:
    lines = ["# Authorization Map", "", f"- Routes analyzed: {payload.get('routeCount', 0)}", f"- Issues requiring review: {len(payload.get('issues', []))}", ""]
    lines.append("## Summary")
    for status, count in payload.get("summary", {}).items():
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Review Queue"])
    if not payload.get("issues"):
        lines.append("- No authorization gaps inferred from route-local signals.")
    for issue in payload.get("issues", [])[:100]:
        lines.append(f"- {issue['severity']}: `{issue['method']} {issue['path']}` `{issue['file']}:{issue['line']}` - {issue['issue']}")
    lines.extend(["", "## Auth Assets"])
    if not payload.get("globalAuthAssets"):
        lines.append("- No auth-specific files detected.")
    for asset in payload.get("globalAuthAssets", [])[:50]:
        lines.append(f"- `{asset['path']}` signals={asset['signalCount']} sample={asset['sample']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess route authentication and authorization signals.")
    parser.add_argument("--repo", required=True, help="Repository path")
    parser.add_argument("--workspace", required=True, help="Audit workspace")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    if not repo.exists():
        raise SystemExit(f"Repository path does not exist: {repo}")
    state, evidence = ensure_workspace(workspace)
    payload = build(repo, workspace)
    write_json(state / "authz_map.json", payload)
    (evidence / "authz_map.md").write_text(render_markdown(payload), encoding="utf-8")
    update_manifest(workspace, "authz_map")
    print(json.dumps({"routes": payload["routeCount"], "issues": len(payload["issues"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
