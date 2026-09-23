#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证方法论路由词是否正确映射到 A 类技能。"""
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

WANT = {
    "方法论": ["alice-progressive", "research-rigor"],
    "系统化调试": ["hardware-breakpoint-observation"],
    "威胁建模": ["threat-modeling"],
    "头脑风暴": ["alice-progressive"],
    "计划编写": ["alice-progressive"],
    "完成前验证": ["research-rigor"],
    "方案拷问": ["grilling"],
}


def main() -> int:
    cmds = json.load(open(CMD, encoding="utf-8"))
    aliases = {a["command"]: a["targets"] for a in cmds["aliases"]}
    skills = json.load(open(SKILLS, encoding="utf-8"))["skills"]
    names = {s["name"] for s in skills}
    ok = True
    for word, targets in WANT.items():
        got = aliases.get(word, [])
        miss = [t for t in targets if t not in got]
        dead = [t for t in got if t not in names]
        status = "OK " if not miss and not dead else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"  [{status}] {word}: targets={got}" + (f" 缺{miss}" if miss else "") + (f" 死链{dead}" if dead else ""))
    print("总路由词:", len(aliases))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
