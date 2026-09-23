#!/usr/bin/env python3
"""Map request-controlled sources to risky server-side sink families."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from backend_common import ensure_workspace, is_server_candidate, iter_source_files, location, read_text, update_manifest, write_json

SOURCE_PATTERNS = {
    "request_body": re.compile(r"\b(req|request)\.(body|json|form|data|POST|GET)\b|\b@RequestBody\b|\brequest\.get_json\b", re.I),
    "request_query": re.compile(r"\b(req|request)\.(query|params|args|GET)\b|\b@RequestParam\b|\b@PathVariable\b", re.I),
    "headers_cookies": re.compile(r"\b(req|request)\.(headers|cookies|cookie)\b|\bgetHeader\s*\(", re.I),
    "file_upload": re.compile(r"\b(multer|UploadFile|MultipartFile|request\.files|FileField|IFormFile|UploadedFile|\$_FILES)\b", re.I),
    "url_input": re.compile(r"\b(callback|redirect|returnUrl|return_url|next|webhook|proxy|targetUrl|remoteUrl|fetchUrl|url)\b", re.I),
}

SINK_PATTERNS = {
    "sql_query": re.compile(r"\b(\$queryRawUnsafe|queryRaw|sequelize\.query|connection\.query|db\.query|cursor\.execute|createQuery|prepareStatement|Statement\.execute|knex\.raw|whereRaw|RawSQL)\b", re.I),
    "nosql_query": re.compile(r"\b(\$where|findOneAndUpdate|findByIdAndUpdate|collection\.find|collection\.aggregate|Model\.find|where\s*:)\b", re.I),
    "shell_command": re.compile(r"\b(child_process|exec\s*\(|execFile\s*\(|spawn\s*\(|Runtime\.getRuntime\(\)\.exec|ProcessBuilder|subprocess\.|os\.system|shell_exec|system\s*\()\b", re.I),
    "server_request": re.compile(r"\b(fetch\s*\(|axios\.|requests\.(get|post)|http\.Get|http\.Post|RestTemplate|WebClient|curl_exec|Net::HTTP)\b", re.I),
    "file_path": re.compile(r"\b(readFile|writeFile|createReadStream|sendFile|open\s*\(|FileInputStream|Path\.Combine|Storage::|File::|fs\.|path\.join)\b", re.I),
    "redirect": re.compile(r"\b(res\.redirect|redirect\s*\(|RedirectResponse|HttpResponseRedirect|return\s+redirect|RedirectView)\b", re.I),
    "template_render": re.compile(r"\b(render_template_string|renderToString|template\.Execute|Html\.Raw|raw\s*\(|SafeString|mark_safe)\b", re.I),
    "deserialization": re.compile(r"\b(pickle\.loads|yaml\.load|ObjectInputStream|BinaryFormatter|Marshal\.load|unserialize\s*\()\b", re.I),
}

SINK_SEVERITY = {
    "shell_command": "high",
    "sql_query": "high",
    "deserialization": "high",
    "server_request": "high",
    "file_path": "medium",
    "redirect": "medium",
    "nosql_query": "medium",
    "template_render": "medium",
}

UNSAFE_CONCAT_RE = re.compile(r"(\+|\$\{|%s|format\s*\(|f['\"]|`[^`]*\$\{)", re.I)


def classify_risk(source: dict, sink: dict) -> dict:
    distance = abs(source["line"] - sink["line"])
    severity = SINK_SEVERITY.get(sink["kind"], "medium")
    reasons = [f"{source['kind']} and {sink['kind']} in same file"]
    if distance <= 80:
        reasons.append(f"within {distance} lines")
    if UNSAFE_CONCAT_RE.search(sink.get("snippet", "")):
        reasons.append("sink line contains interpolation or concatenation")
        if severity == "medium":
            severity = "high"
    if sink["kind"] == "server_request" and source["kind"] == "url_input":
        severity = "high"
        reasons.append("URL-like input reaches outbound request family")
    return {
        "severity": severity,
        "kind": f"{source['kind']}->{sink['kind']}",
        "file": sink["path"],
        "source": source,
        "sink": sink,
        "distance": distance,
        "reason": "; ".join(reasons),
        "status": "needs_review",
    }


def scan_repo(repo: Path) -> dict:
    all_sources = []
    all_sinks = []
    risks = []
    for rel, path in iter_source_files(repo):
        text = read_text(path)
        if not text:
            continue
        if not is_server_candidate(rel, path, text):
            continue
        file_sources = []
        file_sinks = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in SOURCE_PATTERNS.items():
                if pattern.search(line):
                    item = location(rel, line_no, line)
                    item["kind"] = kind
                    file_sources.append(item)
            for kind, pattern in SINK_PATTERNS.items():
                if pattern.search(line):
                    item = location(rel, line_no, line)
                    item["kind"] = kind
                    item["unsafeStringSignal"] = bool(UNSAFE_CONCAT_RE.search(line))
                    file_sinks.append(item)
        all_sources.extend(file_sources)
        all_sinks.extend(file_sinks)
        for source in file_sources:
            for sink in file_sinks:
                if abs(source["line"] - sink["line"]) > 120 and not (source["kind"] == "url_input" and sink["kind"] == "server_request"):
                    continue
                risks.append(classify_risk(source, sink))

    risks = sorted(risks, key=lambda item: ({"high": 0, "medium": 1, "low": 2}.get(item["severity"], 3), item["file"], item["distance"]))
    summary = {}
    for risk in risks:
        summary[risk["severity"]] = summary.get(risk["severity"], 0) + 1
    return {
        "repo": str(repo),
        "sourceCount": len(all_sources),
        "sinkCount": len(all_sinks),
        "riskCount": len(risks),
        "summary": dict(sorted(summary.items())),
        "sources": all_sources[:500],
        "sinks": all_sinks[:500],
        "risks": risks[:300],
        "heuristic": "File/proximity analysis; confirm with manual tracing before treating as exploitable.",
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# Dataflow Risk Map",
        "",
        f"- Sources: {payload.get('sourceCount', 0)}",
        f"- Sinks: {payload.get('sinkCount', 0)}",
        f"- Review risks: {payload.get('riskCount', 0)}",
        f"- Heuristic: {payload.get('heuristic', '')}",
        "",
        "## Review Queue",
    ]
    if not payload.get("risks"):
        lines.append("- No source-to-sink proximity risks detected.")
    for risk in payload.get("risks", [])[:100]:
        sink = risk["sink"]
        source = risk["source"]
        lines.append(f"- {risk['severity']}: {risk['kind']} `{risk['file']}` source L{source['line']} -> sink L{sink['line']} - {risk['reason']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Map request sources to server-side sink families.")
    parser.add_argument("--repo", required=True, help="Repository path")
    parser.add_argument("--workspace", required=True, help="Audit workspace")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    if not repo.exists():
        raise SystemExit(f"Repository path does not exist: {repo}")
    state, evidence = ensure_workspace(workspace)
    payload = scan_repo(repo)
    write_json(state / "dataflow_risk_map.json", payload)
    (evidence / "dataflow_risk_map.md").write_text(render_markdown(payload), encoding="utf-8")
    update_manifest(workspace, "dataflow_risk_map")
    print(json.dumps({"sources": payload["sourceCount"], "sinks": payload["sinkCount"], "risks": payload["riskCount"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
