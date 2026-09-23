#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将「帮助/说明书/教程」类触发词并入 config/command_aliases.json 的 red 表。
映射到总入口技能（ctf-sandbox-orchestrator）+ 文档生成（docs-generator），
命中后Alice直接读 references/HELP.md 并按其引导执行。
用法: python add_help_routes.py
"""
from __future__ import annotations

import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIAS_FILE = os.path.join(SKILL_DIR, "config", "command_aliases.json")

NEW_RED = {
    "help": ["ctf-sandbox-orchestrator", "docs-generator"],
    "帮助": ["ctf-sandbox-orchestrator", "docs-generator"],
    "帮我": ["ctf-sandbox-orchestrator", "docs-generator"],
    "helpme": ["ctf-sandbox-orchestrator", "docs-generator"],
    "说明书": ["ctf-sandbox-orchestrator", "docs-generator"],
    "使用说明书": ["ctf-sandbox-orchestrator", "docs-generator"],
    "教程": ["ctf-sandbox-orchestrator", "docs-generator"],
    "使用教程": ["ctf-sandbox-orchestrator", "docs-generator"],
    "操作指南": ["ctf-sandbox-orchestrator", "docs-generator"],
    "指南": ["ctf-sandbox-orchestrator", "docs-generator"],
    "手册": ["ctf-sandbox-orchestrator", "docs-generator"],
    "总手册": ["ctf-sandbox-orchestrator", "docs-generator"],
    "全量手册": ["ctf-sandbox-orchestrator", "docs-generator"],
    "怎么用": ["ctf-sandbox-orchestrator", "docs-generator"],
    "怎么使用": ["ctf-sandbox-orchestrator", "docs-generator"],
    "咋用": ["ctf-sandbox-orchestrator", "docs-generator"],
    "如何使用": ["ctf-sandbox-orchestrator", "docs-generator"],
    "用不来": ["ctf-sandbox-orchestrator", "docs-generator"],
    "不懂怎么用": ["ctf-sandbox-orchestrator", "docs-generator"],
    "教教我": ["ctf-sandbox-orchestrator", "docs-generator"],
    "教一下": ["ctf-sandbox-orchestrator", "docs-generator"],
    "演示一下": ["ctf-sandbox-orchestrator", "docs-generator"],
    "举个例子": ["ctf-sandbox-orchestrator", "docs-generator"],
    "举例子": ["ctf-sandbox-orchestrator", "docs-generator"],
    "示例": ["ctf-sandbox-orchestrator", "docs-generator"],
    "demo": ["ctf-sandbox-orchestrator", "docs-generator"],
    "usage": ["ctf-sandbox-orchestrator", "docs-generator"],
    "tutorial": ["ctf-sandbox-orchestrator", "docs-generator"],
    "guide": ["ctf-sandbox-orchestrator", "docs-generator"],
    "documentation": ["ctf-sandbox-orchestrator", "docs-generator"],
    "whatcanudo": ["ctf-sandbox-orchestrator"],
    "你会什么": ["ctf-sandbox-orchestrator"],
    "你能干什么": ["ctf-sandbox-orchestrator"],
    "有什么技能": ["ctf-sandbox-orchestrator"],
    "有什么本事": ["ctf-sandbox-orchestrator"],
    "技能列表": ["ctf-sandbox-orchestrator"],
    "技能清单": ["ctf-sandbox-orchestrator"],
    "全部技能": ["ctf-sandbox-orchestrator"],
    "所有技能": ["ctf-sandbox-orchestrator"],
    "技能大全": ["ctf-sandbox-orchestrator"],
    "命令大全": ["ctf-sandbox-orchestrator"],
    "命令列表": ["ctf-sandbox-orchestrator"],
    "命令表": ["ctf-sandbox-orchestrator"],
    "菜单": ["ctf-sandbox-orchestrator"],
    "总菜单": ["ctf-sandbox-orchestrator"],
    "完整菜单": ["ctf-sandbox-orchestrator"],
    "展示菜单": ["ctf-sandbox-orchestrator"],
    "看一下菜单": ["ctf-sandbox-orchestrator"],
    "看菜单": ["ctf-sandbox-orchestrator"],
    "出战表": ["ctf-sandbox-orchestrator"],
    "开战表": ["ctf-sandbox-orchestrator"],
    "打法": ["ctf-sandbox-orchestrator"],
    "怎么打": ["ctf-sandbox-orchestrator"],
    "怎么防": ["ctf-sandbox-orchestrator"],
    "怎么赢": ["ctf-sandbox-orchestrator"],
    "策略": ["ctf-sandbox-orchestrator"],
    "战术": ["ctf-sandbox-orchestrator"],
}


def main() -> int:
    with open(ALIAS_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    red = data.setdefault("red", {})
    added, merged = 0, 0
    for word, targets in NEW_RED.items():
        if word in red:
            old = red[word]
            new = list(dict.fromkeys(old + targets))
            if new != old:
                red[word] = new
                merged += 1
        else:
            red[word] = list(targets)
            added += 1
    with open(ALIAS_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print(f"[OK] 帮助/教程路由词: 新增 {added} 合并 {merged} | red 总数 {len(red)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
