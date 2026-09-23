#!/usr/bin/env python3
"""Versioned project, asset, and shot operations for the director workbench."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


SCHEMA_VERSION = "1.0"
ASSET_PREFIXES = {
    "character": "CHR",
    "location": "LOC",
    "prop": "PRP",
    "wardrobe": "OUT",
    "palette": "PAL",
    "camera": "CAM",
    "keyframe": "KFR",
    "storyboard": "SBD",
    "audio": "AUD",
    "video": "VID",
}
ASSET_STATUSES = {"draft", "reviewed", "locked", "deprecated"}
IDENTITY_MODES = {"fictional", "synthetic_actor", "consented_local_identity"}
BACKENDS = {
    "codex_imagegen",
    "photomaker_v2",
    "pulid_flux",
    "liveportrait",
    "consisid",
    "seedance_2_5",
    "local_post",
}
SEEDANCE_MODES = {"auto", "t2v", "omni_reference", "video_edit", "video_extension"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or f"project-{datetime.now():%Y%m%d-%H%M%S}"


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean: {value}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_json_path(project: str | os.PathLike[str]) -> Path:
    path = Path(project).expanduser()
    if path.is_dir() or path.suffix.lower() != ".json":
        path = path / "project.json"
    return path.resolve()


def load_project(project: str | os.PathLike[str]) -> tuple[Path, dict[str, Any]]:
    path = project_json_path(project)
    if not path.is_file():
        raise FileNotFoundError(f"project file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return path, data


def atomic_save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data.setdefault("project", {})["updated_at"] = now_iso()
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.stem}-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def record_event(data: dict[str, Any], action: str, details: dict[str, Any]) -> None:
    data.setdefault("events", []).append({"at": now_iso(), "action": action, "details": details})


def get_asset(data: dict[str, Any], asset_id: str) -> dict[str, Any]:
    for asset in data.get("assets", []):
        if asset.get("asset_id") == asset_id:
            return asset
    raise KeyError(f"asset not found: {asset_id}")


def get_shot(data: dict[str, Any], shot_id: str) -> dict[str, Any]:
    for shot in data.get("shots", []):
        if shot.get("shot_id") == shot_id:
            return shot
    raise KeyError(f"shot not found: {shot_id}")


def current_version(asset: dict[str, Any]) -> dict[str, Any]:
    number = asset["current_version"]
    for version in asset.get("versions", []):
        if version.get("version") == number:
            return version
    raise KeyError(f"asset {asset.get('asset_id')} has no current version v{number:03d}")


def next_id(items: list[dict[str, Any]], field: str, prefix: str) -> str:
    highest = 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    for item in items:
        match = pattern.match(str(item.get(field, "")))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{prefix}{highest + 1:03d}"


def infer_seedance_mode(shot: dict[str, Any]) -> str:
    explicit = shot.get("seedance_mode", "auto")
    if explicit and explicit != "auto":
        return explicit
    if shot.get("source_video") and shot.get("extension_direction") in {"forward", "backward"}:
        return "video_extension"
    if shot.get("source_video") and shot.get("edit_instructions"):
        return "video_edit"
    if shot.get("asset_refs"):
        return "omni_reference"
    return "t2v"


def command_init(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    project_file = root / "project.json"
    if project_file.exists() and not args.force:
        raise FileExistsError(f"project already exists: {project_file}; pass --force to replace project.json")
    root.mkdir(parents=True, exist_ok=True)
    for folder in ["assets", "boards", "prompts", "jobs", "logs", "renders"]:
        (root / folder).mkdir(exist_ok=True)
    for asset_type in ASSET_PREFIXES:
        (root / "assets" / asset_type).mkdir(parents=True, exist_ok=True)

    identity_mode = args.identity_mode
    backend = args.backend
    if identity_mode == "consented_local_identity" and backend == "codex_imagegen":
        backend = "photomaker_v2"
    eligible = identity_mode != "consented_local_identity"
    stamp = now_iso()
    data: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project": {
            "project_id": args.slug or slugify(args.title),
            "title": args.title,
            "root": str(root),
            "aspect_ratio": args.aspect_ratio,
            "resolution": args.resolution,
            "fps": args.fps,
            "language": args.language,
            "visual_dna": {},
            "created_at": stamp,
            "updated_at": stamp,
        },
        "identity": {
            "identity_mode": identity_mode,
            "generation_backend": backend,
            "seedance_eligible": eligible,
        },
        "assets": [],
        "sequences": [
            {
                "sequence_id": "SEQ001",
                "title": "Main sequence",
                "notes": "",
                "created_at": stamp,
            }
        ],
        "shots": [],
        "events": [],
    }
    record_event(data, "project.init", {"root": str(root), "identity_mode": identity_mode, "backend": backend})
    atomic_save(project_file, data)
    print(project_file)
    return 0


def command_set_identity(args: argparse.Namespace) -> int:
    path, data = load_project(args.project)
    identity = data.setdefault("identity", {})
    identity["identity_mode"] = args.identity_mode
    if args.backend:
        identity["generation_backend"] = args.backend
    elif args.identity_mode == "consented_local_identity":
        identity["generation_backend"] = "photomaker_v2"
    elif identity.get("generation_backend") in {"photomaker_v2", "pulid_flux", "liveportrait", "consisid"}:
        identity["generation_backend"] = "codex_imagegen"
    identity["seedance_eligible"] = (
        args.seedance_eligible
        if args.seedance_eligible is not None
        else args.identity_mode != "consented_local_identity"
    )
    record_event(data, "identity.set", dict(identity))
    atomic_save(path, data)
    print(json.dumps(identity, ensure_ascii=False, indent=2))
    return 0


def command_add_sequence(args: argparse.Namespace) -> int:
    path, data = load_project(args.project)
    sequence_id = next_id(data.setdefault("sequences", []), "sequence_id", "SEQ")
    sequence = {
        "sequence_id": sequence_id,
        "title": args.title,
        "notes": args.notes or "",
        "created_at": now_iso(),
    }
    data["sequences"].append(sequence)
    record_event(data, "sequence.add", {"sequence_id": sequence_id})
    atomic_save(path, data)
    print(sequence_id)
    return 0


def command_add_asset(args: argparse.Namespace) -> int:
    path, data = load_project(args.project)
    prefix = ASSET_PREFIXES[args.type]
    asset_id = next_id(data.setdefault("assets", []), "asset_id", prefix)
    root = Path(data["project"]["root"])
    version_dir = root / "assets" / args.type / asset_id / "v001"
    version_dir.mkdir(parents=True, exist_ok=True)
    project_identity = data.get("identity", {})
    default_eligible = not (
        args.type == "character" and project_identity.get("identity_mode") == "consented_local_identity"
    )
    eligible = args.seedance_eligible if args.seedance_eligible is not None else default_eligible
    stamp = now_iso()
    asset = {
        "asset_id": asset_id,
        "type": args.type,
        "name": args.name,
        "status": args.status,
        "seedance_eligible": eligible,
        "current_version": 1,
        "dependencies": list(dict.fromkeys(args.depends_on or [])),
        "versions": [
            {
                "version": 1,
                "status": args.status,
                "directory": str(version_dir),
                "prompt": args.prompt or "",
                "note": args.note or "",
                "files": [],
                "created_at": stamp,
            }
        ],
        "created_at": stamp,
        "updated_at": stamp,
    }
    known_ids = {item.get("asset_id") for item in data["assets"]}
    missing = [dep for dep in asset["dependencies"] if dep not in known_ids]
    if missing:
        raise ValueError(f"unknown dependency asset IDs: {', '.join(missing)}")
    data["assets"].append(asset)
    record_event(data, "asset.add", {"asset_id": asset_id, "type": args.type})
    atomic_save(path, data)
    print(asset_id)
    return 0


def command_add_file(args: argparse.Namespace) -> int:
    path, data = load_project(args.project)
    source = Path(args.path).expanduser().resolve()
    if not source.is_file() and not args.allow_missing:
        raise FileNotFoundError(f"source file not found: {source}")
    asset = get_asset(data, args.id)
    version = current_version(asset)
    destination: Path
    if args.no_copy:
        destination = source
    else:
        version_dir = Path(version["directory"])
        version_dir.mkdir(parents=True, exist_ok=True)
        destination = version_dir / (args.name or source.name)
        if source.is_file() and source != destination.resolve():
            if destination.exists() and sha256_file(destination) != sha256_file(source):
                stem, suffix = destination.stem, destination.suffix
                destination = destination.with_name(f"{stem}-{datetime.now():%H%M%S}{suffix}")
            shutil.copy2(source, destination)
        elif not source.is_file() and args.allow_missing:
            destination = version_dir / (args.name or source.name)
    file_record = {
        "path": str(destination),
        "source": str(source),
        "role": args.role,
        "sha256": sha256_file(destination) if destination.is_file() else None,
        "exists": destination.is_file(),
        "added_at": now_iso(),
    }
    version.setdefault("files", []).append(file_record)
    asset["updated_at"] = now_iso()
    record_event(data, "asset.add_file", {"asset_id": args.id, "path": str(destination)})
    atomic_save(path, data)
    print(destination)
    return 0


def command_bump_asset(args: argparse.Namespace) -> int:
    path, data = load_project(args.project)
    asset = get_asset(data, args.id)
    previous = current_version(asset)
    new_number = int(asset["current_version"]) + 1
    root = Path(data["project"]["root"])
    version_dir = root / "assets" / asset["type"] / asset["asset_id"] / f"v{new_number:03d}"
    version_dir.mkdir(parents=True, exist_ok=True)
    new_version = {
        "version": new_number,
        "status": args.status,
        "directory": str(version_dir),
        "prompt": args.prompt if args.prompt is not None else previous.get("prompt", ""),
        "note": args.note or "",
        "files": [],
        "created_at": now_iso(),
    }
    asset.setdefault("versions", []).append(new_version)
    asset["current_version"] = new_number
    asset["status"] = args.status
    asset["updated_at"] = now_iso()
    affected = []
    for shot in data.get("shots", []):
        if args.id in shot.get("asset_refs", []):
            shot["review_required"] = True
            affected.append(shot.get("shot_id"))
    record_event(data, "asset.bump", {"asset_id": args.id, "version": new_number, "affected_shots": affected})
    atomic_save(path, data)
    print(json.dumps({"asset_id": args.id, "version": new_number, "affected_shots": affected}, ensure_ascii=False))
    return 0


def command_set_asset_status(args: argparse.Namespace) -> int:
    path, data = load_project(args.project)
    asset = get_asset(data, args.id)
    asset["status"] = args.status
    current_version(asset)["status"] = args.status
    asset["updated_at"] = now_iso()
    record_event(data, "asset.status", {"asset_id": args.id, "status": args.status})
    atomic_save(path, data)
    print(f"{args.id}={args.status}")
    return 0


def default_hold(duration: float) -> float:
    base = 0.4 if duration < 8 else 0.7 if duration <= 15 else 1.2
    return round(min(base, max(0.1, duration * 0.2)), 2)


def command_add_shot(args: argparse.Namespace) -> int:
    path, data = load_project(args.project)
    if args.duration <= 0:
        raise ValueError("duration must be greater than zero")
    sequence_ids = {item.get("sequence_id") for item in data.get("sequences", [])}
    if args.sequence not in sequence_ids:
        raise KeyError(f"sequence not found: {args.sequence}")
    known_assets = {item.get("asset_id") for item in data.get("assets", [])}
    asset_refs = list(dict.fromkeys(args.asset or []))
    missing = [asset_id for asset_id in asset_refs if asset_id not in known_assets]
    if missing:
        raise KeyError(f"unknown asset IDs: {', '.join(missing)}")
    shot_id = next_id(data.setdefault("shots", []), "shot_id", "SH")
    prior = [shot for shot in data["shots"] if shot.get("sequence_id") == args.sequence]
    start_time = round(sum(float(shot.get("duration", 0)) for shot in prior), 3)
    source_video = str(Path(args.source_video).expanduser().resolve()) if args.source_video else None
    hold = default_hold(args.duration)
    shot: dict[str, Any] = {
        "shot_id": shot_id,
        "sequence_id": args.sequence,
        "order": len(prior) + 1,
        "time_start": start_time,
        "duration": args.duration,
        "action": args.action,
        "dialogue": args.dialogue or "",
        "shot_size": args.shot_size,
        "camera_angle": args.camera_angle,
        "camera_move": args.camera_move,
        "lens_mm": args.lens_mm,
        "lighting": args.lighting or "",
        "palette": args.palette or "",
        "transition": args.transition,
        "start_state": args.start_state or "",
        "end_state": args.end_state or "",
        "start_hold": args.start_hold if args.start_hold is not None else hold,
        "end_hold": args.end_hold if args.end_hold is not None else hold,
        "asset_refs": asset_refs,
        "backend": args.backend,
        "seedance_mode": args.seedance_mode,
        "source_video": source_video,
        "edit_instructions": args.edit_instructions or "",
        "extension_direction": args.extension_direction,
        "review_required": False,
        "created_at": now_iso(),
    }
    shot["inferred_seedance_mode"] = infer_seedance_mode(shot)
    data["shots"].append(shot)
    record_event(data, "shot.add", {"shot_id": shot_id, "sequence_id": args.sequence})
    atomic_save(path, data)
    print(json.dumps({"shot_id": shot_id, "inferred_seedance_mode": shot["inferred_seedance_mode"]}))
    return 0


def command_link_asset(args: argparse.Namespace) -> int:
    path, data = load_project(args.project)
    get_asset(data, args.asset)
    shot = get_shot(data, args.shot)
    refs = shot.setdefault("asset_refs", [])
    if args.asset not in refs:
        refs.append(args.asset)
    shot["inferred_seedance_mode"] = infer_seedance_mode(shot)
    shot["review_required"] = True
    record_event(data, "shot.link_asset", {"shot_id": args.shot, "asset_id": args.asset})
    atomic_save(path, data)
    print(f"{args.shot}<-{args.asset}")
    return 0


def validate_project(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"unsupported schema_version: {data.get('schema_version')!r}")
    project = data.get("project", {})
    root = Path(project.get("root", ""))
    if not root.is_dir():
        errors.append(f"project root missing: {root}")
    identity = data.get("identity", {})
    if identity.get("identity_mode") not in IDENTITY_MODES:
        errors.append(f"invalid identity_mode: {identity.get('identity_mode')}")
    if identity.get("generation_backend") not in BACKENDS:
        errors.append(f"invalid generation_backend: {identity.get('generation_backend')}")
    asset_ids: set[str] = set()
    for asset in data.get("assets", []):
        asset_id = asset.get("asset_id")
        if not asset_id or asset_id in asset_ids:
            errors.append(f"duplicate or missing asset_id: {asset_id}")
            continue
        asset_ids.add(asset_id)
        if asset.get("type") not in ASSET_PREFIXES:
            errors.append(f"{asset_id}: invalid type {asset.get('type')}")
        try:
            version = current_version(asset)
        except KeyError as exc:
            errors.append(str(exc))
            continue
        if not Path(version.get("directory", "")).is_dir():
            errors.append(f"{asset_id}: current version directory missing")
        for file_record in version.get("files", []):
            if not Path(file_record.get("path", "")).is_file():
                errors.append(f"{asset_id}: managed file missing: {file_record.get('path')}")
    sequence_ids = {item.get("sequence_id") for item in data.get("sequences", [])}
    shot_ids: set[str] = set()
    for shot in data.get("shots", []):
        shot_id = shot.get("shot_id")
        if not shot_id or shot_id in shot_ids:
            errors.append(f"duplicate or missing shot_id: {shot_id}")
        shot_ids.add(str(shot_id))
        if shot.get("sequence_id") not in sequence_ids:
            errors.append(f"{shot_id}: missing sequence {shot.get('sequence_id')}")
        for asset_id in shot.get("asset_refs", []):
            if asset_id not in asset_ids:
                errors.append(f"{shot_id}: missing asset {asset_id}")
    return errors


def command_validate(args: argparse.Namespace) -> int:
    _, data = load_project(args.project)
    errors = validate_project(data)
    payload = {"ok": not errors, "errors": errors}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Create a managed director project")
    p.add_argument("--root", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--slug")
    p.add_argument("--aspect-ratio", default="16:9")
    p.add_argument("--resolution", default="720p")
    p.add_argument("--fps", type=float, default=24.0)
    p.add_argument("--language", default="zh-CN")
    p.add_argument("--identity-mode", choices=sorted(IDENTITY_MODES), default="fictional")
    p.add_argument("--backend", choices=sorted(BACKENDS), default="codex_imagegen")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=command_init)

    p = sub.add_parser("set-identity", help="Change project identity routing")
    p.add_argument("--project", required=True)
    p.add_argument("--identity-mode", choices=sorted(IDENTITY_MODES), required=True)
    p.add_argument("--backend", choices=sorted(BACKENDS))
    p.add_argument("--seedance-eligible", type=parse_bool)
    p.set_defaults(func=command_set_identity)

    p = sub.add_parser("add-sequence", help="Add a sequence")
    p.add_argument("--project", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--notes")
    p.set_defaults(func=command_add_sequence)

    p = sub.add_parser("add-asset", help="Create a versioned asset")
    p.add_argument("--project", required=True)
    p.add_argument("--type", choices=sorted(ASSET_PREFIXES), required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--prompt")
    p.add_argument("--note")
    p.add_argument("--status", choices=sorted(ASSET_STATUSES), default="draft")
    p.add_argument("--seedance-eligible", type=parse_bool)
    p.add_argument("--depends-on", action="append")
    p.set_defaults(func=command_add_asset)

    p = sub.add_parser("add-file", help="Copy/register a file in the current asset version")
    p.add_argument("--project", required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--name")
    p.add_argument("--role", default="reference")
    p.add_argument("--no-copy", action="store_true")
    p.add_argument("--allow-missing", action="store_true")
    p.set_defaults(func=command_add_file)

    p = sub.add_parser("bump-asset", help="Create a new asset version and mark dependent shots")
    p.add_argument("--project", required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--prompt")
    p.add_argument("--note")
    p.add_argument("--status", choices=sorted(ASSET_STATUSES), default="draft")
    p.set_defaults(func=command_bump_asset)

    p = sub.add_parser("set-asset-status", help="Update current asset status")
    p.add_argument("--project", required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--status", choices=sorted(ASSET_STATUSES), required=True)
    p.set_defaults(func=command_set_asset_status)

    p = sub.add_parser("add-shot", help="Add a storyboard shot")
    p.add_argument("--project", required=True)
    p.add_argument("--sequence", required=True)
    p.add_argument("--duration", type=float, required=True)
    p.add_argument("--action", required=True)
    p.add_argument("--dialogue")
    p.add_argument("--shot-size", default="MS")
    p.add_argument("--camera-angle", default="eye-level")
    p.add_argument("--camera-move", default="locked")
    p.add_argument("--lens-mm", type=float, default=50.0)
    p.add_argument("--lighting")
    p.add_argument("--palette")
    p.add_argument("--transition", default="cut")
    p.add_argument("--start-state")
    p.add_argument("--end-state")
    p.add_argument("--start-hold", type=float)
    p.add_argument("--end-hold", type=float)
    p.add_argument("--asset", action="append")
    p.add_argument("--backend", choices=sorted(BACKENDS), default="seedance_2_5")
    p.add_argument("--seedance-mode", choices=sorted(SEEDANCE_MODES), default="auto")
    p.add_argument("--source-video")
    p.add_argument("--edit-instructions")
    p.add_argument("--extension-direction", choices=["forward", "backward"])
    p.set_defaults(func=command_add_shot)

    p = sub.add_parser("link-asset", help="Link an asset to an existing shot")
    p.add_argument("--project", required=True)
    p.add_argument("--shot", required=True)
    p.add_argument("--asset", required=True)
    p.set_defaults(func=command_link_asset)

    p = sub.add_parser("validate", help="Run structural validation")
    p.add_argument("--project", required=True)
    p.set_defaults(func=command_validate)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
