#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""吸收后收尾补丁：①命令别名噪声头过滤 ②路由同分时取最长命中词。幂等。"""
from __future__ import annotations
import os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS = os.path.dirname(os.path.abspath(__file__))

def patch(fname, old, new, label):
    p = os.path.join(THIS, fname)
    src = open(p, encoding="utf-8").read()
    if new in src:
        print(f"  [skip] {label}: 已应用")
        return
    if old not in src:
        print(f"  [!] {label}: 锚点未命中")
        return
    open(p, "w", encoding="utf-8").write(src.replace(old, new, 1))
    print(f"  [ok] {label}: 已应用")

# ① build_commands.py：过滤噪声别名头（re / windows / tool 等过短或过泛）
patch("build_commands.py",
'''EXTRA_ALIASES = {''',
'''# 噪声别名头：过短或过泛，会污染命令表（不生成这些别名）
NOISE_HEADS = {"re", "windows", "tool", "tools", "flow", "crack", "license", "sandbox"}

EXTRA_ALIASES = {''',
"build_commands.NOISE_HEADS")

patch("build_commands.py",
'''    head = base.split("-")[0]
    if len(head) >= 2 and head not in al and head != base:
        al.append(head)''',
'''    head = base.split("-")[0]
    if len(head) >= 3 and head not in NOISE_HEADS and head not in al and head != base:
        al.append(head)''',
"build_commands.gen_aliases.head")

# ② alice_router.py：同分时优先最长命中词（避免长意图被短词抢路由）
patch("alice_router.py",
'''            score = (sum(w for _, w in sh), len(sh), -len(cat), skill["id"])''',
'''            # 同分裁定：命中词越多越优先，再比最长命中词（长意图压短词）
            score = (sum(w for _, w in sh), len(sh), max(len(t) for t, _ in sh),
                     -len(cat), skill["id"])''',
"alice_router.score.tiebreak")
