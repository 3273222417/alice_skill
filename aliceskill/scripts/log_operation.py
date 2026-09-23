#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比赛操作留痕日志：把攻防比赛中的操作记录追加到 logs/operations.log。

用法:
  python log_operation.py "开始侦察目标 https://target.example"
  python log_operation.py --phase red "利用完成，拿下 flag{...}"
  python log_operation.py --show         # 查看最近日志
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
LOG_DIR = os.path.join(SKILL_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "operations.log")


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


def load_auth() -> dict:
    path = os.path.join(SKILL_DIR, "config", "authorization.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="比赛操作留痕日志")
    parser.add_argument("message", nargs="?", help="操作内容")
    parser.add_argument("--phase", choices=["red", "blue", "menu"], default="red",
                        help="比赛阶段: red=进攻, blue=防守, menu=菜单")
    parser.add_argument("--target", help="目标标识（URL/样本路径/题目名）")
    parser.add_argument("--show", action="store_true", help="查看最近日志")
    args = parser.parse_args()

    auth = load_auth()

    if args.show:
        if not os.path.isfile(LOG_FILE):
            print("[⏳] 暂无操作日志")
            return 0
        lines = open(LOG_FILE, encoding="utf-8").readlines()
        tail = lines[-30:]
        print(f"=== 最近 {len(tail)} 条操作记录 ===")
        print("".join(tail))
        return 0

    if not args.message:
        parser.error("需要提供操作内容 message")

    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    phase_name = {"red": "攻/进攻", "blue": "防/防守", "menu": "菜单"}[args.phase]
    record = {
        "time": ts,
        "phase": args.phase,
        "phase_name": phase_name,
        "target": args.target or "",
        "action": args.message,
        "auth_id": auth.get("auth_id", ""),
    }
    line = (f"[{ts}] [{phase_name}] " +
            (f"目标:{args.target} | " if args.target else "") +
            f"{args.message} (授权编号:{record['auth_id']})")
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")

    if sys.stdout.isatty():
        try:
            from rich.console import Console
            from rich.panel import Panel

            Console().print(Panel(
                f"[bold green]✓ 已记录操作留痕[/]\n"
                f"[dim]{line}[/]",
                title="[bold]OPERATION LOG[/]",
                border_style="green",
            ))
        except Exception:
            print(f"[OK] {line}")
    else:
        print(f"[OK] {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
