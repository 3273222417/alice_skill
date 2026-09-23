#!/usr/bin/env python3
"""Validate director project state, identity routing, references, and Seedance jobs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import project_ops  # noqa: E402


class Report:
    def __init__(self) -> None:
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []
        self.info: list[dict[str, str]] = []

    def error(self, code: str, message: str) -> None:
        self.errors.append({"code": code, "message": message})

    def warn(self, code: str, message: str) -> None:
        self.warnings.append({"code": code, "message": message})

    def note(self, code: str, message: str) -> None:
        self.info.append({"code": code, "message": message})

    def payload(self, project: Path) -> dict[str, Any]:
        return {
            "ok": not self.errors,
            "project": str(project),
            "summary": {
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "info": len(self.info),
            },
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
        }


def current_asset_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {asset.get("asset_id"): asset for asset in data.get("assets", []) if asset.get("asset_id")}


def validate_files(data: dict[str, Any], report: Report, verify_hash: bool) -> None:
    for asset in data.get("assets", []):
        asset_id = asset.get("asset_id", "<unknown>")
        try:
            version = project_ops.current_version(asset)
        except KeyError as exc:
            report.error("ASSET_CURRENT_VERSION", str(exc))
            continue
        directory = Path(version.get("directory", ""))
        if not directory.is_dir():
            report.error("ASSET_VERSION_DIR", f"{asset_id}: version directory does not exist: {directory}")
        files = version.get("files", [])
        if asset.get("status") in {"reviewed", "locked"} and not files:
            report.warn("ASSET_ACCEPTED_EMPTY", f"{asset_id}: {asset.get('status')} asset has no managed files")
        for record in files:
            path = Path(record.get("path", ""))
            if not path.is_file():
                report.error("ASSET_FILE_MISSING", f"{asset_id}: managed file missing: {path}")
                continue
            if verify_hash and record.get("sha256"):
                actual = project_ops.sha256_file(path)
                if actual.lower() != str(record["sha256"]).lower():
                    report.error("ASSET_HASH_MISMATCH", f"{asset_id}: checksum changed: {path}")


def validate_identity(data: dict[str, Any], report: Report) -> None:
    identity = data.get("identity", {})
    mode = identity.get("identity_mode")
    backend = identity.get("generation_backend")
    eligible = identity.get("seedance_eligible")
    if mode == "consented_local_identity":
        if backend in {"seedance_2_5", "codex_imagegen"}:
            report.error(
                "IDENTITY_BACKEND",
                f"consented_local_identity cannot use {backend} as its identity-generation backend; use PhotoMaker/PuLID/LivePortrait/ConsisID",
            )
        if eligible is not False:
            report.error("IDENTITY_ELIGIBILITY", "consented_local_identity must set project seedance_eligible=false")
        report.note("IDENTITY_LOCAL", f"local identity backend: {backend}")
    elif mode in {"fictional", "synthetic_actor"} and eligible is False:
        report.warn("IDENTITY_DISABLED", f"{mode} is marked Seedance-ineligible; confirm this is intentional")


def validate_shot(
    shot: dict[str, Any],
    asset_map: dict[str, dict[str, Any]],
    data: dict[str, Any],
    report: Report,
) -> None:
    shot_id = str(shot.get("shot_id", "<unknown>"))
    try:
        duration = float(shot.get("duration", 0))
    except (TypeError, ValueError):
        report.error("SHOT_DURATION", f"{shot_id}: duration is not numeric")
        return
    if duration <= 0:
        report.error("SHOT_DURATION", f"{shot_id}: duration must be greater than zero")
    start_hold = float(shot.get("start_hold", 0) or 0)
    end_hold = float(shot.get("end_hold", 0) or 0)
    if start_hold < 0 or end_hold < 0 or start_hold + end_hold > duration:
        report.error("SHOT_HOLDS", f"{shot_id}: start/end holds do not fit inside {duration}s")
    if not shot.get("end_state"):
        report.warn("SHOT_END_STATE", f"{shot_id}: no explicit ending state")
    action = str(shot.get("action", ""))
    clause_count = len(re.findall(r"[,，;；]", action)) + 1
    if len(action) > 220 or clause_count > 5:
        report.warn("SHOT_COMPLEXITY", f"{shot_id}: action may contain too many independent events")
    if not shot.get("camera_move") or not shot.get("shot_size"):
        report.warn("SHOT_CAMERA", f"{shot_id}: shot_size/camera_move should be explicit")

    refs = shot.get("asset_refs", [])
    for asset_id in refs:
        asset = asset_map.get(asset_id)
        if not asset:
            report.error("SHOT_ASSET_MISSING", f"{shot_id}: missing asset {asset_id}")
            continue
        if shot.get("backend") == "seedance_2_5" and asset.get("seedance_eligible") is False:
            report.error(
                "SEEDANCE_INELIGIBLE_ASSET",
                f"{shot_id}: {asset_id} is Seedance-ineligible; route the identity layer locally or remove it from this Seedance job",
            )

    mode = project_ops.infer_seedance_mode(shot)
    shot["inferred_seedance_mode"] = mode
    if shot.get("backend") != "seedance_2_5":
        return
    report.note("SHOT_MODE", f"{shot_id}: {mode}")
    source = Path(shot["source_video"]) if shot.get("source_video") else None
    if source and not source.is_file():
        report.error("SOURCE_VIDEO_MISSING", f"{shot_id}: source video missing: {source}")
    if mode == "t2v" and refs:
        report.error("MODE_T2V_REFERENCES", f"{shot_id}: t2v cannot carry media references")
    elif mode == "omni_reference" and not refs and not source:
        report.warn("MODE_OMNI_EMPTY", f"{shot_id}: omni_reference has no registered reference")
    elif mode == "video_edit":
        if not source:
            report.error("EDIT_SOURCE", f"{shot_id}: video_edit requires source_video")
        if not shot.get("edit_instructions"):
            report.error("EDIT_SCOPE", f"{shot_id}: video_edit requires edit_instructions")
    elif mode == "video_extension":
        if not source:
            report.error("EXTENSION_SOURCE", f"{shot_id}: video_extension requires source_video")
        if shot.get("extension_direction") not in {"forward", "backward"}:
            report.error("EXTENSION_DIRECTION", f"{shot_id}: video_extension requires forward/backward direction")


def validate_sequence_patterns(data: dict[str, Any], report: Report) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for shot in data.get("shots", []):
        grouped[str(shot.get("sequence_id"))].append(shot)
    for sequence_id, shots in grouped.items():
        shots.sort(key=lambda item: (item.get("order", 0), item.get("time_start", 0)))
        total = sum(float(shot.get("duration", 0) or 0) for shot in shots)
        has_seedance = any(shot.get("backend") == "seedance_2_5" for shot in shots)
        if has_seedance and not (4 <= total <= 30):
            report.error(
                "SEQUENCE_DURATION",
                f"{sequence_id}: Seedance production sequence is {total:g}s; expected 4–30s",
            )
        report.note("SEQUENCE_DURATION", f"{sequence_id}: {total:g}s across {len(shots)} shots")
        for index in range(2, len(shots)):
            triple = shots[index - 2 : index + 1]
            signatures = {(shot.get("shot_size"), shot.get("camera_move")) for shot in triple}
            if len(signatures) == 1:
                report.warn(
                    "REPETITIVE_COVERAGE",
                    f"{sequence_id}: {triple[0].get('shot_id')}–{triple[-1].get('shot_id')} repeat the same shot size and move",
                )


def run_preflight(project_path: Path, data: dict[str, Any], verify_hash: bool) -> Report:
    report = Report()
    for error in project_ops.validate_project(data):
        report.error("STRUCTURE", error)
    project = data.get("project", {})
    if str(project.get("resolution", "")).lower() != "720p":
        if any(shot.get("backend") == "seedance_2_5" for shot in data.get("shots", [])):
            report.error("SEEDANCE_RESOLUTION", "this workbench requires 720p for Seedance 2.5 output")
        else:
            report.warn("PROJECT_RESOLUTION", f"project resolution is {project.get('resolution')}, not 720p")
    validate_identity(data, report)
    validate_files(data, report, verify_hash)
    assets = current_asset_map(data)
    for shot in data.get("shots", []):
        validate_shot(shot, assets, data, report)
    if data.get("shots"):
        validate_sequence_patterns(data, report)
    else:
        report.warn("NO_SHOTS", "project has no shots yet")
    if len(data.get("assets", [])) > 50:
        report.warn("REFERENCE_BUDGET", "project has more than 50 assets; attach only shot-relevant materials")
    return report


def print_text(payload: dict[str, Any]) -> None:
    status = "PASS" if payload["ok"] else "FAIL"
    summary = payload["summary"]
    print(f"{status}  errors={summary['errors']} warnings={summary['warnings']} info={summary['info']}")
    for section, label in [("errors", "ERROR"), ("warnings", "WARN"), ("info", "INFO")]:
        for item in payload[section]:
            print(f"[{label}:{item['code']}] {item['message']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--verify-hash", action="store_true")
    parser.add_argument("--write-report", help="Optional JSON report output path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        project_path, data = project_ops.load_project(args.project)
        report = run_preflight(project_path, data, args.verify_hash)
        payload = report.payload(project_path)
        if args.write_report:
            output = Path(args.write_report).expanduser().resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_text(payload)
        return 0 if payload["ok"] else 1
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
