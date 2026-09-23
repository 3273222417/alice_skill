#!/usr/bin/env python3
"""Generate a consolidated Markdown security review report from workspace state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def section(title: str, content: str) -> str:
    return f"\n## {title}\n\n{content.strip() or '_No data recorded._'}\n"


def render_inventory(payload: dict) -> str:
    if not payload:
        return "_Inventory not generated._"
    lines = [f"- Repository: `{payload.get('repo', '')}`", f"- Files scanned: {payload.get('file_count', 0)}", ""]
    lines.append("### Surface Counts")
    for label, paths in payload.get("labels", {}).items():
        lines.append(f"- {label}: {len(paths)}")
    lines.append("\n### Pattern Match Counts")
    for kind, matches in payload.get("pattern_matches", {}).items():
        lines.append(f"- {kind}: {len(matches)}")
    return "\n".join(lines)


def render_validation(payload: dict) -> str:
    if not payload:
        return "_Passive validation not generated._"
    lines = [
        f"- Target: `{payload.get('target_url', '')}`",
        f"- Status: {payload.get('status')}",
        f"- Header issues: {len(payload.get('issues', []))}",
    ]
    for issue in payload.get("issues", []):
        detail = issue.get("detail") or issue.get("header") or issue.get("kind")
        lines.append(f"- {issue.get('severity', 'info')}: {issue.get('kind')} - {detail}")
    return "\n".join(lines)


def render_crawl(payload: dict) -> str:
    if not payload:
        return "_Passive crawl not generated._"
    pages = payload.get("pages", [])
    requests = payload.get("requests", [])
    blocked = payload.get("blockedRequests", [])
    lines = [
        f"- Start URL: `{payload.get('startUrl', '')}`",
        f"- Pages visited: {len(pages)}",
        f"- Requests observed: {len(requests)}",
        f"- Non-read requests blocked: {len(blocked)}",
    ]
    for page in pages[:30]:
        lines.append(f"- `{page.get('url')}` status={page.get('status')} title={page.get('title', '')!r}")
    return "\n".join(lines)


def render_api_map(payload: dict) -> str:
    if not payload:
        return "_API/request map not generated._"
    endpoints = payload.get("endpoints", [])
    lines = [f"- Endpoints observed: {len(endpoints)}"]
    for endpoint in endpoints[:50]:
        statuses = ", ".join(f"{key}={value}" for key, value in endpoint.get("statuses", {}).items())
        lines.append(f"- `{endpoint.get('method')} {endpoint.get('path')}` count={endpoint.get('count')} statuses={statuses}")
    return "\n".join(lines)


def render_api_coverage(payload: dict) -> str:
    if not payload:
        return "_API coverage not generated._"
    summary = payload.get("summary", {})
    lines = [
        f"- Total endpoints: {payload.get('endpointCount', 0)}",
        f"- Source and runtime: {summary.get('both', 0)}",
        f"- Source only: {summary.get('source_only', 0)}",
        f"- Runtime only: {summary.get('runtime_only', 0)}",
    ]
    source_only = [row for row in payload.get("endpoints", []) if row.get("sourceSeen") and not row.get("runtimeSeen")]
    runtime_only = [row for row in payload.get("endpoints", []) if row.get("runtimeSeen") and not row.get("sourceSeen")]
    if source_only:
        lines.append("\n### Source Only")
        for row in source_only[:30]:
            lines.append(f"- `{row.get('method')} {row.get('path')}` source={row.get('sourceCount')}")
    if runtime_only:
        lines.append("\n### Runtime Only")
        for row in runtime_only[:30]:
            statuses = ", ".join(f"{key}={value}" for key, value in row.get("runtimeStatuses", {}).items())
            lines.append(f"- `{row.get('method')} {row.get('path')}` runtime={row.get('runtimeCount')} statuses={statuses}")
    return "\n".join(lines)


def render_backend_fingerprint(payload: dict) -> str:
    if not payload:
        return "_Backend fingerprint not generated._"
    lines = [
        f"- Framework signals: {len(payload.get('frameworks', []))}",
        f"- Entrypoints: {len(payload.get('entrypoints', []))}",
        f"- Data layer hints: {len(payload.get('ormHints', []))}",
        f"- Security middleware hints: {len(payload.get('securityMiddlewareHints', []))}",
    ]
    for item in payload.get("frameworks", [])[:20]:
        lines.append(f"- {item.get('name')} confidence={item.get('confidence')} ecosystem={item.get('ecosystem', 'unknown')}")
    return "\n".join(lines)


def render_server_route_map(payload: dict) -> str:
    if not payload:
        return "_Server route map not generated._"
    lines = [f"- Routes discovered: {payload.get('routeCount', 0)}"]
    for method, count in payload.get("summary", {}).get("byMethod", {}).items():
        lines.append(f"- {method}: {count}")
    for route in payload.get("routes", [])[:60]:
        lines.append(f"- `{route.get('method')} {route.get('path')}` `{route.get('file')}:{route.get('line')}` tags={','.join(route.get('riskTags', [])) or '-'}")
    return "\n".join(lines)


def render_issue_map(payload: dict, label: str) -> str:
    if not payload:
        return f"_{label} not generated._"
    lines = [
        f"- Routes analyzed: {payload.get('routeCount', 0)}",
        f"- Issues requiring review: {len(payload.get('issues', []))}",
    ]
    for status, count in payload.get("summary", {}).items():
        lines.append(f"- {status}: {count}")
    for issue in payload.get("issues", [])[:50]:
        lines.append(f"- {issue.get('severity')}: `{issue.get('method')} {issue.get('path')}` `{issue.get('file')}:{issue.get('line')}` - {issue.get('issue')}")
    return "\n".join(lines)


def render_dataflow(payload: dict) -> str:
    if not payload:
        return "_Dataflow risk map not generated._"
    lines = [
        f"- Sources: {payload.get('sourceCount', 0)}",
        f"- Sinks: {payload.get('sinkCount', 0)}",
        f"- Risks requiring review: {payload.get('riskCount', 0)}",
    ]
    for risk in payload.get("risks", [])[:50]:
        sink = risk.get("sink", {})
        lines.append(f"- {risk.get('severity')}: {risk.get('kind')} `{risk.get('file')}` sink L{sink.get('line')} - {risk.get('reason')}")
    return "\n".join(lines)


def render_server_checks(payload: dict) -> str:
    if not payload:
        return "_Server security checks not generated._"
    lines = []
    for check in payload.get("checks", []):
        if not check.get("signalCount"):
            continue
        lines.append(f"- {check.get('severity')}: {check.get('id')} signals={check.get('signalCount')} status={check.get('status')}")
        for signal in check.get("signals", [])[:3]:
            lines.append(f"  - `{signal.get('path')}:{signal.get('line')}` {signal.get('snippet')}")
    return "\n".join(lines) or "_No server-specific check signals found._"


def render_api_spec(payload: dict) -> str:
    if not payload:
        return "_API spec map not generated._"
    summary = payload.get("summary", {})
    lines = [
        f"- Specs detected: {len(payload.get('specs', []))}",
        f"- Spec endpoints: {summary.get('specEndpoints', 0)}",
        f"- Source routes: {summary.get('sourceRoutes', 0)}",
        f"- Source routes missing from spec: {summary.get('sourceOnly', 0)}",
    ]
    for spec in payload.get("specs", [])[:20]:
        lines.append(f"- `{spec.get('path')}` type={spec.get('type')} endpoints={spec.get('endpointCount')}")
    return "\n".join(lines)


def render_backend_runtime(payload: dict) -> str:
    if not payload:
        return "_Backend runtime validation not generated._"
    lines = [
        f"- Target: `{payload.get('targetUrl', '')}`",
        f"- Guardrail: {payload.get('guardrail', '')}",
        f"- Requests sent: {len(payload.get('results', []))}",
        f"- Signals: {len(payload.get('signals', []))}",
    ]
    for result in payload.get("results", [])[:50]:
        if result.get("error"):
            lines.append(f"- error `{result.get('method')} {result.get('path')}` {result.get('error')}")
        else:
            lines.append(f"- {result.get('status')} `{result.get('method')} {result.get('path')}`")
    for signal in payload.get("signals", [])[:30]:
        lines.append(f"- {signal.get('severity')}: {signal.get('kind')} - {signal.get('endpoint')} - {signal.get('detail')}")
    return "\n".join(lines)


def render_role_matrix(payload: dict) -> str:
    if not payload:
        return "_Role matrix not generated._"
    lines = [
        f"- Target: `{payload.get('targetUrl', '')}`",
        f"- Profiles: {', '.join(profile.get('name', '') for profile in payload.get('profiles', []))}",
        f"- Endpoints tested: {len(payload.get('endpoints', []))}",
        f"- Requests sent: {len(payload.get('rows', []))}",
        f"- Signals: {len(payload.get('signals', []))}",
    ]
    for signal in payload.get("signals", [])[:30]:
        lines.append(f"- {signal.get('severity')}: {signal.get('kind')} - {signal.get('endpoint')} - {signal.get('detail')}")
    return "\n".join(lines)


def render_auth(payload: dict) -> str:
    if not payload:
        return "_Authenticated session not created._"
    return "\n".join(
        [
            f"- Login URL: `{payload.get('login_url', '')}`",
            f"- Final URL: `{payload.get('final_url', '')}`",
            f"- Success: {payload.get('success')}",
            f"- Success reason: {payload.get('success_reason', '')}",
            f"- Username env: `{payload.get('username_env', '')}`",
            f"- Password env: `{payload.get('password_env', '')}`",
            "- Secrets recorded: no",
        ]
    )


def render_active(active: dict, probe: dict) -> str:
    lines = []
    if active:
        lines.extend(
            [
                f"- Plan authorized: {active.get('authorized')}",
                f"- Plan target: `{active.get('target_url', '')}`",
                f"- Planned classes: {', '.join(active.get('classes', []))}",
                f"- Plan note: {active.get('note', '')}",
            ]
        )
    else:
        lines.append("- Active validation plan not created.")
    if probe:
        lines.extend(
            [
                "",
                "### Guarded Active Probes",
                f"- Probes sent: {len(probe.get('probes', []))}",
                f"- Issues/signals: {len(probe.get('issues', []))}",
            ]
        )
        for item in probe.get("issues", [])[:30]:
            lines.append(f"- {item.get('severity')}: {item.get('kind')} - {item.get('detail')}")
    else:
        lines.append("- Guarded active probes not executed.")
    return "\n".join(lines)


def render_hypotheses(payload: list) -> str:
    if not payload:
        return "_No hypotheses generated._"
    lines = []
    for item in payload:
        lines.append(f"- {item.get('id')} [{item.get('severity')}] {item.get('title')} ({item.get('status')})")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a consolidated report.")
    parser.add_argument("--workspace", required=True, help="Audit workspace")
    parser.add_argument("--out", default="", help="Output report path")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    state = workspace / "state"
    evidence = workspace / "evidence"
    out = Path(args.out).expanduser().resolve() if args.out else workspace / "reports" / "report.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    manifest = read_json(state / "manifest.json")
    if (state / "manifest.json").exists():
        manifest.setdefault("stages", {})["report"] = "completed"
    inventory = read_json(state / "attack_surface.json")
    validation = read_json(state / "passive_validation.json")
    crawl = read_json(state / "passive_crawl.json")
    api_map = read_json(state / "api_map.json")
    api_coverage = read_json(state / "api_coverage.json")
    backend_fingerprint = read_json(state / "backend_fingerprint.json")
    server_route_map = read_json(state / "server_route_map.json")
    authz_map = read_json(state / "authz_map.json")
    dataflow_risk_map = read_json(state / "dataflow_risk_map.json")
    validation_coverage = read_json(state / "validation_coverage.json")
    server_security_checks = read_json(state / "server_security_checks.json")
    api_spec_map = read_json(state / "api_spec_map.json")
    backend_runtime = read_json(state / "backend_runtime_validation.json")
    role_matrix = read_json(state / "role_matrix.json")
    auth = read_json(state / "auth_session.json")
    hypotheses = read_json(state / "hypotheses.json")
    active = read_json(state / "active_validation.json")
    active_probe = read_json(state / "active_probe.json")
    findings = (workspace / "02-findings.md").read_text(encoding="utf-8") if (workspace / "02-findings.md").exists() else ""

    content = [
        "# Security Review Report",
        section("Scope", "\n".join(f"- {key}: `{value}`" for key, value in manifest.items() if key != "stages")),
        section("Stage Status", "\n".join(f"- {key}: {value}" for key, value in manifest.get("stages", {}).items())),
        section("Authenticated Session", render_auth(auth)),
        section("Backend Framework Fingerprint", render_backend_fingerprint(backend_fingerprint)),
        section("Server Route Map", render_server_route_map(server_route_map)),
        section("Authorization Map", render_issue_map(authz_map, "Authorization map")),
        section("Dataflow Risk Map", render_dataflow(dataflow_risk_map)),
        section("Validation Coverage", render_issue_map(validation_coverage, "Validation coverage")),
        section("Server Security Checks", render_server_checks(server_security_checks)),
        section("API Spec Map", render_api_spec(api_spec_map)),
        section("Backend Runtime Validation", render_backend_runtime(backend_runtime)),
        section("Vulnerability Hypotheses", render_hypotheses(hypotheses if isinstance(hypotheses, list) else [])),
        section("Findings", findings),
        section("Attack Surface Inventory", render_inventory(inventory)),
        section("Passive Crawl", render_crawl(crawl)),
        section("API / Request Map", render_api_map(api_map)),
        section("API Coverage", render_api_coverage(api_coverage)),
        section("Role / Permission Matrix", render_role_matrix(role_matrix)),
        section("Safe Validation", render_validation(validation)),
        section("Active Validation", render_active(active, active_probe)),
        section("Evidence Files", "\n".join(f"- `{path.name}`" for path in sorted(evidence.glob("*")))),
    ]

    out.write_text("\n".join(content).strip() + "\n", encoding="utf-8")
    if (state / "manifest.json").exists():
        (state / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
