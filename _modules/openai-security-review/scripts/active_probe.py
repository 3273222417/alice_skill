#!/usr/bin/env python3
"""Run guarded, low-risk active probes against an explicitly authorized target."""

from __future__ import annotations

import argparse
import html
import ipaddress
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CLASSES = ("cors", "redirect", "xss", "error", "exposure")
REMOTE_ORIGIN = "https://osr.invalid"
EXPOSURE_PATHS = (
    "/.env",
    "/.env.local",
    "/config.json",
    "/login-config.json",
    "/swagger.json",
    "/openapi.json",
    "/api-docs",
    "/debug",
    "/actuator/health",
    "/server-status",
)
SECRET_PATTERNS = re.compile(r"(api[_-]?key|secret|token|password|private[_-]?key)\s*[:=]", re.I)
STACK_PATTERNS = re.compile(
    r"(Traceback \(most recent call last\)|Exception|TypeError|ReferenceError|stack trace|"
    r"PrismaClient|Sequelize|SQL syntax|at Object\.|at Module\.)",
    re.I,
)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, D401
        return None


def fetch(url: str, method: str = "GET", timeout: int = 10, headers: dict | None = None, follow_redirects: bool = True) -> dict:
    request = urllib.request.Request(
        url,
        method=method,
        headers={"User-Agent": "openai-security-review-active-probe/1.0", **(headers or {})},
    )
    context = ssl.create_default_context()
    handlers = [urllib.request.HTTPSHandler(context=context)]
    if not follow_redirects:
        handlers.append(NoRedirectHandler())
    opener = urllib.request.build_opener(*handlers)
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(400_000) if method != "HEAD" else b""
            return {
                "ok": True,
                "url": response.geturl(),
                "status": response.status,
                "headers": {key.lower(): value for key, value in response.headers.items()},
                "body": body.decode("utf-8", errors="replace"),
            }
    except urllib.error.HTTPError as error:
        body = error.read(200_000) if method != "HEAD" else b""
        return {
            "ok": False,
            "url": url,
            "status": error.code,
            "headers": {key.lower(): value for key, value in error.headers.items()},
            "body": body.decode("utf-8", errors="replace"),
            "error": str(error),
        }
    except Exception as error:  # noqa: BLE001 - command-line diagnostics should keep going.
        return {"ok": False, "url": url, "status": None, "headers": {}, "body": "", "error": str(error)}


def target_origin(target_url: str) -> str:
    parsed = urllib.parse.urlparse(target_url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def target_path(target_url: str, path: str) -> str:
    return urllib.parse.urljoin(target_origin(target_url), path)


def with_query(target_url: str, params: dict[str, str]) -> str:
    parsed = urllib.parse.urlparse(target_url)
    query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    query.update(params)
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query), fragment=""))


def is_local_target(target_url: str) -> bool:
    parsed = urllib.parse.urlparse(target_url)
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "host.docker.internal"} or host.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(host)
        return address.is_loopback or address.is_private or address.is_link_local
    except ValueError:
        return False


def issue(severity: str, kind: str, detail: str, probe: dict) -> dict:
    return {
        "severity": severity,
        "kind": kind,
        "detail": detail,
        "class": probe["class"],
        "method": probe["method"],
        "url": probe["url"],
        "status": probe.get("status"),
    }


def probe_cors(target_url: str, timeout: int) -> tuple[list[dict], list[dict]]:
    headers = {"Origin": REMOTE_ORIGIN, "Access-Control-Request-Method": "GET"}
    response = fetch(target_url, method="OPTIONS", timeout=timeout, headers=headers)
    probe = {
        "class": "cors",
        "method": "OPTIONS",
        "url": target_url,
        "status": response.get("status"),
        "headers": {key: response.get("headers", {}).get(key) for key in ("access-control-allow-origin", "access-control-allow-credentials")},
    }
    issues: list[dict] = []
    acao = (response.get("headers", {}).get("access-control-allow-origin") or "").strip()
    acac = (response.get("headers", {}).get("access-control-allow-credentials") or "").strip().lower()
    if acao == REMOTE_ORIGIN and acac == "true":
        issues.append(issue("high", "cors_arbitrary_origin_with_credentials", "CORS appears to trust an arbitrary Origin with credentials.", probe))
    elif acao == REMOTE_ORIGIN:
        issues.append(issue("medium", "cors_arbitrary_origin", "CORS appears to echo an arbitrary Origin.", probe))
    elif acao == "*":
        issues.append(issue("low", "cors_wildcard_origin", "CORS allows any origin for this probe.", probe))
    return [probe], issues


