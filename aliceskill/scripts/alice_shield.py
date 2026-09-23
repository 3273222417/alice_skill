#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice护盾（主动保护 · 防篡改层）
================================
保护对象：Alice技能核心文件（SKILL.md / config / references / scripts 关键件）。
保护动作：
  ① 基线指纹：扫描关键文件 SHA-256 → guard/baseline.json
  ② 巡查校验：对比当前哈希，发现篡改/污染 → 报警 + 自动恢复（可选）
  ③ 白名单：被 AI 或外部改动 → 按备案恢复，改动记录留痕
  ④ 定期巡检：--watch 持续监控（守护进程模式）

用法:
  python alice_shield.py init                     # 生成/更新基线指纹
  python alice_shield.py check                    # 一次性巡查
  python alice_shield.py watch --interval 60      # 持续守护（后台）
  python alice_shield.py restore                  # 从基线备份恢复关键文件
  python alice_shield.py status                   # 查看护盾状态
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
BASELINE = os.path.join(SKILL_DIR, "guard", "baseline.json")
BACKUP_DIR = os.path.join(os.path.dirname(SKILL_DIR), "alice_shield")

# 受保护关键文件（相对 SKILL_DIR）
PROTECTED = [
    "SKILL.md",
    "config/authorization.json",
    "config/command_aliases.json",
    "config/system_objects.json",
    "config/task_guard.json",
    "config/word_filter.json",
    "references/HELP.md",
    "references/MASTER_MANUAL.md",
    "references/battle_manual.md",
    "references/command_map.md",
    "scripts/rebuild_menu.py",
    "scripts/build_commands.py",
    "scripts/check_auth_policy.py",
    "scripts/counter_attack.py",
    "scripts/task_guard.py",
]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: str, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def save_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def load_baseline() -> dict:
    """兼容两种基线格式：扁平 {rel: sha}（alice_launch）与嵌套 {created_at, files}（alice_shield）。"""
    raw = load_json(BASELINE, {})
    if isinstance(raw, dict) and "files" in raw:
        return raw
    if isinstance(raw, dict) and raw:
        files = {}
        for rel, v in raw.items():
            if isinstance(v, str):
                p = os.path.join(SKILL_DIR, rel)
                files[rel] = {"sha256": v, "size": os.path.getsize(p) if os.path.isfile(p) else 0}
            elif isinstance(v, dict):
                files[rel] = v
        return {"created_at": "——（扁平基线，由 alice_launch 维护）", "files": files}
    return {"files": {}}


def collect_fingerprint() -> dict:
    fp = {}
    for rel in PROTECTED:
        p = os.path.join(SKILL_DIR, rel)
        if os.path.isfile(p):
            fp[rel] = {"sha256": sha256(p), "size": os.path.getsize(p)}
    return fp


def cmd_init(a) -> int:
    fp = collect_fingerprint()
    data = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": fp,
    }
    save_json(BASELINE, data)
    # 同步备份关键文件
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for rel in PROTECTED:
        p = os.path.join(SKILL_DIR, rel)
        if os.path.isfile(p):
            dst = os.path.join(BACKUP_DIR, rel.replace("/", "__"))
            shutil.copy2(p, dst)
    print(f"[✓] 护盾基线已建立: {len(fp)} 个关键文件指纹 + 备份")
    return 0


def cmd_check(a) -> int:
    base = load_baseline()
    if not base.get("files"):
        print("[!] 基线不存在，先运行 init")
        return 1
    cur = collect_fingerprint()
    changed = []
    missing = []
    for rel, meta in base["files"].items():
        if rel not in cur:
            missing.append(rel)
        elif cur[rel]["sha256"] != meta["sha256"]:
            changed.append(rel)
    ok = True
    if changed:
        ok = False
        print("[✗] 篡改/污染检测: %d 个文件被改动" % len(changed))
        for rel in changed:
            print("     - " + rel)
        if a.restore:
            for rel in changed:
                bak = os.path.join(BACKUP_DIR, rel.replace("/", "__"))
                if os.path.isfile(bak):
                    shutil.copy2(bak, os.path.join(SKILL_DIR, rel))
                    print("     [恢复] " + rel)
    if missing:
        ok = False
        print("[✗] 缺失文件: %d" % len(missing))
        for rel in missing:
            print("     - " + rel)
    if ok:
        print("[✓] 护盾巡查通过：关键文件全部完好")
    return 0 if ok else 1


def cmd_watch(a) -> int:
    print(f"[⏳] 护盾持续守护启动（每 {a.interval}s 巡检一次，Ctrl+C 停止）")
    round_n = 0
    try:
        while True:
            round_n += 1
            rc = cmd_check(type("A", (), {"restore": a.restore})())
            if rc != 0:
                print(f"  [第{round_n}轮] ⚠ 检测到异常，已{"自动恢复" if a.restore else "报警"}")
            time.sleep(a.interval)
    except KeyboardInterrupt:
        print("\n[✓] 护盾守护已停止")
    return 0


def cmd_status(a) -> int:
    base = load_baseline()
    if not base.get("files"):
        print("[!] 基线不存在")
        return 0
    cur = collect_fingerprint()
    good = sum(1 for rel in base["files"] if rel in cur and cur[rel]["sha256"] == base["files"][rel]["sha256"])
    print(f"[✓] 护盾状态: {good}/{len(base['files'])} 关键文件完好")
    print(f"    基线时间: {base.get('created_at', '—')}")
    print(f"    备份目录: {BACKUP_DIR}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Alice护盾（防篡改保护）")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("init").set_defaults(func=cmd_init)
    chk = sub.add_parser("check")
    chk.add_argument("--restore", action="store_true", help="发现篡改自动从备份恢复")
    chk.set_defaults(func=cmd_check)
    wt = sub.add_parser("watch")
    wt.add_argument("--interval", type=int, default=60)
    wt.add_argument("--restore", action="store_true")
    wt.set_defaults(func=cmd_watch)
    sub.add_parser("status").set_defaults(func=cmd_status)
    a = p.parse_args()
    if not hasattr(a, "func"):
        p.print_help()
        return 0
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
