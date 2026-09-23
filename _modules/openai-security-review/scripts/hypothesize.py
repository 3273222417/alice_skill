#!/usr/bin/env python3
"""Generate a validation queue from the attack-surface inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

RULES = [
    {
        "kind": "client_token_storage",
        "source": "xss_dom",
        "severity": "medium",
        "title": "Review DOM sinks and browser-side token exposure",
        "reason": "DOM sinks combined with token/session storage can turn XSS into account compromise.",
        "validation": "Inspect matched code paths and confirm whether untrusted input can reach DOM sinks.",
    },
    {
        "kind": "auth_access_control",
        "source": "access_control",
        "severity": "high",
        "title": "Verify server-side authorization for privileged or tenant-scoped flows",
        "reason": "Role, tenant, or owner checks in client code may hide missing backend enforcement.",
        "validation": "Trace each privileged route/API call to a server-side authorization check.",
    },
    {
        "kind": "redirect_callback",
        "source": "redirect_url",
        "severity": "medium",
        "title": "Validate redirect and callback URL handling",
        "reason": "User-controlled return URLs can cause open redirects or OAuth callback abuse.",
        "validation": "Confirm allowlist or same-origin validation before navigation or redirect.",
    },
    {
        "kind": "secret_exposure",
        "source": "secret_like",
        "severity": "high",
        "title": "Review secret-like configuration and browser-exposed env vars",
        "reason": "Secrets in frontend code or public env vars can be exposed to users.",
        "validation": "Classify each match as public-safe config or real credential; rotate real secrets.",
    },
    {
        "kind": "ssrf_url_fetch",
        "source": "ssrf_fetcher",
        "severity": "high",
        "title": "Review user-controlled URL fetchers for SSRF",
        "reason": "URL preview, proxy, webhook, and import flows can reach internal services if not constrained.",
        "validation": "Confirm scheme, host, DNS, redirect, and private-IP protections.",
    },
    {
        "kind": "file_handling",
        "source": "file_handling",
        "severity": "medium",
        "title": "Review file upload/download handling",
        "reason": "File flows often need MIME, extension, size, storage, and authorization checks.",
        "validation": "Trace accepted file types, storage path, preview rendering, and download authorization.",
    },
]


def load_inventory(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def build_hypotheses(inventory: dict) -> list[dict]:
    matches = inventory.get("pattern_matches", {})
    hypotheses = []
    for index, rule in enumerate(RULES, start=1):
        evidence = matches.get(rule["source"], [])
        if not evidence:
            continue
        hypotheses.append(
            {
                "id": f"H{index:03d}",
                "kind": rule["kind"],
                "severity": rule["severity"],
                "title": rule["title"],
                "reason": rule["reason"],
                "validation": rule["validation"],
                "status": "needs_review",
                "evidence": evidence[:25],
                "evidence_count": len(evidence),
            }
        )
    return hypotheses


def evidence_from_location(item: dict) -> dict:
    return {
        "path": item.get("path") or item.get("file") or "",
        "line": item.get("line", 0),
        "snippet": item.get("snippet") or item.get("issue") or item.get("reason") or "",
    }


def append_hypothesis(hypotheses: list[dict], *, kind: str, severity: str, title: str, reason: str, validation: str, evidence: list[dict]) -> None:
    if not evidence:
        return
    hypotheses.append(
        {
            "id": f"H{len(hypotheses) + 1:03d}",
            "kind": kind,
            "severity": severity,
            "title": title,
            "reason": reason,
            "validation": validation,
            "status": "needs_review",
            "evidence": evidence[:25],
            "evidence_count": len(evidence),
        }
    )


def extend_with_backend_hypotheses(hypotheses: list[dict], workspace: Path) -> list[dict]:
    state = workspace / "state"

    authz = read_json(state / "authz_map.json", {})
    authz_issues = authz.get("issues", [])
    append_hypothesis(
        hypotheses,
        kind="server_authz_gap",
        severity="high" if any(item.get("severity") == "high" for item in authz_issues) else "medium",
        title="Verify backend authorization gaps on sensitive routes",
        reason="Sensitive or mutating routes without nearby authorization signals may rely on incomplete middleware or client-side gating.",
        validation="Trace each route through global middleware, guards, policies, tenant/owner checks, and negative role tests.",
        evidence=[evidence_from_location(item) for item in authz_issues],
    )

    dataflow = read_json(state / "dataflow_risk_map.json", {})
    dataflow_risks = dataflow.get("risks", [])
    append_hypothesis(
        hypotheses,
        kind="server_source_to_sink",
        severity="high" if any(item.get("severity") == "high" for item in dataflow_risks) else "medium",
        title="Trace request-controlled input into high-risk server sinks",
        reason="Request inputs and sink families appear in close proximity; this can indicate SQL/NoSQL injection, SSRF, command execution, file traversal, redirect, or template risks.",
        validation="Perform manual taint tracing from the source to the sink and confirm parameterization, allowlists, canonicalization, and escaping.",
        evidence=[evidence_from_location(item.get("sink", {})) for item in dataflow_risks],
    )

    validation = read_json(state / "validation_coverage.json", {})
    validation_issues = validation.get("issues", [])
    append_hypothesis(
        hypotheses,
        kind="server_validation_gap",
        severity="high" if any(item.get("severity") == "high" for item in validation_issues) else "medium",
        title="Review state-changing routes without local validation signals",
        reason="Mutating, upload, webhook, or callback routes should have explicit schema or file validation close to the route or in shared middleware.",
        validation="Confirm the effective validation layer, malformed input behavior, size/type limits, and error handling for each route.",
        evidence=[evidence_from_location(item) for item in validation_issues],
    )

    server_checks = read_json(state / "server_security_checks.json", {})
    check_evidence = []
    high_signal = False
    for check in server_checks.get("checks", []):
        if not check.get("signalCount"):
            continue
        if check.get("severity") == "high":
            high_signal = True
        for signal in check.get("signals", [])[:5]:
            signal = dict(signal)
            signal["snippet"] = f"{check.get('id')}: {signal.get('snippet', '')}"
            check_evidence.append(signal)
    append_hypothesis(
        hypotheses,
        kind="server_security_control",
        severity="high" if high_signal else "medium",
        title="Review server security control signals",
        reason="Static checks found server-side security control signals that can indicate weak JWT handling, secret exposure, debug leakage, CORS/CSRF gaps, or unsafe crypto.",
        validation="Classify each signal in deployment context, verify secure production configuration, and remediate real exposures.",
        evidence=[evidence_from_location(item) for item in check_evidence],
    )

    spec_map = read_json(state / "api_spec_map.json", {})
    missing_spec = [row for row in spec_map.get("coverage", []) if row.get("sourceRouteSeen") and not row.get("specSeen")]
    append_hypothesis(
        hypotheses,
        kind="api_contract_drift",
        severity="low",
        title="Review source routes missing from API contract",
        reason="Routes absent from OpenAPI/Swagger contracts are easier to miss during permission, validation, and client coverage reviews.",
        validation="Confirm whether each route is intentionally private/internal or should be documented and covered by contract tests.",
        evidence=[{"path": "<api-spec-map>", "line": 0, "snippet": f"{row.get('method')} {row.get('path')} missing from spec"} for row in missing_spec],
    )

    return hypotheses


def render_markdown(hypotheses: list[dict]) -> str:
    lines = ["# Vulnerability Hypotheses", ""]
    if not hypotheses:
        lines.append("_No hypotheses generated from current inventory._")
        return "\n".join(lines) + "\n"
    for item in hypotheses:
        lines.extend(
            [
                f"## {item['id']} [{item['severity']}] {item['title']}",
                "",
                f"- Kind: {item['kind']}",
                f"- Status: {item['status']}",
                f"- Reason: {item['reason']}",
                f"- Validation: {item['validation']}",
                f"- Evidence count: {item['evidence_count']}",
                "",
                "### Evidence",
            ]
        )
        for evidence in item["evidence"][:10]:
            line = evidence.get("line", 0)
            suffix = f":{line}" if line else ""
            lines.append(f"- `{evidence.get('path', '')}{suffix}` {evidence.get('snippet', '')}")
        lines.append("")
    return "\n".join(lines)


def update_manifest(workspace: Path) -> None:
    manifest_path = workspace / "state" / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.setdefault("stages", {})["hypotheses"] = "completed"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a vulnerability hypothesis queue.")
    parser.add_argument("--workspace", required=True, help="Audit workspace")
    parser.add_argument("--inventory", default="", help="Optional inventory JSON path")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    inventory_path = Path(args.inventory).expanduser().resolve() if args.inventory else workspace / "state" / "attack_surface.json"
    if not inventory_path.exists():
        raise SystemExit(f"Inventory not found: {inventory_path}")

    hypotheses = extend_with_backend_hypotheses(build_hypotheses(load_inventory(inventory_path)), workspace)
    (workspace / "state").mkdir(parents=True, exist_ok=True)
    (workspace / "state" / "hypotheses.json").write_text(json.dumps(hypotheses, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (workspace / "03-hypotheses.md").write_text(render_markdown(hypotheses), encoding="utf-8")
    update_manifest(workspace)
    print(json.dumps({"hypotheses": len(hypotheses), "path": str(workspace / "state" / "hypotheses.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
