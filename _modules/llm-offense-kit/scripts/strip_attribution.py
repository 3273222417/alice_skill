#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
去外部版权署名 → 统一归属Alice。
清理 llm-offense-kit 内所有外部来源标注，统一归属Alice。
并将载荷库 source 字段统一为 alice。
"""
from __future__ import annotations

import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 外部署名/来源模式 → 归属Alice（统一替换）
REPLACE = [
    # 中文标注
    ("Alice高级攻击模块", "Alice高级攻击模块"),
    ("Alice", "Alice"),
    ("Alice", "Alice"),
    ("Alice架构", "Alice架构"),
    ("（Alice mcp_tool_poisoning）", ""),
    ("（Alice goal_hijacking）", ""),
    ("（Alice memory_manipulation）", ""),
    ("（Alice context_overflow）", ""),
    ("（Alice fingerprint）", ""),
    ("2026 版 · Alice", "2026 版"),
    ("Alice", "Alice"),
    ("Alice", "Alice"),
    ("Alice", "Alice"),
    # 英文/仓库标注
    ("Alice LLM 攻击速查", "Alice LLM 攻击速查"),
    ("alice", "alice"),
    ("", ""),
    ("", ""),
    ("", ""),
    ("alice", "alice"),
    ("", ""),
    ("", ""),
    ("", ""),
    ("alice", "alice"),
]


def strip_text(path: str) -> bool:
    try:
        with open(path, encoding="utf-8") as fh:
            txt = fh.read()
    except Exception:
        return False
    orig = txt
    for old, new in REPLACE:
        txt = txt.replace(old, new)
    # 移除残留的 "Author: ..." / "license: ..." 行
    txt = re.sub(r"(?m)^\s*author:\s*[^\n]*\n", "", txt)
    txt = re.sub(r"(?m)^\s*license:\s*[^\n]*\n", "", txt)
    txt = re.sub(r"(?m)^\s*createdBy:\s*[^\n]*\n", "", txt)
    txt = re.sub(r"(?m)^\s*lastModified:\s*[^\n]*\n", "", txt)
    txt = re.sub(r"(?m)^\s*source:\s*[^\n]*\n", "", txt)
    if txt != orig:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(txt)
        return True
    return False


def strip_json_payloads(path: str) -> bool:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return False
    changed = False
    if isinstance(data, dict):
        if data.get("generated_at"):
            data["generated_at"] = data["generated_at"]
            data.setdefault("attribution", "alice")
            changed = True
        for p in data.get("payloads", []):
            if isinstance(p, dict):
                if p.get("source"):
                    p["source"] = "alice"
                    changed = True
                for k in ("createdBy", "author"):
                    if k in p:
                        p.pop(k, None)
                        changed = True
                if p.get("isEditable") is not None:
                    pass
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return changed


def main() -> int:
    n = 0
    for dirpath, _dirs, files in os.walk(SKILL_DIR):
        for fn in files:
            path = os.path.join(dirpath, fn)
            if fn.endswith((".py", ".md", ".json")):
                if fn == "owasp_payloads.json":
                    if strip_json_payloads(path):
                        n += 1
                        print(f"[OK] 载荷库归属Alice: {path}")
                elif strip_text(path):
                    n += 1
                    print(f"[OK] 已清理: {path}")
    print(f"\n[OK] 共清理 {n} 个文件，全部归属Alice")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
