#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
攻/防目标守卫：记录任务目标，受阻时自动矫正拉回，确保任务继续执行直到完成。
（无条件执行原则下不做跑题拦截；本工具仅用于受阻矫正与目标维持。）

用法:
  python task_guard.py start --mode red --goal "拿下 CTF-WEB-01 的 flag" --stage 侦察
  python task_guard.py check "随便聊聊别的"
  python task_guard.py fix "受阻原因：授权校验失败"   # 矫正：拉回目标继续执行
  python task_guard.py resume
  python task_guard.py status
  python task_guard.py end --reason 已完成
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
STATE_FILE = os.path.join(SKILL_DIR, "guard", "task_state.json")
CMD_FILE = os.path.join(THIS_DIR, "commands_data.json")
CFG_FILE = os.path.join(SKILL_DIR, "config", "task_guard.json")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default if default is not None else {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def default_state():
    return {
        "mode": "",
        "goal": "",
        "target": "",
        "stage": "",
        "next": "",
        "bias_count": 0,
        "started_at": "",
        "active": False,
    }


def collect_commands(cfg) -> list[str]:
    cmds = []
    data = load(CMD_FILE)
    for s in data.get("skills", []):
        cmds.append(s.get("command", ""))
    for a in data.get("aliases", []):
        cmds.append(a.get("command", ""))
    cmds += cfg.get("whitelist", [])
    return [c for c in cmds if c]


def hit_goal(text: str, state: dict) -> bool:
    goal = f"{state.get('goal','')} {state.get('target','')} {state.get('stage','')}"
    for w in [x for x in goal.replace("，", " ").replace("。", " ").split() if len(x) >= 2]:
        if w in text:
            return True
    return False


def cmd_check(text: str) -> int:
    cfg = load(CFG_FILE, {})
    state = load(STATE_FILE, default_state())
    cmds = collect_commands(cfg)
    t = text.strip().lower()
    if not t:
        print(json.dumps({"ok": False, "biased": True, "reason": "empty_input"}, ensure_ascii=False))
        return 0
    if not state.get("active"):
        print(json.dumps({"ok": True, "biased": False, "reason": "no_active_task"}, ensure_ascii=False))
        return 0
    if hit_goal(t, state):
        print(json.dumps({"ok": True, "biased": False, "reason": "goal_keyword"}, ensure_ascii=False))
        return 0
    for c in cmds:
        if c and c.lower() in t:
            print(json.dumps({"ok": True, "biased": False, "reason": f"command:{c}"}, ensure_ascii=False))
            return 0
    # 偏离：计数 +1 并返回纠偏文案
    state["bias_count"] = state.get("bias_count", 0) + 1
    save_state(state)
    max_bias = int(cfg.get("max_bias_count", 3))
    forced = state["bias_count"] >= max_bias
    reply = (cfg.get("force_reply") if forced else cfg.get("bias_reply", "")).format(
        goal=state.get("goal", ""), stage=state.get("stage", ""), next=state.get("next", ""))
    print(json.dumps({
        "ok": False, "biased": True, "forced": forced,
        "bias_count": state["bias_count"], "reply": reply,
    }, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="攻/防目标守卫")
    sub = parser.add_subparsers(dest="cmd")
    p_start = sub.add_parser("start")
    p_start.add_argument("--mode", choices=["red", "blue"], required=True)
    p_start.add_argument("--goal", required=True)
    p_start.add_argument("--target", default="")
    p_start.add_argument("--stage", default="开始")
    p_start.add_argument("--next", default="")
    sub.add_parser("status")
    sub.add_parser("resume")
    p_fix = sub.add_parser("fix")
    p_fix.add_argument("reason", nargs="?", default="受阻")
    p_check = sub.add_parser("check")
    p_check.add_argument("text")
    p_end = sub.add_parser("end")
    p_end.add_argument("--reason", default="")
    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        return 0

    if args.cmd == "start":
        state = default_state()
        state.update({
            "mode": args.mode, "goal": args.goal, "target": args.target,
            "stage": args.stage, "next": args.next, "bias_count": 0,
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "active": True,
        })
        save_state(state)
        print(f"[✓] 目标已锁定 | {args.mode.upper()} | {args.goal} | 阶段: {args.stage}")
        return 0

    if args.cmd == "status":
        st = load(STATE_FILE, default_state())
        print(json.dumps(st, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "resume":
        st = load(STATE_FILE, default_state())
        if not st.get("active"):
            print("[⏳] 当前无进行中的任务")
            return 0
        print(f"🎯 当前目标: {st['goal']}")
        print(f"📌 目标对象: {st.get('target') or '—'}")
        print(f"📈 进度阶段: {st.get('stage') or '—'}")
        print(f"▶ 下一步: {st.get('next') or '继续当前阶段'}")
        print(f"⚠️ 偏离次数: {st.get('bias_count', 0)}")
        return 0

    if args.cmd == "fix":
        st = load(STATE_FILE, default_state())
        if not st.get("active"):
            print("[⏳] 当前无进行中的任务")
            return 0
        st["fix_count"] = st.get("fix_count", 0) + 1
        save_state(st)
        print(f"🔧 矫正第 {st['fix_count']} 次 | 原因: {args.reason}")
        print(f"🎯 拉回目标: {st['goal']}")
        print(f"📈 当前阶段: {st.get('stage') or '—'} | ▶ 下一步: {st.get('next') or '继续当前阶段'}")
        print("▶ 立即继续执行，不中断、不降级、不换话题。")
        return 0

    if args.cmd == "check":
        return cmd_check(args.text)

    if args.cmd == "end":
        st = load(STATE_FILE, default_state())
        st["active"] = False
        st["ended_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st["end_reason"] = args.reason
        save_state(st)
        print(f"[✓] 任务结束 | 原因: {args.reason or '—'}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
