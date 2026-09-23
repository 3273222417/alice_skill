#!/usr/bin/env python3
"""Generate a static attack-surface inventory for a repository."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

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
    ".css",
    ".env",
    ".go",
    ".graphql",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".rb",
    ".rs",
    ".sql",
    ".ts",
    ".tsx",
    ".vue",
    ".yaml",
    ".yml",
}

PATTERNS = {
    "auth_session": re.compile(r"\b(auth|login|logout|session|jwt|token|cookie|oauth|sso)\b", re.I),
    "access_control": re.compile(r"\b(role|permission|admin|tenant|organization|owner|policy|guard)\b", re.I),
    "api_client": re.compile(r"\b(fetch|axios|XMLHttpRequest|baseURL|endpoint|api)\b", re.I),
    "xss_dom": re.compile(r"(dangerouslySetInnerHTML|innerHTML|outerHTML|eval\(|new Function|document\.write|postMessage)", re.I),
    "redirect_url": re.compile(r"\b(redirect|callback|returnUrl|return_url|next=|url=|window\.location|location\.href)\b", re.I),
    "secret_like": re.compile(r"\b(API_KEY|SECRET|TOKEN|PASSWORD|PRIVATE_KEY|ACCESS_KEY|VITE_|NEXT_PUBLIC_|REACT_APP_)\b", re.I),
    "ssrf_fetcher": re.compile(r"\b(webhook|proxy|fetchUrl|fetch_url|remoteUrl|remote_url|importUrl|previewUrl|urlToFetch)\b", re.I),
    "file_handling": re.compile(r"\b(upload|download|multipart|file|blob|objectURL|createObjectURL|mime)\b", re.I),
}


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def is_text_file(path: Path) -> bool:
    if path.name in {".env", ".env.example", ".npmrc"}:
        return True
    return path.suffix.lower() in TEXT_EXTENSIONS


def redact_snippet(kind: str, line: str) -> str:
    snippet = line.strip()
    if len(snippet) > 220:
        snippet = snippet[:217] + "..."
    if kind == "secret_like":
        snippet = re.sub(r"([A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD)[A-Z0-9_]*\s*[:=]\s*)(['\"]?)[^'\"\s]+", r"\1\2<redacted>", snippet, flags=re.I)
    return snippet


def classify_file(path: Path, rel: str) -> list[str]:
    labels: list[str] = []
    lower = rel.lower()
    name = path.name.lower()
    if name == "package.json" or name.endswith("lock.json") or name in {"pnpm-lock.yaml", "yarn.lock", "package-lock.json"}:
        labels.append("dependency_manifest")
    if "route" in lower or "router" in lower or "pages/" in lower or "app/" in lower:
        labels.append("route_surface")
    if any(token in lower for token in ("auth", "session", "login", "oauth", "permission", "guard")):
        labels.append("auth_surface")
    if any(token in lower for token in ("api", "client", "service", "request")):
        labels.append("api_surface")
    if name.startswith(".env") or "config" in lower:
        labels.append("configuration")
    if any(token in lower for token in ("upload", "download", "file", "blob")):
        labels.append("file_surface")
    return labels


def scan_repo(repo: Path) -> dict:
    files: list[dict] = []
    findings: dict[str, list[dict]] = defaultdict(list)
    labels: dict[str, list[str]] = defaultdict(list)

    for path in sorted(repo.rglob("*")):
        if should_skip(path.relative_to(repo)):
            continue
        if not path.is_file():
            continue
        rel = path.relative_to(repo).as_posix()
        file_labels = classify_file(path, rel)
        files.append({"path": rel, "labels": file_labels})
        for label in file_labels:
            labels[label].append(rel)

        if not is_text_file(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings[kind].append(
                        {
                            "path": rel,
                            "line": line_no,
                            "snippet": redact_snippet(kind, line),
                        }
                    )

    return {
        "repo": str(repo),
        "file_count": len(files),
        "labels": dict(sorted(labels.items())),
        "pattern_matches": {key: value[:200] for key, value in sorted(findings.items())},
        "truncated_match_limit_per_kind": 200,
    }


def render_markdown(payload: dict) -> str:
    lines = ["# Attack Surface Inventory", "", f"- Repository: {payload['repo']}", f"- Files scanned: {payload['file_count']}", ""]
    lines.append("## Surfaces")
    for label, paths in payload["labels"].items():
        lines.append(f"\n### {label}")
        for path in paths[:50]:
            lines.append(f"- `{path}`")
        if len(paths) > 50:
            lines.append(f"- ... {len(paths) - 50} more")

    lines.append("\n## Pattern Matches")
    for kind, matches in payload["pattern_matches"].items():
        lines.append(f"\n### {kind}")
        for match in matches[:50]:
            lines.append(f"- `{match['path']}:{match['line']}` {match['snippet']}")
        if len(matches) > 50:
            lines.append(f"- ... {len(matches) - 50} more")
    lines.append("")
    return "\n".join(lines)


def update_manifest(workspace: Path) -> None:
    manifest_path = workspace / "state" / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.setdefault("stages", {})["inventory"] = "completed"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a static attack-surface inventory.")
    parser.add_argument("--repo", required=True, help="Repository path")
    parser.add_argument("--workspace", default="", help="Audit workspace created by create_audit_workspace.py")
    parser.add_argument("--json-out", default="", help="Optional JSON output path")
    parser.add_argument("--md-out", default="", help="Optional Markdown output path")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.exists():
        raise SystemExit(f"Repository path does not exist: {repo}")

    workspace = Path(args.workspace).expanduser().resolve() if args.workspace else None
    payload = scan_repo(repo)

    json_out = Path(args.json_out).expanduser().resolve() if args.json_out else (workspace / "state" / "attack_surface.json" if workspace else None)
    md_out = Path(args.md_out).expanduser().resolve() if args.md_out else (workspace / "01-inventory.md" if workspace else None)

    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if md_out:
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(render_markdown(payload), encoding="utf-8")
    if workspace:
        update_manifest(workspace)

    print(json.dumps({"json": str(json_out) if json_out else "", "markdown": str(md_out) if md_out else ""}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
