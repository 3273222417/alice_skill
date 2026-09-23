#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")

import shutil

backup = r"C:\Users\Administrator\.codex\alice_backup\scripts\alice_install.py"
cur = r"C:\Users\Administrator\.codex\skills\alice\scripts\alice_install.py"

# 1) 恢复备份
src = open(backup, encoding="utf-8").read()
open(cur, "w", encoding="utf-8").write(src)
print("restored from backup, size:", len(src))

# 2) 在 write_watermark 函数后插入 inject_skill_watermark
anchor = '        json.dump(mark, fh, ensure_ascii=False, indent=2)\n    return p\n'
new_fn = '''        json.dump(mark, fh, ensure_ascii=False, indent=2)
    return p


def inject_skill_watermark(target: str, info: dict) -> str:
    """在 SKILL.md 顶部注入防伪水印注释（倒卖溯源 + 绑定安装器）。"""
    skill_md = os.path.join(target, "SKILL.md")
    if not os.path.isfile(skill_md):
        return ""
    with open(skill_md, encoding="utf-8") as fh:
        content = fh.read()
    mark = (
        "<!--\\n"
        "  ALICE-WATERMARK: 本技能由Alice安装器（防伪绑定版）安装。\\n"
        "  序列号: {serial}\\n"
        "  持有人: {owner}\\n"
        "  封印时间: {sealed_at}\\n"
        "  脱离安装器/倒卖/拆分必被溯源。\\n"
        "-->\\n"
    ).format(serial=info.get("serial", "N/A"), owner=info.get("owner", "N/A"),
             sealed_at=info.get("sealed_at", "N/A"))
    if "ALICE-WATERMARK" not in content:
        content = mark + content
        with open(skill_md, "w", encoding="utf-8") as fh:
            fh.write(content)
        return skill_md
    return ""
'''
if anchor in src:
    src = src.replace(anchor, new_fn)
    print("inject_skill_watermark inserted")
else:
    print("ANCHOR NOT FOUND")

# 3) 在 cmd_install 防伪写入处加水印调用
old_block = '''        wm = write_watermark(target, seal_info)
        ok(f"防伪标识已写入: {wm}")'''
new_block = '''        wm = write_watermark(target, seal_info)
        ok(f"防伪标识已写入: {wm}")
        wm2 = inject_skill_watermark(target, seal_info)
        if wm2:
            ok(f"SKILL.md 防伪水印已注入: {wm2}")'''
if old_block in src:
    src = src.replace(old_block, new_block)
    print("watermark call added")
else:
    print("CALL BLOCK NOT FOUND")

open(cur, "w", encoding="utf-8").write(src)
print("final size:", len(src))