def probe_redirect(target_url: str, timeout: int) -> tuple[list[dict], list[dict]]:
    probes: list[dict] = []
    issues: list[dict] = []
    external = f"{REMOTE_ORIGIN}/redirect-probe"
    target_host = urllib.parse.urlparse(target_url).netloc
    for param in ("next", "url", "redirect", "returnUrl", "callback"):
        url = with_query(target_url, {param: external})
        response = fetch(url, method="GET", timeout=timeout, follow_redirects=False)
        location = response.get("headers", {}).get("location", "")
        probe = {"class": "redirect", "method": "GET", "url": url, "status": response.get("status"), "location": location}
        probes.append(probe)
        if response.get("status") in {301, 302, 303, 307, 308} and location:
            parsed_location = urllib.parse.urlparse(urllib.parse.urljoin(target_url, location))
            if parsed_location.netloc and parsed_location.netloc != target_host:
                issues.append(issue("high", "possible_open_redirect", f"`{param}` redirected to external origin `{parsed_location.netloc}`.", probe))
    return probes, issues


def probe_xss_reflection(target_url: str, timeout: int) -> tuple[list[dict], list[dict]]:
    marker = f"osr_probe_{int(time.time())}"
    url = with_query(target_url, {"osr_probe": marker})
    response = fetch(url, method="GET", timeout=timeout)
    body = response.get("body", "")
    reflected = marker in body
    escaped_reflected = html.escape(marker) in body
    probe = {"class": "xss", "method": "GET", "url": url, "status": response.get("status"), "markerReflected": reflected}
    issues: list[dict] = []
    if reflected and not escaped_reflected:
        issues.append(issue("low", "reflected_marker", "A benign marker was reflected in the response. Review the rendering context for XSS risk.", probe))
    return [probe], issues


def probe_error(target_url: str, timeout: int) -> tuple[list[dict], list[dict]]:
    url = target_path(target_url, f"/__osr_probe_{int(time.time())}")
    response = fetch(url, method="GET", timeout=timeout)
    body = response.get("body", "")
    matches = sorted(set(match.group(0) for match in STACK_PATTERNS.finditer(body)))[:10]
    probe = {"class": "error", "method": "GET", "url": url, "status": response.get("status"), "matches": matches}
    issues = [issue("medium", "verbose_error_signal", f"Error response contains stack/debug markers: {', '.join(matches)}.", probe)] if matches else []
    return [probe], issues


def probe_exposure(target_url: str, timeout: int) -> tuple[list[dict], list[dict]]:
    probes: list[dict] = []
    issues: list[dict] = []
    for path in EXPOSURE_PATHS:
        url = target_path(target_url, path)
        response = fetch(url, method="GET", timeout=timeout)
        body = response.get("body", "")
        content_type = response.get("headers", {}).get("content-type", "")
        probe = {
            "class": "exposure",
            "method": "GET",
            "url": url,
            "status": response.get("status"),
            "contentType": content_type,
            "bytesRead": len(body.encode("utf-8")),
        }
        probes.append(probe)
        if response.get("status") != 200:
            continue
        if path.startswith("/.env") and ("=" in body or SECRET_PATTERNS.search(body)):
            issues.append(issue("high", "env_file_exposed", f"`{path}` returned a 200 response with env-like content.", probe))
        elif SECRET_PATTERNS.search(body):
            issues.append(issue("high", "secret_like_public_response", f"`{path}` returned secret-like keys.", probe))
        elif path in {"/swagger.json", "/openapi.json", "/api-docs", "/debug", "/server-status"}:
            issues.append(issue("medium", "debug_or_api_docs_public", f"`{path}` is publicly reachable.", probe))
        elif path in {"/config.json", "/login-config.json"}:
            issues.append(issue("info", "public_config_response", f"`{path}` is publicly reachable; verify it contains no secrets.", probe))
    return probes, issues


