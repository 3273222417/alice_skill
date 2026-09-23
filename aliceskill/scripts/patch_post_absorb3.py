#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收尾补丁 ④：①3.9 脱壳小方面移到 3.4 之后（编号有序）②修 refresh_skill_menu --check 判定。幂等。"""
from __future__ import annotations
import os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS = os.path.dirname(os.path.abspath(__file__))

# ① 手册小方面顺序：把 3.9 脱壳 移到 3.4 之后
p = os.path.join(THIS, "build_manual.py")
src = open(p, encoding="utf-8").read()
moved = '''    "3.2 差分与补丁": ["binary-diff", "patch-diff-exploit"],
            "3.9 脱壳流程编排": ["re-flow-unpack"],'''
target = '''    "3.2 差分与补丁": ["binary-diff", "patch-diff-exploit"],'''
if moved in src:
    src = src.replace(moved, target, 1)
    anchor = '''            "3.4 文件解析": ["competition-file-parser-chain", "competition-reverse-pwn"],'''
    if anchor in src:
        src = src.replace(anchor, anchor + '''
            "3.5 脱壳流程编排": ["re-flow-unpack"],''', 1)
    print("  [ok] build_manual: 3.9 -> 3.5 顺序修正")
else:
    print("  [skip] build_manual: 顺序已修正")
open(p, "w", encoding="utf-8").write(src)

# ② refresh_skill_menu --check 判定修正
p2 = os.path.join(THIS, "refresh_skill_menu.py")
s2 = open(p2, encoding="utf-8").read()
old = '''    if a.check:
        cur = md[start:end]
        ok = f"共 {len(skills)} 个技能" in md or f"（{len(skills)}）" in cur
        print(("[✓] " if ok else "[✗] ") + f"SKILL.md 第 3 节技能数 = {len(skills)}")
        return 0 if ok else 1'''
new = '''    if a.check:
        cur = md[start:end]
        listed = sum(1 for ln in cur.splitlines() if ln.startswith("- ") and ". " in ln[:8])
        ok = listed == len(skills)
        print(("[✓] " if ok else "[✗] ") +
              f"SKILL.md 第 3 节：列出 {listed} 条 / skills_data 共 {len(skills)} 条")
        return 0 if ok else 1'''
if old in s2:
    open(p2, "w", encoding="utf-8").write(s2.replace(old, new, 1))
    print("  [ok] refresh_skill_menu: --check 判定已修正")
else:
    print("  [skip] refresh_skill_menu: 已是新判定")
