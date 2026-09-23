#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")

p = r"C:\Users\Administrator\.codex\skills\alice\scripts\absorb_routes.py"
src = open(p, encoding="utf-8").read()
# 替换冲突词
pairs = [
    ('"卸载": ["skill-installer"]', '"卸载技能": ["skill-installer"]'),
    ('"部署": ["iac-security"]', '"部署方案": ["iac-security"]'),
    ('"补丁": ["patch-diff-exploit"]', '"补丁分析": ["patch-diff-exploit"]'),
    ('"快照": ["memory-forensics"]', '"快照取证": ["memory-forensics"]'),
]
for old, new in pairs:
    if old in src:
        src = src.replace(old, new)
        print("REPLACED:", old)
    else:
        print("NOT FOUND:", old)
open(p, "w", encoding="utf-8").write(src)