def render_markdown(payload: dict) -> str:
    lines = [
        "# Authorized Active Probe Results",
        "",
        f"- Target: {payload['target_url']}",
        f"- Created UTC: {payload['created_utc']}",
        f"- Classes: {', '.join(payload['classes'])}",
        f"- Probes sent: {len(payload['probes'])}",
        f"- Issues/signals: {len(payload['issues'])}",
        "",
        "## Issues And Signals",
    ]
    if payload["issues"]:
        for item in payload["issues"]:
            lines.append(f"- {item['severity']}: {item['kind']} - {item['detail']} (`{item['method']} {item['url']}`)")
    else:
        lines.append("- No issues found by the guarded active probes.")
    lines.extend(["", "## Probe Log"])
    for probe in payload["probes"]:
        lines.append(f"- {probe['class']}: `{probe['method']} {probe['url']}` status={probe.get('status')}")
    lines.append("")
    return "\n".join(lines)


def update_manifest(workspace: Path) -> None:
    manifest_path = workspace / "state" / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["active_validation_authorized"] = True
    manifest.setdefault("stages", {})["active_validation"] = "safe_probes_completed"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_active_choice(answer: str) -> bool | None:
    normalized = answer.strip().lower()
    if normalized == "" or normalized in {"2", "not active", "inactive", "skip", "no", "n"}:
        return False
    if normalized in {"1", "active", "yes", "y"}:
        return True
    return None


def confirm_or_exit(args: argparse.Namespace) -> None:
    if args.confirm_active:
        return
    if not sys.stdin.isatty():
        raise SystemExit("Refusing active probes without --confirm-active in non-interactive mode.")
    print("Active probes send low-risk GET/OPTIONS requests to the target.")
    print(f"Target: {args.target_url}")
    print(f"Classes: {args.classes}")
    print("Choose an option:")
    print("  1) ACTIVE")
    print("  2) NOT ACTIVE (default)")
    while True:
        answer = input("Select 1 or 2 [2]: ")
        decision = parse_active_choice(answer)
        if decision is None:
            print("Please choose 1 (ACTIVE) or 2 (NOT ACTIVE).")
            continue
        if not decision:
            raise SystemExit("Active probes cancelled.")
        return


def normalize_classes(raw: str) -> list[str]:
    selected = [item.strip() for item in raw.split(",") if item.strip()]
    invalid = [item for item in selected if item not in CLASSES]
    if invalid:
        raise SystemExit(f"Unsupported active probe classes: {', '.join(invalid)}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Run guarded low-risk active probes.")
    parser.add_argument("--workspace", required=True, help="Audit workspace")
    parser.add_argument("--target-url", required=True, help="Authorized target URL")
    parser.add_argument("--classes", default="cors,redirect,xss,error,exposure", help="Comma-separated probe classes")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds")
    parser.add_argument("--i-am-authorized", action="store_true", help="Required acknowledgement of authorization")
    parser.add_argument("--confirm-active", action="store_true", help="Required for non-interactive active probe execution")
    parser.add_argument("--allow-remote", action="store_true", help="Allow active probes against non-local targets")
    args = parser.parse_args()

    if not args.i_am_authorized:
        raise SystemExit("Refusing active probes without --i-am-authorized.")
    parsed = urllib.parse.urlparse(args.target_url)
    if parsed.scheme not in {"http", "https"}:
        raise SystemExit("Only http and https target URLs are supported.")
    if not args.allow_remote and not is_local_target(args.target_url):
        raise SystemExit("Refusing active probes against a non-local target without --allow-remote.")

    selected = normalize_classes(args.classes)
    confirm_or_exit(args)

    probes: list[dict] = []
    issues: list[dict] = []
    runners = {
        "cors": probe_cors,
        "redirect": probe_redirect,
        "xss": probe_xss_reflection,
        "error": probe_error,
        "exposure": probe_exposure,
    }
    for name in selected:
        next_probes, next_issues = runners[name](args.target_url, args.timeout)
        probes.extend(next_probes)
        issues.extend(next_issues)

    workspace = Path(args.workspace).expanduser().resolve()
    (workspace / "state").mkdir(parents=True, exist_ok=True)
    (workspace / "evidence").mkdir(parents=True, exist_ok=True)
    payload = {
        "authorized": True,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_url": args.target_url,
        "classes": selected,
        "allow_remote": args.allow_remote,
        "probes": probes,
        "issues": issues,
    }
    (workspace / "state" / "active_probe.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (workspace / "evidence" / "active_probe.md").write_text(render_markdown(payload), encoding="utf-8")
    update_manifest(workspace)

    print(json.dumps({"probes": len(probes), "issues": len(issues), "json": str(workspace / "state" / "active_probe.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
