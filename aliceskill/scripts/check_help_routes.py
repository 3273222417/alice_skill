#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证帮助/教程类路由词。"""
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

WANT = ["help", "帮助", "说明书", "使用教程", "操作指南", "怎么用", "教教我", "示例", "usage", "tutorial", "guide", "你会什么", "技能列表", "完整菜单", "怎么打", "战术"]


def main() -> int:
    cmds = json.load(open(CMD, encoding="utf-8"))
    aliases = {a["command"]: a["targets"] for a in cmds["aliases"]}
    skills = json.load(open(SKILLS, encoding="utf-8"))["skills"]
    names = {s["name"] for s in skills}
    ok = True
    for w in WANT:
        got = aliases.get(w, [])
        dead = [t for t in got if t not in names]
        if w not in aliases or dead:
            ok = False
            print(f"  [FAIL] {w}: {got}" + (f" 死链{dead}" if dead else " 缺失"))
        else:
            print(f"  [OK ] {w} -> {got}")
    print("总路由词:", len(aliases))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
