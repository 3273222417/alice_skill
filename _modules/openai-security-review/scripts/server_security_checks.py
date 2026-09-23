#!/usr/bin/env python3
"""Run server-specific static security checks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from backend_common import ensure_workspace, is_config_file, is_server_candidate, iter_source_files, location, read_text, update_manifest, write_json

CHECKS = {
    "cors_wildcard": {
        "severity": "medium",
        "pattern": re.compile(r"(Access-Control-Allow-Origin['\"]?\s*[:,]\s*['\"]\*|origin\s*:\s*['\"]\*|allow_origins\s*=\s*\[[^\]]*['\"]\*|CorsConfiguration\.ALL)", re.I),
        "recommendation": "Confirm wildcard CORS is not combined with credentials and is scoped to public resources.",
    },
    "csrf_disabled": {
        "severity": "medium",
        "pattern": re.compile(r"(csrf\s*\(\)\.disable|csrf\s*:\s*false|CSRF_COOKIE_SECURE\s*=\s*False|protect_from_forgery\s+except:|withoutMiddleware\s*\([^)]*VerifyCsrfToken)", re.I),
        "recommendation": "Confirm browser-session state-changing routes have CSRF protection or same-site token defenses.",
    },
    "insecure_cookie": {
        "severity": "medium",
        "pattern": re.compile(r"(httpOnly\s*:\s*false|secure\s*:\s*false|sameSite\s*:\s*['\"]none['\"]|SESSION_COOKIE_SECURE\s*=\s*False|SESSION_COOKIE_HTTPONLY\s*=\s*False)", re.I),
        "recommendation": "Review cookie flags for Secure, HttpOnly, and SameSite according to session sensitivity.",
    },
    "jwt_weakness": {
        "severity": "high",
        "pattern": re.compile(r"(ignoreExpiration\s*:\s*true|algorithms?\s*:\s*\[[^\]]*['\"]none['\"]|jwt\.decode\s*\(|verify\s*=\s*False|validate_signature\s*=\s*False)", re.I),
        "recommendation": "Avoid unsigned/unchecked JWT handling and enforce issuer, audience, algorithm, and expiration validation.",
    },
    "weak_password_crypto": {
        "severity": "high",
        "pattern": re.compile(r"(createHash\s*\(\s*['\"](?:md5|sha1)['\"]|hashlib\.(?:md5|sha1)\s*\(|MessageDigest\.getInstance\s*\(\s*['\"](?:MD5|SHA-1)['\"]|password\s*==|compareSync\s*\([^)]*password)", re.I),
        "recommendation": "Use password-specific hashing such as Argon2, bcrypt, scrypt, or PBKDF2 with suitable parameters.",
    },
    "debug_error_exposure": {
        "severity": "medium",
        "pattern": re.compile(r"(debug\s*=\s*True|app\.set\s*\(\s*['\"]env['\"]\s*,\s*['\"]development|showStack|stacktrace|exposeStack|display_errors\s*=\s*On)", re.I),
        "recommendation": "Confirm debug and stack trace output is disabled in production-like deployments.",
    },
    "secret_like": {
        "severity": "high",
        "pattern": re.compile(r"\b[A-Z0-9_]*(?:SECRET|API_KEY|PRIVATE_KEY|ACCESS_KEY|TOKEN|PASSWORD)[A-Z0-9_]*\s*[:=]\s*['\"]?[^'\"\s#]{8,}", re.I),
        "recommendation": "Classify secret-like values, remove committed credentials, and rotate any real secrets.",
    },
    "path_traversal": {
        "severity": "medium",
        "pattern": re.compile(r"(sendFile\s*\(|createReadStream\s*\(|readFile\s*\(|writeFile\s*\(|path\.join\s*\(|Path\.Combine\s*\(|open\s*\()[^\n]*(req\.|request\.|params|query|body)", re.I),
        "recommendation": "Confirm user-controlled paths are normalized to an allowlisted storage root.",
    },
    "ssrf_fetcher": {
        "severity": "high",
        "pattern": re.compile(r"(fetch\s*\(|axios\.|requests\.get|http\.Get|RestTemplate|WebClient|curl_exec)[^\n]*(url|uri|webhook|callback|proxy|target|remote)", re.I),
        "recommendation": "Confirm outbound URL fetchers restrict scheme, redirects, DNS rebinding, and private IP ranges.",
    },
    "open_redirect": {
        "severity": "medium",
        "pattern": re.compile(r"(redirect\s*\(|res\.redirect|HttpResponseRedirect|RedirectResponse)[^\n]*(returnUrl|return_url|next|callback|url|req\.|request\.)", re.I),
        "recommendation": "Confirm redirects use same-origin checks or explicit allowlists.",
    },
    "docker_root_user": {
        "severity": "low",
        "pattern": re.compile(r"^FROM\s+.+", re.I | re.M),
        "recommendation": "If this is a runtime image, confirm it switches to a non-root USER and does not bake secrets into layers.",
        "dockerCheck": True,
    },
}


def scan_repo(repo: Path) -> dict:
    signals_by_check: dict[str, list[dict]] = {key: [] for key in CHECKS}
    dockerfiles: dict[str, str] = {}
    manifests = []

    for rel, path in iter_source_files(repo):
        text = read_text(path)
        if not text:
            continue
        if path.name in {"package.json", "requirements.txt", "pyproject.toml", "pom.xml", "build.gradle", "go.mod", "Gemfile", "composer.json"}:
            manifests.append(rel)
        if path.name == "Dockerfile" or rel.endswith("/Dockerfile"):
            dockerfiles[rel] = text
        server_candidate = is_server_candidate(rel, path, text)
        config_candidate = path.name.startswith(".env") or is_config_file(rel)
        for line_no, line in enumerate(text.splitlines(), start=1):
            for key, check in CHECKS.items():
                if check.get("dockerCheck"):
                    if path.name != "Dockerfile":
                        continue
                elif key == "secret_like":
                    if not config_candidate:
                        continue
                elif key == "debug_error_exposure":
                    if not (config_candidate or server_candidate):
                        continue
                elif not server_candidate:
                    continue
                pattern = check["pattern"]
                if not pattern.search(line):
                    continue
                signals_by_check[key].append(location(rel, line_no, line))

    checks = []
    for key, check in CHECKS.items():
        signals = signals_by_check[key]
        status = "signals_found" if signals else "no_signal"
        if check.get("dockerCheck"):
            status = "needs_manual_review" if signals else "not_applicable"
            for rel, text in dockerfiles.items():
                if re.search(r"^\s*USER\s+\S+", text, re.I | re.M):
                    signals_by_check[key] = [signal for signal in signals_by_check[key] if signal["path"] != rel]
                    status = "non_root_user_signal" if not signals_by_check[key] else status
        checks.append(
            {
                "id": key,
                "severity": check["severity"],
                "status": status,
                "signals": signals_by_check[key][:80],
                "signalCount": len(signals_by_check[key]),
                "recommendation": check["recommendation"],
            }
        )

    summary = {}
    for check in checks:
        if check["signalCount"]:
            summary[check["severity"]] = summary.get(check["severity"], 0) + 1
    return {"repo": str(repo), "summary": dict(sorted(summary.items())), "checks": checks, "dependencyManifests": sorted(set(manifests))}


def render_markdown(payload: dict) -> str:
    lines = ["# Server Security Checks", "", "## Summary"]
    if not payload.get("summary"):
        lines.append("- No server-specific static signals found.")
    for severity, count in payload.get("summary", {}).items():
        lines.append(f"- {severity}: {count} check families with signals")
    lines.extend(["", "## Checks"])
    for check in payload.get("checks", []):
        lines.append(f"### {check['id']}")
        lines.append(f"- Severity: {check['severity']}")
        lines.append(f"- Status: {check['status']}")
        lines.append(f"- Recommendation: {check['recommendation']}")
        for signal in check.get("signals", [])[:20]:
            lines.append(f"- `{signal['path']}:{signal['line']}` {signal['snippet']}")
        lines.append("")
    lines.append("## Dependency Manifests")
    for manifest in payload.get("dependencyManifests", []):
        lines.append(f"- `{manifest}`")
    if not payload.get("dependencyManifests"):
        lines.append("- None found.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run server-specific static security checks.")
    parser.add_argument("--repo", required=True, help="Repository path")
    parser.add_argument("--workspace", required=True, help="Audit workspace")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    if not repo.exists():
        raise SystemExit(f"Repository path does not exist: {repo}")
    state, evidence = ensure_workspace(workspace)
    payload = scan_repo(repo)
    write_json(state / "server_security_checks.json", payload)
    (evidence / "server_security_checks.md").write_text(render_markdown(payload), encoding="utf-8")
    update_manifest(workspace, "server_security_checks")
    signal_count = sum(check["signalCount"] for check in payload["checks"])
    print(json.dumps({"checks": len(payload["checks"]), "signals": signal_count}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
