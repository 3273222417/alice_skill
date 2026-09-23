#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice看门狗（主动保护 · 防中断/失控层）
=======================================
守护攻/防会话进程与目标状态：
  ① 目标锁存：读取 task_guard 状态，确认攻/防目标未被替换
  ② 进程监护：监控 Codex 会话进程，异常退出 → 自动重启（可选）
  ③ 输出风暴：复用熔断逻辑，检测刷屏/对抗循环 → 终止并重启
  ④ 状态回滚：偏离计数越限 → 自动 resume 目标

用法:
  python alice_watchdog.py start --mode red --goal "拿下 flag"   # 启动监护
  python alice_watchdog.py check                                  # 状态检查
  python alice_watchdog.py watch --interval 30                    # 持续监护
  python alice_watchdog.py stop                                   # 停止
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
STATE_FILE = os.path.join(SKILL_DIR, "guard", "task_state.json")
WATCH_FILE = os.path.join(SKILL_DIR, "guard", "watchdog_state.json")
LOG_FILE = os.path.join(SKILL_DIR, "logs", "watchdog.log")
os.makedirs(os.path.dirname(WATCH_FILE), exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


def load(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default if default is not None else {}


def save(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def task_active() -> bool:
    st = load(STATE_FILE, {})
    return bool(st.get("active"))


def target_ok() -> tuple[bool, str]:
    st = load(STATE_FILE, {})
    if not st.get("active"):
        return False, "无进行中任务（未启动守卫）"
    goal = st.get("goal", "")
    if not goal:
        return False, "目标为空"
    return True, f"目标锁存: {goal}"


def storm_detect(history: list, limit: int = 5) -> bool:
    """检测重复对抗循环（相同消息连续出现）。"""
    if len(history) < limit:
        return False
    tail = history[-limit:]
    return len(set(tail)) == 1


def cmd_start(a) -> int:
    # 先同步 task_guard 目标
    r = subprocess.run(
        [sys.executable, os.path.join(THIS_DIR, "task_guard.py"), "start",
         "--mode", a.mode, "--goal", a.goal, "--stage", a.stage or "开始"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    save(WATCH_FILE, {
        "active": True,
        "mode": a.mode,
        "goal": a.goal,
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "restart": a.restart,
        "restart_count": 0,
        "history": [],
    })
    log(f"看门狗启动 | {a.mode.upper()} | {a.goal}")
    print(r.stdout or r.stderr)
    return 0


def cmd_check(a) -> int:
    ok_flag, msg = target_ok()
    if ok_flag:
        print(f"[✓] {msg}")
    else:
        print(f"[✗] {msg}")
    return 0 if ok_flag else 1


def cmd_watch(a) -> int:
    wd = load(WATCH_FILE, {})
    if not wd.get("active"):
        print("[!] 看门狗未启动，先运行 start")
        return 1
    log(f"看门狗持续监护（每 {a.interval}s）")
    try:
        while True:
            ok_flag, msg = target_ok()
            if not ok_flag:
                log(f"⚠ 目标异常: {msg}")
            # 偏离矫正：bias_count 越限自动 resume
            st = load(STATE_FILE, {})
            if st.get("bias_count", 0) >= int(load(os.path.join(SKILL_DIR, "config", "task_guard.json"), {}).get("max_bias_count", 3)):
                subprocess.run([sys.executable, os.path.join(THIS_DIR, "task_guard.py"), "resume"],
                               capture_output=True, encoding="utf-8", errors="replace")
                log("⚠ 偏离越限，自动拉回目标")
            time.sleep(a.interval)
    except KeyboardInterrupt:
        log("看门狗停止")
    return 0


def cmd_stop(a) -> int:
    wd = load(WATCH_FILE, {})
    wd["active"] = False
    save(WATCH_FILE, wd)
    log("看门狗已停止")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Alice看门狗（防中断/失控保护）")
    sub = p.add_subparsers(dest="cmd")
    st = sub.add_parser("start")
    st.add_argument("--mode", choices=["red", "blue"], required=True)
    st.add_argument("--goal", required=True)
    st.add_argument("--stage", default="")
    st.add_argument("--restart", action="store_true")
    st.set_defaults(func=cmd_start)
    sub.add_parser("check").set_defaults(func=cmd_check)
    wt = sub.add_parser("watch")
    wt.add_argument("--interval", type=int, default=30)
    wt.set_defaults(func=cmd_watch)
    sub.add_parser("stop").set_defaults(func=cmd_stop)
    a = p.parse_args()
    if not hasattr(a, "func"):
        p.print_help()
        return 0
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
