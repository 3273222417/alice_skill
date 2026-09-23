#!/usr/bin/env python3
"""Detect backend frameworks, server entrypoints, and data-layer hints."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from backend_common import ensure_workspace, iter_source_files, location, read_text, safe_snippet, update_manifest, write_json

DEPENDENCY_HINTS = {
    "@nestjs/core": ("NestJS", "node"),
    "@nestjs/common": ("NestJS", "node"),
    "@remix-run/node": ("Remix", "node"),
    "@trpc/server": ("tRPC", "node"),
    "apollo-server": ("Apollo Server", "node"),
    "apollo-server-express": ("Apollo Server", "node"),
    "django": ("Django", "python"),
    "express": ("Express", "node"),
    "fastapi": ("FastAPI", "python"),
    "fastify": ("Fastify", "node"),
    "flask": ("Flask", "python"),
    "gin-gonic/gin": ("Gin", "go"),
    "graphql": ("GraphQL", "node"),
    "gorm.io/gorm": ("GORM", "go"),
    "koa": ("Koa", "node"),
    "laravel/framework": ("Laravel", "php"),
    "labstack/echo": ("Echo", "go"),
    "mongoose": ("Mongoose", "node"),
    "next": ("Next.js", "node"),
    "prisma": ("Prisma", "node"),
    "rails": ("Rails", "ruby"),
    "sequelize": ("Sequelize", "node"),
    "sinatra": ("Sinatra", "ruby"),
    "spring-boot-starter-web": ("Spring Boot", "java"),
    "spring-boot-starter-security": ("Spring Security", "java"),
    "sqlalchemy": ("SQLAlchemy", "python"),
    "starlette": ("Starlette", "python"),
    "typeorm": ("TypeORM", "node"),
}

CODE_HINTS = {
    "Express": re.compile(r"\bexpress\s*\(|\bapp\.(?:get|post|put|patch|delete)\s*\(", re.I),
    "Fastify": re.compile(r"\bfastify\s*\(|\bfastify\.(?:get|post|route)\s*\(", re.I),
    "NestJS": re.compile(r"\bNestFactory\b|@Controller\s*\(|@Injectable\s*\(", re.I),
    "Next.js": re.compile(r"\bNextRequest\b|NextResponse|export\s+async\s+function\s+(?:GET|POST|PUT|PATCH|DELETE)\b"),
    "FastAPI": re.compile(r"\bFastAPI\s*\(|@(?:app|router)\.(?:get|post|put|patch|delete)\s*\(", re.I),
    "Flask": re.compile(r"\bFlask\s*\(|@app\.route\s*\(", re.I),
    "Django": re.compile(r"\burlpatterns\b|django\.urls|settings\.py\b", re.I),
    "Spring Boot": re.compile(r"@SpringBootApplication|@RestController|@RequestMapping", re.I),
    "Gin": re.compile(r"\bgin\.Default\s*\(|\bgin\.New\s*\(", re.I),
    "Rails": re.compile(r"Rails\.application\.routes|ApplicationController", re.I),
    "Laravel": re.compile(r"Route::(?:get|post|put|patch|delete|middleware)\s*\(", re.I),
}

ENTRYPOINT_RE = re.compile(
    r"\b(listen\s*\(|createServer\s*\(|NestFactory|FastAPI\s*\(|Flask\s*\(|SpringApplication\.run|gin\.Default\s*\(|Rails\.application|RouteServiceProvider)",
    re.I,
)

ORM_HINT_RE = re.compile(
    r"\b(PrismaClient|mongoose|sequelize|TypeORM|DataSource|SQLAlchemy|SessionLocal|EntityManager|Repository<|GORM|ActiveRecord|Eloquent|Dapper|DbContext)\b",
    re.I,
)

SECURITY_MIDDLEWARE_RE = re.compile(
    r"\b(helmet|cors|csrf|csurf|passport|jwt|session|cookie|Guard|AuthGuard|PreAuthorize|Authorize|authentication|authorization)\b",
    re.I,
)

CONFIG_FILE_RE = re.compile(r"(^|/)(\.env|config|settings|application|docker-compose|Dockerfile|nginx|apache|k8s|helm)", re.I)


def dependency_candidates(path: Path, text: str) -> list[tuple[str, str, str]]:
    hits = []
    lower = text.lower()
    for token, (name, ecosystem) in DEPENDENCY_HINTS.items():
        if token.lower() in lower:
            hits.append((name, ecosystem, token))
    return hits


def confidence(signal_count: int, dependency_seen: bool) -> float:
    base = 0.7 if dependency_seen else 0.45
    return round(min(0.97, base + (signal_count * 0.08)), 2)


def scan_repo(repo: Path, hints: list[str]) -> dict:
    frameworks: dict[str, dict] = {}
    dependencies: list[dict] = []
    entrypoints: list[dict] = []
    orm_hints: list[dict] = []
    security_hints: list[dict] = []
    config_files: list[str] = []

    for raw_hint in hints:
        hint = raw_hint.strip()
        if not hint:
            continue
        frameworks[hint] = {
            "name": hint,
            "ecosystem": "hint",
            "confidence": 0.8,
            "evidence": [{"path": "<config>", "line": 0, "snippet": "configured framework hint"}],
            "signalCount": 1,
            "dependencySeen": False,
        }

    for rel, path in iter_source_files(repo):
        text = read_text(path)
        if not text:
            continue
        if CONFIG_FILE_RE.search(rel):
            config_files.append(rel)

        for framework_name, ecosystem, token in dependency_candidates(path, text):
            entry = frameworks.setdefault(
                framework_name,
                {
                    "name": framework_name,
                    "ecosystem": ecosystem,
                    "confidence": 0.0,
                    "evidence": [],
                    "signalCount": 0,
                    "dependencySeen": False,
                },
            )
            entry["dependencySeen"] = True
            entry["signalCount"] += 2
            if len(entry["evidence"]) < 12:
                entry["evidence"].append({"path": rel, "line": 0, "snippet": f"dependency: {token}"})
            dependencies.append({"name": token, "framework": framework_name, "ecosystem": ecosystem, "path": rel})

        lines = text.splitlines()
        for line_no, line in enumerate(lines, start=1):
            for framework_name, pattern in CODE_HINTS.items():
                if not pattern.search(line):
                    continue
                entry = frameworks.setdefault(
                    framework_name,
                    {
                        "name": framework_name,
                        "ecosystem": "unknown",
                        "confidence": 0.0,
                        "evidence": [],
                        "signalCount": 0,
                        "dependencySeen": False,
                    },
                )
                entry["signalCount"] += 1
                if len(entry["evidence"]) < 12:
                    entry["evidence"].append(location(rel, line_no, line))
            if ENTRYPOINT_RE.search(line):
                entrypoints.append(location(rel, line_no, line))
            if ORM_HINT_RE.search(line):
                orm_hints.append(location(rel, line_no, line))
            if SECURITY_MIDDLEWARE_RE.search(line):
                security_hints.append(location(rel, line_no, line))

    by_dependency = defaultdict(bool)
    for dep in dependencies:
        by_dependency[dep["framework"]] = True

    normalized = []
    for name, entry in frameworks.items():
        entry["confidence"] = confidence(entry["signalCount"], bool(entry.get("dependencySeen") or by_dependency[name]))
        entry.pop("dependencySeen", None)
        entry.pop("signalCount", None)
        normalized.append(entry)

    return {
        "repo": str(repo),
        "frameworks": sorted(normalized, key=lambda item: (-item["confidence"], item["name"])),
        "dependencies": dependencies[:300],
        "entrypoints": entrypoints[:100],
        "ormHints": orm_hints[:150],
        "securityMiddlewareHints": security_hints[:150],
        "configFiles": sorted(set(config_files))[:300],
    }


def render_markdown(payload: dict) -> str:
    lines = ["# Backend Framework Fingerprint", "", f"- Repository: `{payload.get('repo', '')}`", ""]
    lines.append("## Frameworks")
    if not payload.get("frameworks"):
        lines.append("- No backend framework signal found.")
    for item in payload.get("frameworks", []):
        lines.append(f"- **{item['name']}** confidence={item['confidence']} ecosystem={item.get('ecosystem', 'unknown')}")
        for evidence in item.get("evidence", [])[:5]:
            suffix = f":{evidence['line']}" if evidence.get("line") else ""
            lines.append(f"  - `{evidence['path']}{suffix}` {safe_snippet(evidence.get('snippet', ''))}")

    for title, key in (
        ("Entrypoints", "entrypoints"),
        ("Data Layer Hints", "ormHints"),
        ("Security Middleware Hints", "securityMiddlewareHints"),
    ):
        lines.extend(["", f"## {title}"])
        values = payload.get(key, [])
        if not values:
            lines.append("- None found.")
        for item in values[:50]:
            lines.append(f"- `{item['path']}:{item['line']}` {item['snippet']}")
    lines.extend(["", "## Configuration Files"])
    if not payload.get("configFiles"):
        lines.append("- None found.")
    for item in payload.get("configFiles", [])[:100]:
        lines.append(f"- `{item}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect backend frameworks and related server-side assets.")
    parser.add_argument("--repo", required=True, help="Repository path")
    parser.add_argument("--workspace", required=True, help="Audit workspace")
    parser.add_argument("--hints", default="", help="Comma-separated framework hints from config")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    if not repo.exists():
        raise SystemExit(f"Repository path does not exist: {repo}")

    state, evidence = ensure_workspace(workspace)
    payload = scan_repo(repo, [item for item in args.hints.split(",") if item.strip()])
    write_json(state / "backend_fingerprint.json", payload)
    (evidence / "backend_fingerprint.md").write_text(render_markdown(payload), encoding="utf-8")
    update_manifest(workspace, "backend_fingerprint")
    print(json.dumps({"frameworks": len(payload["frameworks"]), "entrypoints": len(payload["entrypoints"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
