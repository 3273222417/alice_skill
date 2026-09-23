#!/usr/bin/env python3
"""Assess input validation coverage for discovered server routes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from backend_common import ensure_workspace, is_server_candidate, iter_source_files, read_json, read_text, safe_snippet, update_manifest, write_json

VALIDATION_RE = re.compile(
    r"\b(zod|joi|yup|superstruct|class-validator|class-transformer|Dto\b|DTO\b|schema\.parse|safeParse|validate\s*\(|validationPipe|pydantic|BaseModel|Serializer|FormRequest|rules\s*\(|@Valid\b|@Validated\b|BindingResult|go-playground/validator|ShouldBind|BindJSON|ModelState\.IsValid)\b",
    re.I,
)
SANITIZER_RE = re.compile(r"\b(sanitize|escape|xss|DOMPurify|validator\.|bleach|htmlspecialchars|strip_tags)\b", re.I)
FILE_VALIDATION_RE = re.compile(r"\b(fileFilter|limits\s*:|mimetype|content-type|extension|virus|clamav|sizeLimit|maxSize|max_file_size)\b", re.I)
MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


def route_context(repo: Path, route: dict, radius: int = 18) -> str:
    text = read_text(repo / route.get("file", ""))
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
    tags = route.get("riskTags", [])
    validation_signals = sorted(set(route.get("validationSignals", []) + VALIDATION_RE.findall(context)))[:30]
    sanitizer_signals = sorted(set(SANITIZER_RE.findall(context)))[:30]
    file_signals = sorted(set(FILE_VALIDATION_RE.findall(context)))[:30]
    needs_input_validation = method in MUTATING or "file" in tags or "webhook" in tags

    if validation_signals or ("file" in tags and file_signals):
        status = "validation_signal_present"
        severity = "info"
        issue = ""
    elif needs_input_validation:
        status = "missing_local_validation_signal"
        severity = "high" if "file" in tags else "medium"
        issue = "Route appears to accept state-changing or high-risk input but has no nearby validation signal."
    else:
        status = "not_required_or_unknown"
        severity = "info"
        issue = ""

    return {
        "method": method,
        "path": route.get("path", ""),
        "file": route.get("file", ""),
        "line": route.get("line", 0),
        "tags": tags,
        "status": status,
        "severity": severity,
        "issue": issue,
        "validationSignals": validation_signals,
        "sanitizerSignals": sanitizer_signals,
        "fileValidationSignals": file_signals,
        "snippet": route.get("snippet", ""),
    }


def global_validation_assets(repo: Path) -> list[dict]:
    assets = []
    for rel, path in iter_source_files(repo):
        text = read_text(path)
        if not text:
            continue
        if not is_server_candidate(rel, path, text):
            continue
        count = len(VALIDATION_RE.findall(text)) + len(SANITIZER_RE.findall(text)) + len(FILE_VALIDATION_RE.findall(text))
        if count == 0:
            continue
        sample = next((line for line in text.splitlines() if VALIDATION_RE.search(line) or SANITIZER_RE.search(line) or FILE_VALIDATION_RE.search(line)), "")
        assets.append({"path": rel, "signalCount": count, "sample": safe_snippet(sample)})
    return sorted(assets, key=lambda item: (-item["signalCount"], item["path"]))[:150]


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
        "globalValidationAssets": global_validation_assets(repo),
    }


def render_markdown(payload: dict) -> str:
    lines = ["# Validation Coverage", "", f"- Routes analyzed: {payload.get('routeCount', 0)}", f"- Issues requiring review: {len(payload.get('issues', []))}", ""]
    lines.append("## Summary")
    for status, count in payload.get("summary", {}).items():
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Review Queue"])
    if not payload.get("issues"):
        lines.append("- No validation coverage gaps inferred from route-local signals.")
    for issue in payload.get("issues", [])[:100]:
        lines.append(f"- {issue['severity']}: `{issue['method']} {issue['path']}` `{issue['file']}:{issue['line']}` - {issue['issue']}")
    lines.extend(["", "## Validation Assets"])
    if not payload.get("globalValidationAssets"):
        lines.append("- No validation assets detected.")
    for asset in payload.get("globalValidationAssets", [])[:50]:
        lines.append(f"- `{asset['path']}` signals={asset['signalCount']} sample={asset['sample']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess input validation coverage.")
    parser.add_argument("--repo", required=True, help="Repository path")
    parser.add_argument("--workspace", required=True, help="Audit workspace")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    if not repo.exists():
        raise SystemExit(f"Repository path does not exist: {repo}")
    state, evidence = ensure_workspace(workspace)
    payload = build(repo, workspace)
    write_json(state / "validation_coverage.json", payload)
    (evidence / "validation_coverage.md").write_text(render_markdown(payload), encoding="utf-8")
    update_manifest(workspace, "validation_coverage")
    print(json.dumps({"routes": payload["routeCount"], "issues": len(payload["issues"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
