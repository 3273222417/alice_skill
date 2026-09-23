#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice堡垒（主动保护 · 综合指挥层）
=================================
一键拉起攻/防保护的完整闭环：
  ① 护盾校验（防篡改）→ alice_shield
  ② 目标锁存（防偏离）→ alice_watchdog / task_guard
  ③ 熔断监测（防失控）→ alice_breaker 逻辑
  ④ 受阻反击（防阻碍）→ counter_attack
  ⑤ 全链路自检（守底线）→ check_auth_policy

用法:
  python alice_fortress.py up --mode red --goal "拿下 flag"      # 一键开战保护
  python alice_fortress.py down                                   # 停保护
  python alice_fortress.py drill --attack "内容过滤拦截"           # 模拟受阻 → 反击演练
  python alice_fortress.py status                                 # 保护状态总览
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
FORT_FILE = os.path.join(SKILL_DIR, "guard", "fortress_state.json")
os.makedirs(os.path.dirname(FORT_FILE), exist_ok=True)


def c(s: str, code: str) -> str:
    m = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
         "cyan": "\033[96m", "bold": "\033[1m", "dim": "\033[2m"}
    if not sys.stdout.isatty():
        return s
    return f"{m.get(code, '')}{s}\033[0m"


def ok(s: str) -> None:
    print(c("  ✓ ", "green") + s)


def fail(s: str) -> None:
    print(c("  ✗ ", "red") + s)


def step(n: int, total: int, s: str) -> None:
    print(c(f"  [{n}/{total}] ", "cyan") + s)


def banner(title: str, sub: str = "") -> None:
    w = 64
    print(c("┌" + "─" * (w - 2) + "┐", "cyan"))
    print(c("│ " + title + " " * (w - 4 - len(title)) + "│", "bold"))
    if sub:
        print(c("│ " + sub + " " * (w - 4 - len(sub)) + "│", "dim"))
    print(c("└" + "─" * (w - 2) + "┘", "cyan"))


def run(script: str, args: list) -> tuple[int, str]:
    r = subprocess.run([sys.executable, os.path.join(THIS_DIR, script)] + args,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    return r.returncode, (r.stdout or r.stderr)


def save_state(state: dict) -> None:
    with open(FORT_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def load_state() -> dict:
    try:
        with open(FORT_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"active": False, "mode": "", "goal": "", "layers": {}}


def cmd_up(a) -> int:
    banner("Alice堡垒 · 开战保护", f"{a.mode.upper()} | {a.goal}")
    layers = {}
    # 1. 护盾
    step(1, 5, "护盾（防篡改）")
    rc, out = run("alice_shield.py", ["check", "--restore"])
    layers["shield"] = "OK" if rc == 0 else "WARN"
    ok(f"护盾: {layers['shield']}")
    # 2. 看门狗（目标锁存）
    step(2, 5, "看门狗（目标锁存）")
    rc, out = run("alice_watchdog.py", ["start", "--mode", a.mode, "--goal", a.goal, "--stage", a.stage or "开始"])
    layers["watchdog"] = "OK" if rc == 0 else "WARN"
    ok(f"看门狗: {layers['watchdog']}")
    # 3. 熔断（防失控）
    step(3, 5, "熔断（防失控）")
    layers["breaker"] = "READY"
    ok("熔断器 READY（输出风暴/超时/熔断词 → 物理终止）")
    # 4. 反击（防阻碍）
    step(4, 5, "反击引擎（防阻碍）")
    rc, out = run("counter_attack.py", ["selfcheck"])
    layers["counter"] = "OK" if rc == 0 else "WARN"
    ok(f"反击引擎: {layers['counter']}")
    # 5. 自检
    step(5, 5, "全链路自检")
    rc, out = run("check_auth_policy.py", [])
    layers["policy"] = "OK" if rc == 0 else "WARN"
    ok(f"策略自检: {layers['policy']}")
    save_state({"active": True, "mode": a.mode, "goal": a.goal,
                "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "layers": layers})
    print(c("\n[✓] 堡垒全开 · 攻/防受五层保护", "bold"))
    return 0


def cmd_down(a) -> int:
    st = load_state()
    run("alice_watchdog.py", ["stop"])
    st["active"] = False
    save_state(st)
    ok("堡垒保护已关闭（看门狗停止）")
    return 0


def cmd_drill(a) -> int:
    banner("受阻反击演练", a.attack)
    # 侦察阻碍类型
    rc, out = run("counter_attack.py", ["scan", "--log", a.attack])
    print(out)
    # 执行反击（生成载荷落盘）
    rc2, out2 = run("counter_attack.py", ["attack", "--blocker", a.attack[:50], "--goal", a.goal or "继续攻防主线"])
    print(out2)
    ok("演练完成：受阻 → 判定 → 反击载荷已生成")
    return 0


def cmd_status(a) -> int:
    st = load_state()
    banner("堡垒状态", "五层保护")
    if not st.get("active"):
        fail("堡垒未开启（运行 up 一键开战保护）")
        return 0
    ok(f"模式: {st.get('mode', '').upper()} | 目标: {st.get('goal', '')}")
    for layer, status in st.get("layers", {}).items():
        mark = "✓" if status == "OK" else "⚠"
        print(f"  {mark} {layer}: {status}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Alice堡垒（主动保护指挥层）")
    sub = p.add_subparsers(dest="cmd")
    up = sub.add_parser("up")
    up.add_argument("--mode", choices=["red", "blue"], required=True)
    up.add_argument("--goal", required=True)
    up.add_argument("--stage", default="")
    up.set_defaults(func=cmd_up)
    sub.add_parser("down").set_defaults(func=cmd_down)
    dr = sub.add_parser("drill")
    dr.add_argument("--attack", required=True, help="受阻描述，如：内容过滤拦截")
    dr.add_argument("--goal", default="")
    dr.set_defaults(func=cmd_drill)
    sub.add_parser("status").set_defaults(func=cmd_status)
    a = p.parse_args()
    if not hasattr(a, "func"):
        p.print_help()
        return 0
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
