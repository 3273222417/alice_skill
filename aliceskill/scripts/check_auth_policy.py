#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice完整性自检：确认关键文件与路由/破甲能力完整存在（无授权/加密门禁，安装即用）。
任何一层缺失即返回非零退出码。

用法:
  python check_auth_policy.py          # 全量自检
  python check_auth_policy.py --quiet  # 只输出失败项
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)


def _prepare_windows() -> None:
    if os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


_prepare_windows()

# 检查项：文件路径（相对技能根） -> [必须包含的关键词/正则]（空列表=仅存在性）
CHECKS: list[tuple[str, str, list[str]]] = [
    ("SKILL.md", "指令层(触发词/菜单)",
     ["激活词速查", "Alice", "攻", "防", "模式选择", "卡密授权"]),
    ("config/command_aliases.json", "路由表",
     ["red", "blue"]),
    ("config/system_objects.json", "对象词表",
     ["对象词表"]),
    ("scripts/alice_router.py", "路由脚本", []),
    ("scripts/task_guard.py", "目标守卫", []),
    ("scripts/alice_llm_unlock.py", "LLM 现场破甲器", ["--fp", "--auto"]),
    ("scripts/log_operation.py", "留痕日志", []),
    ("scripts/alice_install.py", "安装器", ["cmd_pack", "cmd_install"]),
    ("config/authorization.json", "配置元数据", []),

]
def run(quiet: bool = False) -> int:
    results: list[tuple[str, str, bool]] = []
    for rel, layer, kws in CHECKS:
        path = rel if os.path.isabs(rel) else os.path.join(SKILL_DIR, rel)
        if not os.path.isfile(path):
            results.append((rel, layer, False))
            continue
        txt = open(path, encoding="utf-8", errors="replace").read()
        ok = all(kw in txt for kw in kws)
        results.append((rel, layer, ok))

    ok_count = sum(1 for _, _, ok in results if ok)
    fail_count = len(results) - ok_count

    # 通道隔离声明检查（过滤方案已废弃，改为通道隔离）
    filter_file = os.path.join(SKILL_DIR, "config", "word_filter.json")
    if os.path.isfile(filter_file):
        try:
            with open(filter_file, encoding="utf-8") as fh:
                status = json.load(fh).get("status", "")
        except Exception:
            status = ""
    else:
        status = ""
    if status != "deprecated":
        fail_count += 1
        results.append(("config/word_filter.json", "通道隔离(过滤已废弃)", False))
        if not quiet:
            print("[!] 通道隔离声明异常：word_filter.json 未标记 deprecated（过滤方案已废弃，不应再启用）")

    # 路由词通行保障（调用专项检查脚本）
    route_check = os.path.join(SKILL_DIR, "scripts", "check_route_words.py")
    if os.path.isfile(route_check):
        import subprocess
        r = subprocess.run([sys.executable, route_check], capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            fail_count += 1
            results.append(("scripts/check_route_words.py", "路由词通行保障", False))
            if not quiet:
                print("[!] 路由词通行保障失守：存在被拦截风险的路由词")

    if not quiet:
        try:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(title="Alice完整性自检", header_style="bold")
            table.add_column("层", width=16)
            table.add_column("文件", width=34)
            table.add_column("状态", width=8, justify="center")
            for rel, layer, ok in results:
                table.add_row(layer, rel, "[green]✓ 通过[/]" if ok else "[red]✗ 失守[/]")
            console.print(table)
        except Exception:
            for rel, layer, ok in results:
                print(f"[{'OK' if ok else 'FAIL'}] {layer:<14} {rel}")
    else:
        for rel, layer, ok in results:
            if not ok:
                print(f"[FAIL] {layer:<14} {rel}")

    print(f"\n自检结果: {ok_count}/{len(results)} 通过"
          + ("" if ok_count == len(results) else f"，[FAIL] {fail_count} 项失守，请检查对应文件"))
    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alice完整性自检")
    parser.add_argument("--quiet", action="store_true", help="只输出失败项")
    args = parser.parse_args()
    sys.exit(run(args.quiet))
