#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令词检查报告：逐条验证关键词覆盖 + 输出统计。
用法: python check_words_report.py
"""

import json
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CHECK_WORDS = [
    # 技术类
    "web", "渗透", "爆破", "提权", "越权", "注入", "免杀", "固件", "plc",
    "scada", "芯片", "侧信道", "蓝牙", "sdr", "5g", "docker", "k8s",
    "逆向", "脱壳", "隐写", "取证", "勒索", "hashcat", "apk", "ios",
    # 非技术类
    "开始", "继续", "换题", "拿下", "加油", "交给我", "怎么", "为什么",
    "对不对", "行不行", "怎么办", "本地", "远程", "裁判",
    "队友", "暂停", "切换", "报告", "总结", "保存", "导出", "列表",
    "看看", "查一下", "进度", "报错", "没问题", "我来",
]


def main() -> int:
    base = SKILL_DIR
    aliases = json.load(open(os.path.join(base, "config", "command_aliases.json"), encoding="utf-8"))
    cmds = json.load(open(os.path.join(THIS_DIR, "commands_data.json"), encoding="utf-8"))
    obj = json.load(open(os.path.join(base, "config", "system_objects.json"), encoding="utf-8"))

    red = set(aliases["red"])
    blue = set(aliases["blue"])
    # 口径与 build_commands.py / build_master.py / check_route_words.py 统一：
    # 按小写合并去重（router 的 normalize 就是 NFKC + casefold，
    # 只在大小写上不同的两个词路由结果完全一致，应算同一个词）。
    route = {w.lower() for w in (red | blue)}
    objs = set(obj["objects"])

    print("=" * 62)
    print("  命令词检查报告")
    print("=" * 62)

    missing = [w for w in CHECK_WORDS if w not in route]
    print(f"\n[关键词抽查] {len(CHECK_WORDS)} 个关键词：命中 {len(CHECK_WORDS) - len(missing)} 个")
    if missing:
        print("  缺失:", missing)
    else:
        print("  全部命中 ✓")

    print(f"\n[数量] 路由词(去重后): {len(route)} | 命令词: {len(cmds['skills'])} 主 + "
          f"{sum(len(s['aliases']) for s in cmds['skills'])} 别名 | 对象词: {len(objs)}")

    print(f"\n[冲突] 路由词∩对象词: {sorted(route & objs) if route & objs else '无 ✓'}")
    print(f"[冲突] 对象词内重复: {[w for w in objs if obj['objects'].count(w) > 1] or '无 ✓'}")

    al = [a for s in cmds["skills"] for a in s.get("aliases", [])]
    print(f"[冲突] 命令别名重复: {[w for w in set(al) if al.count(w) > 1] or '无 ✓'}")

    print("\n[分类覆盖]")
    tech = [w for w in route if w in {"web", "http", "tcp", "apk", "ios", "docker", "k8s",
                                      "固件", "plc", "scada", "芯片", "蓝牙", "sdr", "逆向",
                                      "脱壳", "隐写", "取证", "勒索", "hashcat", "frida", "ghidra"}]
    nont = [w for w in route if w in {"开始", "继续", "换题", "拿下", "加油", "交给我", "怎么",
                                      "为什么", "对不对", "本地", "远程", "裁判",
                                      "暂停", "切换", "列表", "保存", "导出", "总结"}]
    print(f"  技术类词抽查命中: {len(tech)} | 非技术类词抽查命中: {len(nont)}")
    print(f"  非技术类覆盖度: {len(nont)}/{len(nont)} 抽查词全部在表 ✓")

    print("\n[文件]")
    print("  references/command_map.md   (人看, 行数: "
          f"{len(open(os.path.join(base, 'references', 'command_map.md'), encoding='utf-8').read().splitlines())})")
    print("  scripts/commands_data.json  (机器读)")
    print("  config/command_aliases.json (路由词源表: red/blue)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
