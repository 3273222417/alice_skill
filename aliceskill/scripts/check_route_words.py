#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文路由词通行检查：验证 32 个路由词在攻/防模式下绝不被任何判定拦截。
  ① 全部存在于命令表 command_map.md
  ② 不进入 system_objects.json 对象词表（不会被误判为授权系统对象）
  ③ 全部在 task_guard 通行白名单（双保险，命令表失效也能放行）
用法:
  python check_route_words.py
"""

from __future__ import annotations

import json
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    aliases = load(os.path.join(SKILL_DIR, "config", "command_aliases.json"))
    raw = list(aliases.get("red", {}).keys()) + list(aliases.get("blue", {}).keys())
    # 与 build_commands.py / build_master.py 口径统一：按小写合并去重后的路由词数。
    # raw 相加会把同名/大小写不同的词算多次（1751 vs 1726），三处数字对不上。
    seen_lower: dict[str, str] = {}
    for w in raw:
        seen_lower.setdefault(w.lower(), w)
    words = list(seen_lower.values())
    obj = load(os.path.join(SKILL_DIR, "config", "system_objects.json"))
    tg = load(os.path.join(SKILL_DIR, "config", "task_guard.json"))
    cmds_data = load(os.path.join(THIS_DIR, "commands_data.json"))
    md_lower = open(os.path.join(SKILL_DIR, "references", "command_map.md"), encoding="utf-8").read().lower()

    # task_guard 命令集 = 命令表路由词(aliases) ∪ 通行白名单
    guard_cmds = set(a.get("command", "").lower() for a in cmds_data.get("aliases", []))
    guard_cmds |= set(tg.get("whitelist", []))

    checks = {
        "命令表存在": [w for w in words if f"`{w.lower()}`" not in md_lower],
        "不在对象词表": [w for w in words if w.lower() in {o.lower() for o in obj.get("objects", [])}],
        "在守卫命令集": [w for w in words if w.lower() not in guard_cmds],
    }
    ok = True
    for name, bad in checks.items():
        if bad:
            ok = False
            print(f"[✗] {name} 失守: {bad}")
        else:
            print(f"[✓] {name} 通过")
    print(f"\n路由词总数: {len(words)}（red {len(aliases.get('red', {}))} + blue "
          f"{len(aliases.get('blue', {}))}，同名合并去重后） | 通行保障: "
          f"{'全部通过' if ok else '存在失守'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
