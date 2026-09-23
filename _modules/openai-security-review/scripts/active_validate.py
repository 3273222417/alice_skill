#!/usr/bin/env python3
"""Create a guarded active-validation plan for explicitly authorized testing."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

CLASSES = ("auth", "authz", "injection", "xss", "ssrf", "redirect", "file-handling")


def render_plan(target_url: str, classes: list[str]) -> str:
    class_lines = "\n".join(f"- {item}" for item in classes)
    return f"""# Authorized Active Validation Plan

This plan records authorization and prepares human-reviewed validation. It does not execute exploit payloads by itself. For guarded low-risk GET/OPTIONS probes, use `active_probe.py` with a separate confirmation step.

## Target

- URL: {target_url}
- Authorized classes:
{class_lines}

## Guardrails

- Use only test/staging/local environments.
- Use test accounts and synthetic data.
- Avoid destructive actions, brute force, persistence, data exfiltration, and production systems.
- Capture exact requests, responses, timestamps, and cleanup steps.
- Stop immediately if the target behaves unexpectedly or data integrity may be affected.

## Validation Slots

For each hypothesis, fill:

```text
Finding:
Class:
Preconditions:
Validation steps:
Expected safe signal:
Observed result:
Evidence path:
Cleanup:
Conclusion:
```
"""


def update_manifest(workspace: Path, authorized: bool) -> None:
    manifest_path = workspace / "state" / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["active_validation_authorized"] = authorized
    manifest.setdefault("stages", {})["active_validation"] = "authorized_plan_created" if authorized else "not_authorized"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an active validation plan with explicit authorization.")
    parser.add_argument("--workspace", required=True, help="Audit workspace")
    parser.add_argument("--target-url", required=True, help="Authorized target URL")
    parser.add_argument("--classes", default=",".join(CLASSES), help="Comma-separated validation classes")
    parser.add_argument("--i-am-authorized", action="store_true", help="Required acknowledgement of authorization")
    parser.add_argument("--execute", action="store_true", help="Reserved for project-specific validators; this script never executes exploit payloads")
    args = parser.parse_args()

    if not args.i_am_authorized:
        raise SystemExit("Refusing active validation plan without --i-am-authorized.")
    if args.execute:
        raise SystemExit("This public skill does not include an exploit runner. Create a project-specific validator with human-approved payloads.")

    selected = [item.strip() for item in args.classes.split(",") if item.strip()]
    invalid = [item for item in selected if item not in CLASSES]
    if invalid:
        raise SystemExit(f"Unsupported classes: {', '.join(invalid)}")

    workspace = Path(args.workspace).expanduser().resolve()
    (workspace / "state").mkdir(parents=True, exist_ok=True)
    (workspace / "evidence").mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "authorized": True,
        "created_utc": stamp,
        "target_url": args.target_url,
        "classes": selected,
        "execute": False,
        "note": "Plan-only mode. No exploit payloads were executed.",
    }

    (workspace / "state" / "active_validation.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (workspace / "evidence" / "active_validation_plan.md").write_text(render_plan(args.target_url, selected), encoding="utf-8")
    update_manifest(workspace, authorized=True)

    print(workspace / "evidence" / "active_validation_plan.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
