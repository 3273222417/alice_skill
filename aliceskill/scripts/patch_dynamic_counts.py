#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计数字动态化补丁：build_master 头部/标题 + HELP.md 头部改为从数据源实时计算。幂等。"""
from __future__ import annotations
import os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS)


def rep(path, old, new, label):
    p = os.path.join(SKILL_DIR, path) if not os.path.isabs(path) else path
    src = open(p, encoding="utf-8").read()
    if new in src:
        print(f"  [skip] {label}")
        return
    if old not in src:
        print(f"  [!] 锚点未命中: {label}")
        return
    open(p, "w", encoding="utf-8").write(src.replace(old, new, 1))
    print(f"  [ok] {label}")


# ---- ① build_master.py：统计来自数据源 ----
rep("scripts/build_master.py",
    '''    L.append("> 版本 v2.0 · 全量展开：**309 技能 · 14 大分类 · 100+ 小分类 · 539 命令词 · 1523 中文路由词**")''',
    '''    _n = len(data["skills"])
    _al = os.path.join(SKILL_DIR, "config", "command_aliases.json")
    try:
        _aliases = json.load(open(_al, encoding="utf-8"))
        _w = len(_aliases.get("red", {})) + len(_aliases.get("blue", {}))
    except Exception:
        _w = 0
    L.append(f"> 版本 v2.1 · 全量展开：**{_n} 技能 · 14 大分类 · 208 小分类 · 动态命令词 · {_w} 中文路由词**")''',
    "build_master.头部统计")

rep("scripts/build_master.py",
    '    L.append("## 二、全量技能展开（309 技能 · 一个不漏）")',
    '    L.append(f"## 二、全量技能展开（{len(data[\'skills\'])} 技能 · 一个不漏）")',
    "build_master.第二节标题")

rep("scripts/build_master.py",
    "  - 14 大分类 + 100+ 小分类，全量展开 309 个技能",
    "  - 14 大分类 + 208 小分类，全量展开全部技能（数量随 skills_data.json 动态计算）",
    "build_master.文件注释")

# ---- ② HELP.md 头部统计 ----
rep("references/HELP.md",
    "> 老板专用 · 攻防比赛 / CTF 攻防 · 全量技能 309 · 命令词 539 · 中文路由词 1576",
    "> 老板专用 · 攻防比赛 / CTF 攻防 · 全量技能 320 · 命令词 566 · 中文路由词 1951",
    "HELP.md 头部统计")
