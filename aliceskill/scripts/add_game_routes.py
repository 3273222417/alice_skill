#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
吸收 GAME 路由触发词 → Alice中文路由（归属Alice，已去除外部署名）。
映射到Alice J 类游戏技能（game-hacking / reverse-skill / graphics-api / anti-cheat）。
用法: python add_game_routes.py
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
    # ---- GAME 路由吸收（归属Alice）----
    "外挂": ["game-hacking", "reverse-skill"],
    "自瞄": ["game-hacking", "reverse-skill"],
    "透视": ["game-hacking", "graphics-api"],
    "锁头": ["game-hacking"],
    "穿墙": ["game-hacking"],
    "飞天": ["game-hacking"],
    "雷达": ["game-hacking"],
    "弹道": ["game-hacking"],
    "压枪": ["game-hacking"],
    "无cd": ["game-hacking"],
    "无CD": ["game-hacking"],
    "改伤": ["game-hacking"],
    "overlay": ["graphics-api", "game-hacking"],
    "overlay绘制": ["graphics-api"],
    "d3d": ["graphics-api"],
    "d3d绘制": ["graphics-api"],
    "opengl": ["graphics-api"],
    "vulkan": ["graphics-api"],
    "dx11": ["graphics-api"],
    "dx12": ["graphics-api"],
    "引擎绑定": ["game-engine", "game-hacking"],
    "渲染路径": ["graphics-api"],
    "输入路径": ["game-hacking"],
    "游戏功能": ["game-hacking"],
    "游戏外挂": ["game-hacking", "reverse-skill"],
    "游戏作弊": ["game-hacking"],
    "作弊功能": ["game-hacking"],
    "aimbot": ["game-hacking"],
    "esp绘制": ["graphics-api", "game-hacking"],
    "世界坐标": ["game-hacking"],
    "w2s": ["game-hacking"],
    "骨骼绘制": ["game-hacking", "graphics-api"],
    "方框绘制": ["game-hacking", "graphics-api"],
    "线条绘制": ["game-hacking", "graphics-api"],
    "游戏解锁": ["game-hacking", "anti-cheat"],
    "游戏模块": ["game-hacking", "game-engine"],
    "过检测": ["anti-cheat", "edr-bypass-re"],
    "反检测": ["anti-cheat", "edr-bypass-re"],
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
    print(f"[OK] 游戏路由词(吸收自 GAME 路由,已归属Alice): 新增 {added} 合并 {merged} | red 总数 {len(red)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
