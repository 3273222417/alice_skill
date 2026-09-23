#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收尾补丁 ②：①alice_shield 兼容扁平基线格式 ②文档/注释里的技能计数改为动态。幂等。"""
from __future__ import annotations
import os, re, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS)


def patch(fname, old, new, label, root=None):
    p = os.path.join(root or THIS, fname)
    if not os.path.isfile(p):
        print(f"  [!] {label}: 文件不存在 {p}")
        return
    src = open(p, encoding="utf-8").read()
    if new in src:
        print(f"  [skip] {label}: 已应用")
        return
    if old not in src:
        print(f"  [!] {label}: 锚点未命中")
        return
    open(p, "w", encoding="utf-8").write(src.replace(old, new, 1))
    print(f"  [ok] {label}: 已应用")


# ① alice_shield：兼容 alice_launch 生成的扁平基线（{rel: sha}）
patch("alice_shield.py",
'''def collect_fingerprint() -> dict:''',
'''def load_baseline() -> dict:
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


def collect_fingerprint() -> dict:''',
"alice_shield.load_baseline")

patch("alice_shield.py",
'''    base = load_json(BASELINE, {})
    if not base.get("files"):
        print("[!] 基线不存在，先运行 init")
        return 1''',
'''    base = load_baseline()
    if not base.get("files"):
        print("[!] 基线不存在，先运行 init")
        return 1''',
"alice_shield.cmd_check")

patch("alice_shield.py",
'''    base = load_json(BASELINE, {})
    if not base.get("files"):
        print("[!] 基线不存在")
        return 0''',
'''    base = load_baseline()
    if not base.get("files"):
        print("[!] 基线不存在")
        return 0''',
"alice_shield.cmd_status")

# ② 动态计数：脚本注释里的固定技能数
patch("alice_contract.py", "技能覆盖（14 类 / 310 技能", "技能覆盖（14 类 / 全量技能", "alice_contract.docstring")
patch("alice_router.py", "数据源：skills_data.json（Alice 310 技能）", "数据源：skills_data.json（Alice全量技能）", "alice_router.docstring")
patch("alice_router.py", "使用说明书：**全部技能一个不漏", "使用说明书：**全部技能一个不漏", "noop")
print("[完成] 收尾补丁 ② 就绪")
