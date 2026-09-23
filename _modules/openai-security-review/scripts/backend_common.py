#!/usr/bin/env python3
"""Shared helpers for server-side security review scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

EXCLUDED_DIRS = {
    ".cache",
    ".git",
    ".hg",
    ".next",
    ".svn",
    ".turbo",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}

TEXT_EXTENSIONS = {
    ".cs",
    ".cjs",
    ".go",
    ".graphql",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".mjs",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".sql",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}

MANIFEST_NAMES = {
    "Cargo.toml",
    "Gemfile",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "go.mod",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
}

CONFIG_FILE_RE = re.compile(r"(^|/)(\.env|config|settings|application|docker-compose|Dockerfile|nginx|apache|k8s|helm)", re.I)
SERVER_PATH_RE = re.compile(r"(^|/)(server|backend|routes|controllers|middleware|handlers|functions|lambda|lambdas)(/|$)", re.I)
SERVER_API_PATH_RE = re.compile(r"(^|/)(pages/api|app/.+/route\.(?:js|jsx|ts|tsx)|api)(/|$)", re.I)
CLIENT_API_PATH_RE = re.compile(r"(^|/)src/api(/|$)", re.I)
SERVER_CONTENT_RE = re.compile(
    r"\b(express\s*\(|fastify\s*\(|koa\s*\(|NestFactory|@Controller|NextRequest|NextResponse|export\s+async\s+function\s+(?:GET|POST|PUT|PATCH|DELETE)\b|FastAPI\s*\(|Flask\s*\(|urlpatterns|@RestController|@RequestMapping|gin\.Default|Route::(?:get|post|put|patch|delete))",
    re.I,
)

SECRET_VALUE_RE = re.compile(
    r"((?:api[_-]?key|secret|token|password|private[_-]?key|access[_-]?key)[A-Z0-9_.-]*\s*[:=]\s*)(['\"]?)[^'\"\s,;]+",
    re.I,
)


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS or path.name in MANIFEST_NAMES or path.name.startswith(".env")


def is_config_file(rel: str) -> bool:
    return bool(CONFIG_FILE_RE.search(rel))


def is_server_candidate(rel: str, path: Path, text: str = "") -> bool:
    suffix = path.suffix.lower()
    if is_config_file(rel):
        return False
    if suffix in {".py", ".go", ".java", ".kt", ".rb", ".php", ".cs", ".rs"}:
        return True
    if SERVER_PATH_RE.search(rel):
        return True
    if SERVER_API_PATH_RE.search(rel) and not CLIENT_API_PATH_RE.search(rel):
        return True
    return bool(text and SERVER_CONTENT_RE.search(text))


def iter_source_files(repo: Path, extensions: set[str] | None = None) -> Iterable[tuple[str, Path]]:
    for path in sorted(repo.rglob("*")):
        rel_path = path.relative_to(repo)
        if should_skip(rel_path) or not path.is_file():
            continue
        if extensions is not None and path.suffix.lower() not in extensions and path.name not in MANIFEST_NAMES:
            continue
        if extensions is None and not is_text_file(path):
            continue
        yield rel_path.as_posix(), path


def read_text(path: Path, max_bytes: int = 2_000_000) -> str:
    try:
        if path.stat().st_size > max_bytes:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def safe_snippet(line: str, limit: int = 240) -> str:
    snippet = SECRET_VALUE_RE.sub(r"\1\2<redacted>", line.strip())
    if len(snippet) > limit:
        return snippet[: limit - 3] + "..."
    return snippet


def location(rel: str, line: int, snippet: str) -> dict:
    return {"path": rel, "line": line, "snippet": safe_snippet(snippet)}


def ensure_workspace(workspace: Path) -> tuple[Path, Path]:
    state = workspace / "state"
    evidence = workspace / "evidence"
    state.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    return state, evidence


def update_manifest(workspace: Path, stage: str) -> None:
    manifest_path = workspace / "state" / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = read_json(manifest_path)
    manifest.setdefault("stages", {})[stage] = "completed"
    write_json(manifest_path, manifest)


def normalize_route_path(path_value: str, base: str = "") -> str:
    raw = (path_value or "").strip()
    raw = raw.strip("'\"`")
    if raw in {"", "undefined", "None"}:
        raw = "/"
    raw = re.sub(r"\s+", "", raw)
    if not raw.startswith("/"):
        raw = "/" + raw
    if base:
        clean_base = base.strip().strip("'\"`")
        if clean_base and not clean_base.startswith("/"):
            clean_base = "/" + clean_base
        raw = clean_base.rstrip("/") + raw
    raw = re.sub(r"/{2,}", "/", raw)
    return raw or "/"


def route_risk_tags(method: str, path_value: str) -> list[str]:
    text = f"{method} {path_value}".lower()
    tags = []
    patterns = {
        "admin": r"\badmin|role|permission|policy\b",
        "auth": r"\bauth|login|logout|token|session|oauth|sso\b",
        "tenant": r"\btenant|org|organization|workspace|account\b",
        "user_data": r"\buser|profile|member|customer\b",
        "payment": r"\bbilling|payment|invoice|order|checkout\b",
        "file": r"\bfile|upload|download|export|import|attachment\b",
        "webhook": r"\bwebhook|callback|redirect|return-url|return_url\b",
    }
    for tag, pattern in patterns.items():
        if re.search(pattern, text):
            tags.append(tag)
    if method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        tags.append("mutating")
    return sorted(set(tags))


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    escaped_rows = [[cell.replace("|", "\\|") for cell in row] for row in rows]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in escaped_rows)
    return "\n".join(lines)
