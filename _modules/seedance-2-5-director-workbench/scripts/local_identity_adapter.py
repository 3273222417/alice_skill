#!/usr/bin/env python3
"""Probe, recommend, and package local consented-identity backend jobs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
DEFAULT_MODEL_ROOT = LOCAL_APPDATA / "无限破甲" / "ai-models"

BACKENDS: dict[str, dict[str, Any]] = {
    "photomaker_v2": {
        "display_name": "PhotoMaker V2",
        "repo_folder": "PhotoMaker",
        "url": "https://github.com/TencentARC/PhotoMaker",
        "license": "Apache-2.0 code",
        "min_vram_gb": 12,
        "tasks": ["still"],
        "entrypoints": ["gradio_demo/app_v2.py", "gradio_demo/app.py"],
        "notes": [
            "Default still-image identity route on a 12GB GPU.",
            "PhotoMaker prompts require the trigger word 'img' after the class word.",
        ],
    },
    "pulid_flux": {
        "display_name": "PuLID-FLUX",
        "repo_folder": "PuLID",
        "url": "https://github.com/ToTheBeginning/PuLID",
        "license": "Apache-2.0 code",
        "min_vram_gb": 11,
        "tasks": ["still"],
        "entrypoints": ["app_flux.py"],
        "notes": [
            "12GB route uses aggressive offload, FP8, and CPU ONNX provider.",
            "FP8 can reduce face detail compared with BF16 and is slow with aggressive offload.",
        ],
    },
    "liveportrait": {
        "display_name": "LivePortrait",
        "repo_folder": "LivePortrait",
        "url": "https://github.com/KlingAIResearch/LivePortrait",
        "license": "MIT code; bundled/default InsightFace model terms require separate review",
        "min_vram_gb": 8,
        "tasks": ["portrait-animation"],
        "entrypoints": ["inference.py"],
        "notes": ["Source portrait plus driving video/template; optimized for face/head motion, not full-body action."],
    },
    "consisid": {
        "display_name": "ConsisID",
        "repo_folder": "ConsisID",
        "url": "https://github.com/PKU-YuanGroup/ConsisID",
        "license": "Apache-2.0 code",
        "min_vram_gb": 7,
        "default_vram_gb": 44,
        "tasks": ["full-video"],
        "entrypoints": ["infer.py", "app.py"],
        "notes": [
            "Default pipeline is far above 12GB; use all offload and VAE optimizations.",
            "Optimized route is experimental, much slower, and may reduce quality.",
        ],
    },
    "infiniteyou": {
        "display_name": "InfiniteYou",
        "repo_folder": "InfiniteYou",
        "url": "https://github.com/bytedance/InfiniteYou",
        "license": "Review repository and checkpoint terms before use",
        "min_vram_gb": 16,
        "tasks": ["still"],
        "entrypoints": [],
        "notes": ["Reserved for cloud/high-memory expansion; not recommended on RTX 3060 12GB."],
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_capture(argv: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def gpu_probe() -> dict[str, Any]:
    result = run_capture(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader,nounits",
        ]
    )
    if not result or result.returncode != 0 or not result.stdout.strip():
        return {"available": False, "name": None, "memory_mib": 0, "memory_gb": 0.0, "driver": None}
    line = result.stdout.strip().splitlines()[0]
    parts = [part.strip() for part in line.split(",")]
    try:
        memory_mib = int(float(parts[1]))
    except (IndexError, ValueError):
        memory_mib = 0
    return {
        "available": True,
        "name": parts[0] if parts else None,
        "memory_mib": memory_mib,
        "memory_gb": round(memory_mib / 1024, 2),
        "driver": parts[2] if len(parts) > 2 else None,
    }


def find_entrypoint(repo: Path, candidates: list[str]) -> Path | None:
    for candidate in candidates:
        path = repo / candidate
        if path.is_file():
            return path
    return None


def probe(model_root: Path) -> dict[str, Any]:
    gpu = gpu_probe()
    backends: dict[str, Any] = {}
    for key, spec in BACKENDS.items():
        repo = model_root / spec["repo_folder"]
        entrypoint = find_entrypoint(repo, spec["entrypoints"])
        min_vram = float(spec["min_vram_gb"])
        if key == "photomaker_v2" and gpu["memory_gb"] >= min_vram:
            vram_status = "recommended"
        elif key == "pulid_flux" and gpu["memory_gb"] >= min_vram:
            vram_status = "edge_optimized"
        elif key == "consisid" and min_vram <= gpu["memory_gb"] < float(spec["default_vram_gb"]):
            vram_status = "optimized_slow"
        else:
            vram_status = "sufficient" if gpu["memory_gb"] >= min_vram else "insufficient"
        backends[key] = {
            "name": spec["display_name"],
            "repo": str(repo),
            "repo_present": repo.is_dir(),
            "entrypoint": str(entrypoint) if entrypoint else None,
            "launcher_ready": bool(entrypoint),
            "vram_status": vram_status,
            "minimum_vram_gb": min_vram,
            "license": spec["license"],
        }
    return {
        "model_root": str(model_root),
        "python": sys.executable,
        "python_version": sys.version.split()[0],
        "conda": shutil.which("conda"),
        "ffmpeg": shutil.which("ffmpeg"),
        "gpu": gpu,
        "backends": backends,
    }


def recommendation(task: str, reference_count: int, commercial: bool, model_root: Path) -> dict[str, Any]:
    state = probe(model_root)
    vram = float(state["gpu"]["memory_gb"])
    reasons: list[str] = []
    alternates: list[str] = []
    warnings: list[str] = []

    if task == "still":
        if vram >= 11:
            selected = "photomaker_v2"
            reasons.append("PhotoMaker V2 is the default still route and fits the documented ~11GB minimum.")
        else:
            selected = "photomaker_v2"
            warnings.append("Detected VRAM is below the documented PhotoMaker minimum; use stronger offload/cloud hardware.")
        if reference_count <= 1 and vram >= 11:
            alternates.append("pulid_flux")
            reasons.append("PuLID-FLUX is the single-reference, prompt-editable fallback.")
        elif vram >= 11:
            alternates.append("pulid_flux")
        if vram < 16:
            warnings.append("InfiniteYou is marked unavailable locally because the optimized route still targets about 16GB VRAM.")
    elif task == "portrait-animation":
        selected = "liveportrait"
        reasons.append("LivePortrait matches portrait speech, blink, expression, and small head-motion animation.")
        if commercial:
            warnings.append("Replace/review default InsightFace models before commercial use; their terms are separate from MIT code.")
    elif task == "full-video":
        selected = "consisid"
        reasons.append("ConsisID is the full identity-preserving local video route.")
        warnings.append("Enable model/sequential CPU offload and VAE slicing/tiling; expect slow inference and possible quality loss.")
        if vram < 7:
            warnings.append("Detected VRAM is below the documented 5–7GB fully optimized allocation range.")
    else:
        raise ValueError(f"unsupported task: {task}")

    selected_state = state["backends"][selected]
    if not selected_state["repo_present"]:
        warnings.append(f"Repository is not installed at {selected_state['repo']}; recommendation is ready but execution is not.")
    return {
        "task": task,
        "reference_count": reference_count,
        "selected": selected,
        "selected_name": BACKENDS[selected]["display_name"],
        "alternates": alternates,
        "hardware": state["gpu"],
        "reasons": reasons,
        "warnings": warnings,
        "launcher_ready": selected_state["launcher_ready"],
        "repo": selected_state["repo"],
    }


def launcher_for(backend: str, repo: Path, sources: list[Path], driving: Path | None) -> tuple[list[str], Path | None]:
    spec = BACKENDS[backend]
    if not spec["entrypoints"]:
        return [], None
    entrypoint = find_entrypoint(repo, spec["entrypoints"]) or repo / spec["entrypoints"][0]
    relative = str(entrypoint.relative_to(repo))
    if backend == "photomaker_v2":
        return [sys.executable, relative], entrypoint
    if backend == "pulid_flux":
        return [sys.executable, relative, "--aggressive_offload", "--fp8", "--onnx_provider", "cpu"], entrypoint
    if backend == "liveportrait":
        if not sources or not driving:
            return [], entrypoint
        return [sys.executable, relative, "-s", str(sources[0]), "-d", str(driving)], entrypoint
    if backend == "consisid":
        if relative.lower().endswith("infer.py"):
            return [sys.executable, relative, "--model_path", "BestWishYsh/ConsisID-preview"], entrypoint
        return [sys.executable, relative], entrypoint
    return [], entrypoint


def build_job(args: argparse.Namespace, model_root: Path) -> dict[str, Any]:
    if args.backend == "infiniteyou":
        raise ValueError("InfiniteYou is a reserved cloud/high-memory option, not a local 12GB launcher")
    spec = BACKENDS[args.backend]
    if args.task not in spec["tasks"]:
        raise ValueError(f"{args.backend} does not support task {args.task}; supported: {', '.join(spec['tasks'])}")
    sources = [Path(value).expanduser().resolve() for value in (args.source or [])]
    driving = Path(args.driving).expanduser().resolve() if args.driving else None
    if not args.allow_missing:
        missing = [str(path) for path in sources if not path.is_file()]
        if driving and not driving.is_file():
            missing.append(str(driving))
        if missing:
            raise FileNotFoundError("missing job inputs: " + ", ".join(missing))
    if args.backend == "liveportrait" and (not sources or not driving):
        raise ValueError("LivePortrait requires at least one --source and --driving")
    if args.backend in {"photomaker_v2", "pulid_flux", "consisid"} and not sources:
        raise ValueError(f"{args.backend} requires at least one --source identity image")

    repo = Path(args.repo).expanduser().resolve() if args.repo else model_root / spec["repo_folder"]
    argv, entrypoint = launcher_for(args.backend, repo, sources, driving)
    gpu = gpu_probe()
    warnings = list(spec["notes"])
    if args.backend == "photomaker_v2" and " img" not in f" {args.prompt} ":
        warnings.append("PhotoMaker trigger word 'img' is not visible in the prompt; place it after the person class word.")
    if args.backend == "consisid":
        warnings.append("Official infer.py exposes model_path but not every memory switch as CLI flags; apply required_runtime_settings in the pipeline/runtime before rendering.")
    job = {
        "schema_version": "1.0",
        "created_at": now_iso(),
        "status": "planned",
        "identity_mode": "consented_local_identity",
        "seedance_eligible": False,
        "task": args.task,
        "backend": args.backend,
        "backend_name": spec["display_name"],
        "source_images": [str(path) for path in sources],
        "driving": str(driving) if driving else None,
        "prompt": args.prompt,
        "negative_prompt": args.negative_prompt or "",
        "output": str(Path(args.output).expanduser().resolve()) if args.output else None,
        "repo": str(repo),
        "entrypoint": str(entrypoint) if entrypoint else None,
        "launcher": argv,
        "launcher_command_windows": subprocess.list2cmdline(argv) if argv else None,
        "launcher_ready": bool(entrypoint and entrypoint.is_file() and argv),
        "hardware": gpu,
        "required_runtime_settings": {
            "enable_model_cpu_offload": args.backend == "consisid",
            "enable_sequential_cpu_offload": args.backend == "consisid",
            "vae_enable_slicing": args.backend == "consisid",
            "vae_enable_tiling": args.backend == "consisid",
            "fp8": args.backend == "pulid_flux",
            "aggressive_offload": args.backend == "pulid_flux",
            "onnx_provider": "cpu" if args.backend == "pulid_flux" else None,
        },
        "license": spec["license"],
        "source_url": spec["url"],
        "warnings": warnings,
    }
    return job


def write_job(path_value: str, job: dict[str, Any]) -> Path:
    path = Path(path_value).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-root", default=str(DEFAULT_MODEL_ROOT))
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("probe", help="Inspect GPU, tools, repository paths, and launcher readiness")
    p.add_argument("--json-output")

    p = sub.add_parser("recommend", help="Recommend a backend for the current hardware")
    p.add_argument("--task", choices=["still", "portrait-animation", "full-video"], required=True)
    p.add_argument("--reference-count", type=int, default=1)
    p.add_argument("--commercial", action="store_true")
    p.add_argument("--json-output")

    p = sub.add_parser("build-job", help="Write a reproducible local identity job packet")
    p.add_argument("--backend", choices=sorted(BACKENDS), required=True)
    p.add_argument("--task", choices=["still", "portrait-animation", "full-video"], required=True)
    p.add_argument("--source", action="append")
    p.add_argument("--driving")
    p.add_argument("--prompt", required=True)
    p.add_argument("--negative-prompt")
    p.add_argument("--output")
    p.add_argument("--repo")
    p.add_argument("--job-json", required=True)
    p.add_argument("--allow-missing", action="store_true")
    p.add_argument("--execute", action="store_true")
    return parser


def emit(payload: dict[str, Any], output: str | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        path = Path(output).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(text)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    model_root = Path(args.model_root).expanduser().resolve()
    try:
        if args.command == "probe":
            emit(probe(model_root), args.json_output)
            return 0
        if args.command == "recommend":
            if args.reference_count < 1:
                raise ValueError("reference-count must be at least 1")
            emit(recommendation(args.task, args.reference_count, args.commercial, model_root), args.json_output)
            return 0
        if args.command == "build-job":
            job = build_job(args, model_root)
            path = write_job(args.job_json, job)
            print(path)
            if args.execute:
                if not job["launcher_ready"]:
                    raise RuntimeError("launcher is not ready; install the repository and verify its entrypoint")
                result = subprocess.run(job["launcher"], cwd=job["repo"], check=False)
                return int(result.returncode)
            return 0
        raise ValueError(f"unknown command: {args.command}")
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
