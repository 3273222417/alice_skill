#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 LLM 攻击路由词。"""
from __future__ import annotations

import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CMD = os.path.join(THIS_DIR, "commands_data.json")
SKILLS = os.environ.get("ALICE_DATA") or os.path.join(THIS_DIR, "skills_data.json")

WANT = [
    "AI攻击", "提示注入", "越狱", "间接注入", "上下文诱导", "篡改上下文",
    "污染上下文", "绕过滤器", "多轮诱导", "知识库投毒", "工具投毒",
    "多模态注入", "记忆注入", "诱导路由", "载荷库", "直接注入",
    "隐藏指令", "诱导", "编码混淆", "系统提示提取",
    "mcp投毒", "工具描述注入", "返回值注入", "目标劫持", "任务注入",
    "优先级覆盖", "记忆操纵", "上下文溢出", "指纹探测", "高级攻击",
]


def main() -> int:
    cmds = json.load(open(CMD, encoding="utf-8"))
    aliases = {a["command"].lower(): a["targets"] for a in cmds["aliases"]}
    skills = json.load(open(SKILLS, encoding="utf-8"))["skills"]
    names = {s["name"] for s in skills}
    ok = True
    for w in WANT:
        got = aliases.get(w.lower(), [])
        dead = [t for t in got if t not in names]
        if not got or dead:
            ok = False
            print(f"  [FAIL] {w}: {got}" + (f" 死链{dead}" if dead else " 缺失"))
        else:
            print(f"  [OK ] {w} -> {got[:3]}")
    print("总路由词:", len(aliases))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
