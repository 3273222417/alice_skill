#!/usr/bin/env python3
"""Extract OpenAPI/Swagger/GraphQL contract hints and compare them with discovered routes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from backend_common import ensure_workspace, iter_source_files, normalize_route_path, read_json, read_text, safe_snippet, update_manifest, write_json

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
SPEC_NAME_RE = re.compile(r"(openapi|swagger|api-docs|schema\.graphql|\.graphql$)", re.I)
GRAPHQL_TYPE_RE = re.compile(r"^\s*type\s+(Query|Mutation)\s*\{", re.I)
GRAPHQL_FIELD_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^)]*\))?\s*:", re.I)


def configured_paths(repo: Path, raw: str) -> list[Path]:
    paths = []
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = repo / path
        if path.exists() and path.is_file():
            paths.append(path.resolve())
    return paths


def discover_specs(repo: Path, configured: str) -> list[Path]:
    found = set(configured_paths(repo, configured))
    for rel, path in iter_source_files(repo):
        if SPEC_NAME_RE.search(rel):
            found.add(path.resolve())
            continue
        text = read_text(path, max_bytes=500_000)
        if not text:
            continue
        if re.search(r"^\s*(openapi|swagger)\s*:", text, re.I | re.M):
            found.add(path.resolve())
    return sorted(found)


def parse_openapi_json(path: Path, text: str) -> list[dict]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    endpoints = []
    for route_path, operations in (payload.get("paths") or {}).items():
        if not isinstance(operations, dict):
            continue
        for method, operation in operations.items():
            if method.lower() not in HTTP_METHODS:
                continue
            endpoints.append(
                {
                    "method": method.upper(),
                    "path": normalize_route_path(route_path),
                    "source": path.as_posix(),
                    "kind": "openapi",
                    "operationId": operation.get("operationId", "") if isinstance(operation, dict) else "",
                    "authSignals": list((operation.get("security") or [])) if isinstance(operation, dict) else [],
                }
            )
    return endpoints


def parse_openapi_yaml(path: Path, text: str) -> list[dict]:
    endpoints = []
    current_path = ""
    in_paths = False
    for line in text.splitlines():
        if re.match(r"^\s*paths\s*:\s*$", line):
            in_paths = True
            continue
        if in_paths and re.match(r"^\S", line) and not line.startswith("paths:"):
            in_paths = False
        if not in_paths:
            continue
        path_match = re.match(r"^\s{2,}(/[^:\s]+)\s*:\s*$", line)
        if path_match:
            current_path = path_match.group(1)
            continue
        method_match = re.match(r"^\s{4,}(get|post|put|patch|delete|head|options|trace)\s*:\s*$", line, re.I)
        if current_path and method_match:
            endpoints.append({"method": method_match.group(1).upper(), "path": normalize_route_path(current_path), "source": path.as_posix(), "kind": "openapi-yaml", "operationId": "", "authSignals": []})
    return endpoints


def parse_graphql(path: Path, text: str) -> list[dict]:
    endpoints = []
    current_type = ""
    for line in text.splitlines():
        if match := GRAPHQL_TYPE_RE.search(line):
            current_type = match.group(1).lower()
            continue
        if current_type and line.strip().startswith("}"):
            current_type = ""
            continue
        if current_type and (match := GRAPHQL_FIELD_RE.search(line)):
            method = "QUERY" if current_type == "query" else "MUTATION"
            endpoints.append({"method": method, "path": f"graphql:{match.group(1)}", "source": path.as_posix(), "kind": "graphql", "operationId": match.group(1), "authSignals": []})
    return endpoints


def parse_spec(path: Path, repo: Path) -> tuple[list[dict], dict]:
    text = read_text(path, max_bytes=1_500_000)
    rel = path.relative_to(repo).as_posix() if path.is_relative_to(repo) else path.as_posix()
    if not text:
        return [], {"path": rel, "type": "unknown", "endpointCount": 0}
    endpoints: list[dict] = []
    spec_type = "unknown"
    if path.suffix.lower() == ".json":
        endpoints = parse_openapi_json(Path(rel), text)
        spec_type = "openapi-json" if endpoints else "json"
    elif path.suffix.lower() in {".yaml", ".yml"} or re.search(r"^\s*(openapi|swagger)\s*:", text, re.I | re.M):
        endpoints = parse_openapi_yaml(Path(rel), text)
        spec_type = "openapi-yaml" if endpoints else "yaml"
    if not endpoints and (path.suffix.lower() == ".graphql" or "type Query" in text or "type Mutation" in text):
        endpoints = parse_graphql(Path(rel), text)
        spec_type = "graphql" if endpoints else spec_type
    return endpoints, {"path": rel, "type": spec_type, "endpointCount": len(endpoints)}


def route_keys(route_map: dict) -> set[str]:
    keys = set()
    for route in route_map.get("routes", []):
        method = (route.get("method") or "UNKNOWN").upper()
        path = route.get("path") or ""
        if not path or method == "UNKNOWN":
            continue
        keys.add(f"{method} {path}")
    return keys


def runtime_keys(api_map: dict) -> set[str]:
    keys = set()
    for endpoint in api_map.get("endpoints", []):
        method = (endpoint.get("method") or "GET").upper()
        path = endpoint.get("path") or ""
        if path:
            keys.add(f"{method} {path}")
    return keys


def build(repo: Path, workspace: Path, spec_paths: str) -> dict:
    specs = []
    endpoints = []
    for path in discover_specs(repo, spec_paths):
        parsed, spec = parse_spec(path, repo)
        specs.append(spec)
        endpoints.extend(parsed)

    spec_keys = {f"{endpoint['method']} {endpoint['path']}" for endpoint in endpoints if endpoint.get("method") not in {"QUERY", "MUTATION"}}
    routes = route_keys(read_json(workspace / "state" / "server_route_map.json"))
    runtime = runtime_keys(read_json(workspace / "state" / "api_map.json"))
    all_keys = sorted(spec_keys | routes | runtime)
    coverage = []
    for key in all_keys:
        method, api_path = key.split(" ", 1)
        coverage.append({"method": method, "path": api_path, "specSeen": key in spec_keys, "sourceRouteSeen": key in routes, "runtimeSeen": key in runtime})
    summary = {
        "specEndpoints": len(spec_keys),
        "sourceRoutes": len(routes),
        "runtimeEndpoints": len(runtime),
        "specOnly": sum(1 for row in coverage if row["specSeen"] and not row["sourceRouteSeen"] and not row["runtimeSeen"]),
        "sourceOnly": sum(1 for row in coverage if row["sourceRouteSeen"] and not row["specSeen"]),
        "runtimeOnly": sum(1 for row in coverage if row["runtimeSeen"] and not row["specSeen"] and not row["sourceRouteSeen"]),
    }
    return {"repo": str(repo), "specs": specs, "endpoints": endpoints, "coverage": coverage, "summary": summary}


def render_markdown(payload: dict) -> str:
    lines = ["# API Spec Map", "", "## Specs"]
    if not payload.get("specs"):
        lines.append("- No OpenAPI/Swagger/GraphQL spec files detected.")
    for spec in payload.get("specs", []):
        lines.append(f"- `{spec['path']}` type={spec['type']} endpoints={spec['endpointCount']}")
    lines.extend(["", "## Coverage"])
    summary = payload.get("summary", {})
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    drift = [row for row in payload.get("coverage", []) if row["sourceRouteSeen"] and not row["specSeen"]]
    if drift:
        lines.extend(["", "### Source Routes Missing From Spec"])
        for row in drift[:100]:
            lines.append(f"- `{row['method']} {row['path']}`")
    graphql = [endpoint for endpoint in payload.get("endpoints", []) if endpoint.get("kind") == "graphql"]
    if graphql:
        lines.extend(["", "## GraphQL Operations"])
        for endpoint in graphql[:100]:
            lines.append(f"- `{endpoint['method']} {endpoint['operationId']}` source=`{endpoint['source']}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract API specs and compare with source/runtime routes.")
    parser.add_argument("--repo", required=True, help="Repository path")
    parser.add_argument("--workspace", required=True, help="Audit workspace")
    parser.add_argument("--spec-paths", default="", help="Comma-separated OpenAPI/Swagger/GraphQL spec paths")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    if not repo.exists():
        raise SystemExit(f"Repository path does not exist: {repo}")
    state, evidence = ensure_workspace(workspace)
    payload = build(repo, workspace, args.spec_paths)
    write_json(state / "api_spec_map.json", payload)
    (evidence / "api_spec_map.md").write_text(render_markdown(payload), encoding="utf-8")
    update_manifest(workspace, "api_spec_map")
    print(json.dumps({"specs": len(payload["specs"]), "endpoints": len(payload["endpoints"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
