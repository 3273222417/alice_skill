#!/usr/bin/env python3
"""Extract source-level API hints and correlate them with runtime observations."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    ".turbo",
    ".cache",
    "__pycache__",
}
TEXT_EXTENSIONS = {
    ".cjs",
    ".go",
    ".graphql",
    ".js",
    ".jsx",
    ".mjs",
    ".py",
    ".rb",
    ".rs",
    ".ts",
    ".tsx",
    ".vue",
}
HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
STRING_RE = re.compile(r"""['"`]((?:/api/|/api\b|api/|https?://)[^'"`<>{}\s\\]*)['"`]""")
FETCH_RE = re.compile(r"\b(fetch|axios|request|XMLHttpRequest)\b", re.I)
METHOD_RE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b", re.I)
AXIOS_METHOD_RE = re.compile(r"\baxios\.(get|post|put|patch|delete|head|options)\s*\(", re.I)
ROUTE_METHOD_RE = re.compile(r"\b(app|router|route)\.(get|post|put|patch|delete|head|options)\s*\(", re.I)
NEXT_ROUTE_FILE_RE = re.compile(r"(?:^|/)(app|pages)/.+/(route|page)\.(js|jsx|ts|tsx)$")


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def normalize_path(value: str) -> str:
    raw = value.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        return parsed.path or "/"
    if raw.startswith("api/"):
        return "/" + raw
    if not raw.startswith("/"):
        return "/" + raw
    return raw


def infer_method(line: str) -> str:
    axios_match = AXIOS_METHOD_RE.search(line)
    if axios_match:
        return axios_match.group(1).upper()
    route_match = ROUTE_METHOD_RE.search(line)
    if route_match:
        return route_match.group(2).upper()
    method_match = METHOD_RE.search(line)
    if method_match:
        return method_match.group(1).upper()
    if FETCH_RE.search(line):
        return "UNKNOWN"
    return "UNKNOWN"


def classify_api_hint(method: str, api_path: str, line: str) -> str:
    base_like = re.fullmatch(r"/api(?:/v\d+)?", api_path) is not None
    config_like = re.search(r"(BASE_URL|API_URL|baseURL|baseUrl)", line, re.I) is not None
    if method == "UNKNOWN" and (base_like or config_like):
        return "base"
    return "endpoint"


def route_path_from_file(rel: str) -> str:
    if not NEXT_ROUTE_FILE_RE.search(rel):
        return ""
    parts = rel.split("/")
    try:
        root_index = parts.index("app") if "app" in parts else parts.index("pages")
    except ValueError:
        return ""
    route_parts = parts[root_index + 1 :]
    if route_parts:
        route_parts[-1] = re.sub(r"\.(route|page)\.(js|jsx|ts|tsx)$", "", route_parts[-1])
    cleaned = [part for part in route_parts if part not in {"", "index", "page", "route"}]
    if not cleaned:
        return "/"
    return "/" + "/".join(cleaned)


def source_key(method: str, path: str) -> str:
    return f"{method.upper()} {path}"


def scan_repo(repo: Path) -> dict:
    endpoints: dict[str, dict] = {}
    route_files: list[dict] = []

    for path in sorted(repo.rglob("*")):
        rel_path = path.relative_to(repo)
        if should_skip(rel_path) or not path.is_file() or not is_text_file(path):
            continue
        rel = rel_path.as_posix()
        derived_route = route_path_from_file(rel)
        if derived_route:
            route_files.append({"path": rel, "route": derived_route})
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            strings = STRING_RE.findall(line)
            if not strings:
                continue
            method = infer_method(line)
            for raw in strings:
                api_path = normalize_path(raw)
                if not api_path.startswith("/api") and "/api/" not in api_path:
                    continue
                key = source_key(method, api_path)
                entry = endpoints.setdefault(
                    key,
                    {
                        "method": method,
                        "path": api_path,
                        "kind": classify_api_hint(method, api_path, line),
                        "count": 0,
                        "locations": [],
                    },
                )
                if entry["kind"] == "base" and classify_api_hint(method, api_path, line) == "endpoint":
                    entry["kind"] = "endpoint"
                entry["count"] += 1
                if len(entry["locations"]) < 20:
                    entry["locations"].append({"path": rel, "line": line_no, "snippet": line.strip()[:240]})

    specific_by_path = {
        endpoint["path"]: key
        for key, endpoint in endpoints.items()
        if endpoint["method"] != "UNKNOWN"
    }
    for key, endpoint in list(endpoints.items()):
        if endpoint["method"] != "UNKNOWN":
            continue
        target_key = specific_by_path.get(endpoint["path"])
        if not target_key:
            continue
        target = endpoints[target_key]
        target["count"] += endpoint["count"]
        target["locations"].extend(endpoint["locations"][: max(0, 20 - len(target["locations"]))])
        del endpoints[key]

    return {
        "generatedFrom": "source_api_map",
        "endpointCount": len(endpoints),
        "endpoints": sorted(endpoints.values(), key=lambda item: (item["path"], item["method"])),
        "routeFiles": route_files[:500],
    }


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def endpoint_keys(payload: dict, source: str) -> dict[str, dict]:
    items = {}
    for endpoint in payload.get("endpoints", []):
        method = (endpoint.get("method") or "UNKNOWN").upper()
        path = endpoint.get("path") or ""
        if not path:
            continue
        if source == "runtime" and method == "UNKNOWN":
            method = "GET"
        items[source_key(method, path)] = endpoint
    return items


def build_coverage(source_map: dict, runtime_map: dict) -> dict:
    source = endpoint_keys(source_map, "source")
    runtime = endpoint_keys(runtime_map, "runtime")
    all_keys = sorted(set(source) | set(runtime))
    rows = []
    for key in all_keys:
        method, api_path = key.split(" ", 1)
        rows.append(
            {
                "method": method,
                "path": api_path,
                "sourceSeen": key in source,
                "runtimeSeen": key in runtime,
                "kind": source.get(key, {}).get("kind") or runtime.get(key, {}).get("kind") or "endpoint",
                "sourceCount": source.get(key, {}).get("count", 0),
                "runtimeCount": runtime.get(key, {}).get("count", 0),
                "runtimeStatuses": runtime.get(key, {}).get("statuses", {}),
                "sourceLocations": source.get(key, {}).get("locations", [])[:5],
            }
        )
    summary = defaultdict(int)
    for row in rows:
        if row["sourceSeen"] and row["runtimeSeen"]:
            summary["both"] += 1
        elif row["sourceSeen"]:
            summary["source_only"] += 1
        elif row["runtimeSeen"]:
            summary["runtime_only"] += 1
    return {
        "generatedFrom": "source_api_map+passive_crawl",
        "summary": dict(summary),
        "endpointCount": len(rows),
        "endpoints": rows,
    }


def render_source_map(payload: dict) -> str:
    lines = ["# Source API Map", "", f"- Endpoints discovered: {payload.get('endpointCount', 0)}", f"- Route files discovered: {len(payload.get('routeFiles', []))}", ""]
    for endpoint in payload.get("endpoints", [])[:100]:
        lines.append(f"## {endpoint.get('method')} {endpoint.get('path')}")
        lines.append(f"- Kind: {endpoint.get('kind', 'endpoint')}")
        lines.append(f"- Source hits: {endpoint.get('count', 0)}")
        for location in endpoint.get("locations", [])[:5]:
            lines.append(f"- `{location['path']}:{location['line']}` {location['snippet']}")
        lines.append("")
    return "\n".join(lines)


def render_coverage(payload: dict) -> str:
    summary = payload.get("summary", {})
    lines = [
        "# API Coverage",
        "",
        f"- Total endpoints: {payload.get('endpointCount', 0)}",
        f"- Source and runtime: {summary.get('both', 0)}",
        f"- Source only: {summary.get('source_only', 0)}",
        f"- Runtime only: {summary.get('runtime_only', 0)}",
        "",
    ]
    for label, predicate in (
        ("Source Only", lambda row: row["sourceSeen"] and not row["runtimeSeen"]),
        ("Runtime Only", lambda row: row["runtimeSeen"] and not row["sourceSeen"]),
        ("Source And Runtime", lambda row: row["sourceSeen"] and row["runtimeSeen"]),
    ):
        lines.append(f"## {label}")
        matches = [row for row in payload.get("endpoints", []) if predicate(row)]
        if not matches:
            lines.append("- None")
        for row in matches[:100]:
            statuses = ", ".join(f"{key}={value}" for key, value in row.get("runtimeStatuses", {}).items())
            lines.append(f"- `{row['method']} {row['path']}` source={row['sourceCount']} runtime={row['runtimeCount']} statuses={statuses}")
        lines.append("")
    return "\n".join(lines)


def update_manifest(workspace: Path) -> None:
    manifest_path = workspace / "state" / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.setdefault("stages", {})["source_api_map"] = "completed"
    manifest.setdefault("stages", {})["api_coverage"] = "completed"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate source API map and optional runtime coverage.")
    parser.add_argument("--repo", required=True, help="Repository path")
    parser.add_argument("--workspace", required=True, help="Audit workspace")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    if not repo.exists():
        raise SystemExit(f"Repository path does not exist: {repo}")

    state = workspace / "state"
    evidence = workspace / "evidence"
    state.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)

    source_map = scan_repo(repo)
    runtime_map = read_json(state / "api_map.json")
    coverage = build_coverage(source_map, runtime_map)

    (state / "source_api_map.json").write_text(json.dumps(source_map, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (state / "api_coverage.json").write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (evidence / "source_api_map.md").write_text(render_source_map(source_map), encoding="utf-8")
    (evidence / "api_coverage.md").write_text(render_coverage(coverage), encoding="utf-8")
    update_manifest(workspace)

    print(json.dumps({"sourceEndpoints": source_map["endpointCount"], "coverageEndpoints": coverage["endpointCount"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
