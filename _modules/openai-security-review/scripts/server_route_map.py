#!/usr/bin/env python3
"""Build a heuristic server route and middleware map."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from backend_common import ensure_workspace, is_server_candidate, iter_source_files, location, normalize_route_path, read_text, route_risk_tags, safe_snippet, update_manifest, write_json

ROUTE_FILE_EXTENSIONS = {".cs", ".go", ".java", ".js", ".jsx", ".kt", ".mjs", ".php", ".py", ".rb", ".ts", ".tsx"}

EXPRESS_ROUTE_RE = re.compile(r"\b(?:app|router|route|fastify|server)\s*\.\s*(get|post|put|patch|delete|head|options|all)\s*\(\s*([`'\"])(.*?)\2", re.I)
EXPRESS_CHAIN_RE = re.compile(r"\.route\s*\(\s*([`'\"])(.*?)\1\s*\)\s*\.\s*(get|post|put|patch|delete|head|options|all)\s*\(", re.I)
FASTIFY_ROUTE_RE = re.compile(r"\.route\s*\(\s*\{[^}\n]*(?:method\s*:\s*([`'\"])(.*?)\1)[^}\n]*(?:url\s*:\s*([`'\"])(.*?)\3)", re.I)
NEXT_HANDLER_RE = re.compile(r"export\s+async\s+function\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b")
NEST_CONTROLLER_RE = re.compile(r"@Controller\s*\(\s*(?:([`'\"])(.*?)\1)?\s*\)")
NEST_ROUTE_RE = re.compile(r"@(Get|Post|Put|Patch|Delete|Head|Options|All)\s*\(\s*(?:([`'\"])(.*?)\2)?\s*\)")

PY_DECORATOR_RE = re.compile(r"@\w+\.(get|post|put|patch|delete|head|options|route)\s*\(\s*([`'\"])(.*?)\2(.*)", re.I)
DJANGO_PATH_RE = re.compile(r"\b(?:path|re_path)\s*\(\s*([`'\"])(.*?)\1", re.I)

SPRING_CLASS_RE = re.compile(r"@(?:RequestMapping)\s*\((.*?)\)")
SPRING_ROUTE_RE = re.compile(r"@(GetMapping|PostMapping|PutMapping|PatchMapping|DeleteMapping|RequestMapping)\s*\((.*?)\)")

GO_ROUTE_RE = re.compile(r"\b(?:r|router|engine|group|e)\.(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|Any|Handle|HandleFunc)\s*\(\s*\"([^\"]+)\"", re.I)
GO_HTTP_RE = re.compile(r"\bhttp\.HandleFunc\s*\(\s*\"([^\"]+)\"", re.I)

RUBY_ROUTE_RE = re.compile(r"^\s*(get|post|put|patch|delete|head|options)\s+['\"]([^'\"]+)['\"]", re.I)
PHP_ROUTE_RE = re.compile(r"\bRoute::(get|post|put|patch|delete|options|any|match)\s*\(\s*['\"]([^'\"]+)['\"]", re.I)
CS_ROUTE_RE = re.compile(r"\bMap(Get|Post|Put|Patch|Delete|Methods)\s*\(\s*\"([^\"]+)\"", re.I)

AUTH_RE = re.compile(r"\b(auth|authenticated|authorize|authorization|permission|policy|guard|role|tenant|owner|scope|jwt|session|passport|middleware)\b", re.I)
AUTHZ_RE = re.compile(r"\b(role|permission|policy|tenant|owner|scope|can\(|authorize|PreAuthorize|RequireAuthorization|RolesAllowed|ability)\b", re.I)
VALIDATION_RE = re.compile(r"\b(zod|joi|yup|class-validator|class\s+\w+Dto|DTO|pydantic|BaseModel|serializer|validate|validation|schema|FormRequest|RequestBody)\b", re.I)
MIDDLEWARE_RE = re.compile(r"\b(middleware|use\(|before_action|Depends\(|Guard|Interceptor|filter|handler|csrf|cors|helmet)\b", re.I)


def quoted_value(args: str) -> str:
    match = re.search(r"(?:value|path)\s*=\s*([`'\"])(.*?)\1", args)
    if match:
        return match.group(2)
    match = re.search(r"([`'\"])(.*?)\1", args)
    return match.group(2) if match else ""


def spring_methods(kind: str, args: str) -> list[str]:
    kind_map = {
        "GetMapping": ["GET"],
        "PostMapping": ["POST"],
        "PutMapping": ["PUT"],
        "PatchMapping": ["PATCH"],
        "DeleteMapping": ["DELETE"],
    }
    if kind in kind_map:
        return kind_map[kind]
    matches = re.findall(r"RequestMethod\.([A-Z]+)", args)
    return matches or ["UNKNOWN"]


def decorator_methods(method: str, rest: str) -> list[str]:
    if method.lower() != "route":
        return [method.upper()]
    matches = re.findall(r"['\"](GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)['\"]", rest, re.I)
    return [item.upper() for item in matches] or ["UNKNOWN"]


def next_route_from_file(rel: str) -> str:
    if "/app/" not in f"/{rel}" or not rel.endswith((".js", ".jsx", ".ts", ".tsx")):
        return ""
    parts = rel.split("/")
    if "app" not in parts:
        return ""
    app_index = parts.index("app")
    route_parts = parts[app_index + 1 :]
    if not route_parts or not re.fullmatch(r"route\.(?:js|jsx|ts|tsx)", route_parts[-1]):
        return ""
    cleaned = [part for part in route_parts[:-1] if not part.startswith("(")]
    normalized = []
    for part in cleaned:
        if part.startswith("[") and part.endswith("]"):
            normalized.append(":" + part.strip("[]").replace("...", ""))
        else:
            normalized.append(part)
    return "/" + "/".join(normalized) if normalized else "/"


def nearest_base(line_no: int, bases: list[tuple[int, str]]) -> str:
    selected = ""
    for base_line, base in bases:
        if base_line <= line_no:
            selected = base
        else:
            break
    return selected


def context_signals(lines: list[str], index: int) -> tuple[list[str], list[str], list[str]]:
    start = max(0, index - 8)
    end = min(len(lines), index + 12)
    context = "\n".join(lines[start:end])
    auth = sorted(set(match.group(0) for match in AUTH_RE.finditer(context)))[:12]
    authz = sorted(set(match.group(0) for match in AUTHZ_RE.finditer(context)))[:12]
    validation = sorted(set(match.group(0) for match in VALIDATION_RE.finditer(context)))[:12]
    middleware = sorted(set(match.group(0) for match in MIDDLEWARE_RE.finditer(context)))[:12]
    return auth + authz, validation, middleware


def add_route(routes: list[dict], rel: str, line_no: int, line: str, method: str, path_value: str, framework: str, base: str = "") -> None:
    path = normalize_route_path(path_value, base)
    routes.append(
        {
            "method": method.upper(),
            "path": path,
            "file": rel,
            "line": line_no,
            "frameworkHint": framework,
            "snippet": safe_snippet(line),
            "riskTags": route_risk_tags(method, path),
            "authSignals": [],
            "validationSignals": [],
            "middlewareSignals": [],
        }
    )


def scan_file(rel: str, text: str) -> list[dict]:
    routes: list[dict] = []
    lines = text.splitlines()
    suffix = Path(rel).suffix.lower()
    is_js_server = suffix in {".cjs", ".js", ".mjs", ".ts"}
    is_python = suffix == ".py"
    is_java = suffix in {".java", ".kt"}
    is_go = suffix == ".go"
    is_ruby = suffix == ".rb"
    is_php = suffix == ".php"
    is_dotnet = suffix == ".cs"
    nest_bases = [(i, match.group(2) or "") for i, line in enumerate(lines, start=1) if (match := NEST_CONTROLLER_RE.search(line))]
    spring_bases = [(i, quoted_value(match.group(1))) for i, line in enumerate(lines, start=1) if (match := SPRING_CLASS_RE.search(line))]
    next_path = next_route_from_file(rel)

    for index, line in enumerate(lines):
        line_no = index + 1
        if is_js_server:
            for match in EXPRESS_ROUTE_RE.finditer(line):
                add_route(routes, rel, line_no, line, match.group(1), match.group(3), "express/fastify")
            for match in EXPRESS_CHAIN_RE.finditer(line):
                add_route(routes, rel, line_no, line, match.group(3), match.group(2), "express")
            for match in FASTIFY_ROUTE_RE.finditer(line):
                add_route(routes, rel, line_no, line, match.group(2), match.group(4), "fastify")
        if next_path and (match := NEXT_HANDLER_RE.search(line)):
            add_route(routes, rel, line_no, line, match.group(1), next_path, "next")
        if is_js_server and (match := NEST_ROUTE_RE.search(line)):
            method = match.group(1).upper().replace("ALL", "UNKNOWN")
            add_route(routes, rel, line_no, line, method, match.group(3) or "", "nestjs", nearest_base(line_no, nest_bases))
        if is_python and (match := PY_DECORATOR_RE.search(line)):
            for method in decorator_methods(match.group(1), match.group(4)):
                add_route(routes, rel, line_no, line, method, match.group(3), "python")
        if is_python and (match := DJANGO_PATH_RE.search(line)):
            add_route(routes, rel, line_no, line, "UNKNOWN", match.group(2), "django")
        if is_java and (match := SPRING_ROUTE_RE.search(line)):
            path_value = quoted_value(match.group(2))
            for method in spring_methods(match.group(1), match.group(2)):
                add_route(routes, rel, line_no, line, method, path_value, "spring", nearest_base(line_no, spring_bases))
        if is_go and (match := GO_ROUTE_RE.search(line)):
            method = "UNKNOWN" if match.group(1).lower() in {"any", "handle", "handlefunc"} else match.group(1)
            add_route(routes, rel, line_no, line, method, match.group(2), "go")
        if is_go and (match := GO_HTTP_RE.search(line)):
            add_route(routes, rel, line_no, line, "UNKNOWN", match.group(1), "go")
        if is_ruby and (match := RUBY_ROUTE_RE.search(line)):
            add_route(routes, rel, line_no, line, match.group(1), match.group(2), "ruby")
        if is_php and (match := PHP_ROUTE_RE.search(line)):
            method = "UNKNOWN" if match.group(1).lower() in {"any", "match"} else match.group(1)
            add_route(routes, rel, line_no, line, method, match.group(2), "laravel")
        if is_dotnet and (match := CS_ROUTE_RE.search(line)):
            method = "UNKNOWN" if match.group(1).lower() == "methods" else match.group(1)
            add_route(routes, rel, line_no, line, method, match.group(2), "dotnet")

    for route in routes:
        index = max(0, int(route["line"]) - 1)
        auth, validation, middleware = context_signals(lines, index)
        route["authSignals"] = auth
        route["validationSignals"] = validation
        route["middlewareSignals"] = middleware
    return routes


def scan_repo(repo: Path) -> dict:
    routes: list[dict] = []
    route_files: set[str] = set()
    for rel, path in iter_source_files(repo, ROUTE_FILE_EXTENSIONS):
        text = read_text(path)
        if not text:
            continue
        if not is_server_candidate(rel, path, text) and not next_route_from_file(rel):
            continue
        file_routes = scan_file(rel, text)
        if file_routes:
            route_files.add(rel)
            routes.extend(file_routes)

    deduped = []
    seen = set()
    for route in routes:
        key = (route["method"], route["path"], route["file"], route["line"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(route)

    by_method = Counter(route["method"] for route in deduped)
    by_framework = Counter(route["frameworkHint"] for route in deduped)
    return {
        "repo": str(repo),
        "routeCount": len(deduped),
        "routeFiles": sorted(route_files),
        "summary": {"byMethod": dict(sorted(by_method.items())), "byFramework": dict(sorted(by_framework.items()))},
        "routes": sorted(deduped, key=lambda item: (item["path"], item["method"], item["file"], item["line"])),
    }


def render_markdown(payload: dict) -> str:
    lines = ["# Server Route Map", "", f"- Routes discovered: {payload.get('routeCount', 0)}", ""]
    lines.append("## Method Summary")
    for method, count in payload.get("summary", {}).get("byMethod", {}).items():
        lines.append(f"- {method}: {count}")
    lines.extend(["", "## Routes"])
    if not payload.get("routes"):
        lines.append("- No server routes detected.")
    for route in payload.get("routes", [])[:250]:
        signals = []
        if route.get("authSignals"):
            signals.append("auth")
        if route.get("validationSignals"):
            signals.append("validation")
        if route.get("middlewareSignals"):
            signals.append("middleware")
        signal_text = ", ".join(signals) or "no local signal"
        lines.append(f"- `{route['method']} {route['path']}` {route['frameworkHint']} `{route['file']}:{route['line']}` tags={','.join(route.get('riskTags', [])) or '-'} signals={signal_text}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a heuristic server route map.")
    parser.add_argument("--repo", required=True, help="Repository path")
    parser.add_argument("--workspace", required=True, help="Audit workspace")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    if not repo.exists():
        raise SystemExit(f"Repository path does not exist: {repo}")
    state, evidence = ensure_workspace(workspace)
    payload = scan_repo(repo)
    write_json(state / "server_route_map.json", payload)
    (evidence / "server_route_map.md").write_text(render_markdown(payload), encoding="utf-8")
    update_manifest(workspace, "server_route_map")
    print(json.dumps({"routes": payload["routeCount"], "files": len(payload["routeFiles"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
