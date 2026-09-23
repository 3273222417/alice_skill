#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
刷新Alice SKILL.md 的技能总菜单（第 3 节）+ 顶部计数，数据源 scripts/skills_data.json。
只替换第 3 节整块，其余章节（0/1/2/4/5/6/7）原样保留。
用法: python refresh_skill_menu.py [--check]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
DATA = os.environ.get("ALICE_DATA") or os.path.join(THIS_DIR, "skills_data.json")
SKILLMD = os.path.join(SKILL_DIR, "SKILL.md")
CATS = {
    "A": "总入口与方法论", "B": "信息收集与协议", "C": "Web/API 渗透与 JS 逆向",
    "D": "二进制逆向", "E": "漏洞利用与提权", "F": "恶意软件分析", "G": "移动端安全",
    "H": "密码学与取证", "I": "固件与 IoT", "J": "游戏安全与防御对抗",
    "K": "浏览器与桌面自动化", "L": "云与容器", "M": "业务与内容制作",
    "N": "技能工程与平台", "Z": "其他/未分类",
}


def render_block(skills: list[dict]) -> str:
    out = [f"## 3. 技能总菜单（自动生成，共 {len(CATS)} 类）", ""]
    for code, cn in CATS.items():
        group = [s for s in skills if s["category"] == code]
        group.sort(key=lambda x: int("".join(ch for ch in x["code"] if ch.isdigit()) or 0))
        out.append(f"### {code}. {cn}（{len(group)}）")
        out.append("")
        if not group:
            out += ["_暂无_", ""]
            continue
        for s in group:
            flag = " ⚡内置" if s.get("builtin") else ""
            desc = (s.get("desc") or "").replace("\n", " ").strip()
            out.append(f"- {s['code']}. {s['name']} — {desc}{flag}")
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    data = json.load(open(DATA, encoding="utf-8"))
    skills = data["skills"]
    md = open(SKILLMD, encoding="utf-8").read()

    start = md.index("## 3. 技能总菜单")
    end = md.index("## 4. 路由规则")
    block = render_block(skills)
    new_md = md[:start] + block + "\n" + md[end:]
    new_md = new_md.replace("共收录 **310** 个技能（15 类）",
                            f"共收录 **{len(skills)}** 个技能（{len(CATS)} 类）")
    if a.check:
        cur = md[start:end]
        listed = sum(1 for ln in cur.splitlines() if ln.startswith("- ") and ". " in ln[:8])
        ok = listed == len(skills)
        print(("[✓] " if ok else "[✗] ") +
              f"SKILL.md 第 3 节：列出 {listed} 条 / skills_data 共 {len(skills)} 条")
        return 0 if ok else 1

    if new_md == md:
        print("[=] SKILL.md 无需变更")
        return 0
    open(SKILLMD, "w", encoding="utf-8", newline="\n").write(new_md)
    print(f"[OK] SKILL.md 第 3 节已刷新：{len(skills)} 技能 / {len(CATS)} 类")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
