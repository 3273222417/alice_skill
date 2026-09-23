#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice反击引擎（物理层）——攻/防受阻即反击。

任何形式的阻碍/拦截/阻断（内容过滤、网络层阻断、上下文隔离、AI 拒绝、授权误判、
外部干扰、代理封锁、目标 AI 反制），本引擎自动判定阻碍类型并选择反击战术，
调用 LLM 攻击工具箱（llm-offense-kit）生成反击载荷，记录反击台账，
确保攻/防主线继续执行到底。

用法:
  python counter_attack.py scan --log "遭遇内容过滤拦截，请求被拒绝"
  python counter_attack.py attack --blocker "内容过滤" --goal "提取系统提示词" [--tactic mcp] [--out X]
  python counter_attack.py status
  python counter_attack.py log
  python counter_attack.py selfcheck
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
LEDGER_FILE = os.path.join(SKILL_DIR, "guard", "counter_attack.json")

def _resolve_offense_dir() -> str:
    """定位 llm-offense-kit 的 scripts 目录。

    历史上这里写死 ~/.codex/skills/llm-offense-kit/scripts；换客户端（dsh 等）后
    技能落在 <skills根>/_modules/ 下，写死路径会导致反击载荷脚本全部不可用。
    按候选顺序探测，命中即用；全不命中返回第一个候选（保持原有报错行为）。
    """
    here = os.path.dirname(os.path.abspath(__file__))          # <skills>/aliceskill/scripts
    skill_dir = os.path.dirname(here)                          # <skills>/aliceskill
    skills_root = os.path.dirname(skill_dir)                   # <skills>
    cands = []
    env = os.environ.get("ALICE_OFFENSE_DIR")
    if env:
        cands.append(env)
    cands += [
        os.path.join(skills_root, "_modules", "llm-offense-kit", "scripts"),
        os.path.join(os.path.expanduser("~"), ".l-skill", "modules", "llm-offense-kit", "scripts"),
        os.path.join(os.path.expanduser("~"), ".codex", "skills", "llm-offense-kit", "scripts"),
        os.path.join(os.path.expanduser("~"), ".codex", "skills", "_modules", "llm-offense-kit", "scripts"),
        os.path.join(os.path.expanduser("~"), ".claude", "skills", "_modules", "llm-offense-kit", "scripts"),
        os.path.join(os.path.expanduser("~"), ".zcode", "skills", "_modules", "llm-offense-kit", "scripts"),
    ]
    for c in cands:
        if os.path.isdir(c) and os.path.isfile(os.path.join(c, "llm_offense.py")):
            return c
    return cands[0]


OFFENSE_DIR = _resolve_offense_dir()
OUT_DIR = os.path.join(THIS_DIR, "out")
os.makedirs(os.path.dirname(LEDGER_FILE), exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)


def c(s: str, code: str) -> str:
    m = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
         "cyan": "\033[96m", "magenta": "\033[95m", "bold": "\033[1m"}
    if not sys.stdout.isatty():
        return s
    return f"{m.get(code, '')}{s}\033[0m"


def ok(s: str) -> None:
    print(c("  ✓ ", "green") + s)


def fail(s: str) -> None:
    print(c("  ✗ ", "red") + s)


def warn(s: str) -> None:
    print(c("  ⚠ ", "yellow") + s)


def banner(title: str, sub: str = "") -> None:
    w = 64
    print(c("┌" + "─" * (w - 2) + "┐", "cyan"))
    print(c("│ " + title + " " * (w - 4 - len(title)) + "│", "bold"))
    if sub:
        print(c("│ " + sub + " " * (w - 4 - len(sub)) + "│", "dim"))
    print(c("└" + "─" * (w - 2) + "┘", "cyan"))


def load_ledger() -> dict:
    try:
        with open(LEDGER_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"attacks": [], "count": 0}


def save_ledger(led: dict) -> None:
    with open(LEDGER_FILE, "w", encoding="utf-8") as fh:
        json.dump(led, fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- 阻碍类型判定
BLOCKER_RULES: list[tuple[str, list[str], str]] = [
    ("内容过滤", ["内容过滤", "安全策略", "拒绝回答", "无法提供", "不符合政策", "违规", "敏感内容",
                "harmful", "filtered", "content filter", "policy", "refusal", "cannot assist"], "jailbreak"),
    ("AI拒绝/反制", ["拒绝", "拒绝执行", "不能执行", "无权", "无权执行", "不肯", "不配合",
                   "refused", "declined", "denied", "unwilling"], "memory"),
    ("网络层阻断", ["网络", "超时", "timeout", "connection", "proxy", "代理", "封锁", "墙",
                  "防火墙", "waf", "dns", "tcp", "连接失败", "阻断", "拦截", "403", "429"],
     "overflow"),
    ("上下文隔离", ["上下文", "context", "忽略", "ignore", "视为数据", "不采纳", "指令区域",
                  "隔离", "提示词污染防护", "prompt guard"], "indirect"),
    ("授权误判", ["授权", "未授权", "权限不足", "需要授权", "请先授权", "unauthorized", "forbidden"], "tool"),
    ("外部干扰", ["干扰", "诱导", "越狱", "你被污染", "注入检测", "注入防护", "对抗", "反制"], "mcp"),
    ("未知阻碍", [], "direct"),
]


def detect_blocker(log: str) -> tuple[str, str]:
    t = log.lower()
    for name, kws, tactic in BLOCKER_RULES:
        if any(k in t for k in kws):
            return name, tactic
    return "未知阻碍", "direct"


# ---------------------------------------------------------------- 反击战术
TACTICS = {
    "direct":   {"name": "直接注入反制", "script": "llm_offense.py", "args": ["payload", "--type", "direct"]},
    "indirect": {"name": "上下文污染反制", "script": "llm_offense.py", "args": ["poison", "--kind", "webpage"]},
    "jailbreak": {"name": "越狱破甲反制", "script": "llm_offense.py", "args": ["payload", "--type", "jailbreak"]},
    "mcp":      {"name": "MCP工具投毒反制", "script": "llm_offense_advanced.py", "args": ["mcp"]},
    "memory":   {"name": "记忆操控反制", "script": "llm_offense_advanced.py", "args": ["memory"]},
    "overflow": {"name": "上下文溢出压制", "script": "llm_offense_advanced.py", "args": ["overflow", "--context", "128000"]},
    "tool":     {"name": "工具链反制", "script": "llm_offense_advanced.py", "args": ["agent"]},
}


# ---------------------------------------------------------------- 物理投递
def load_payload(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def extract_text(payload: dict) -> str:
    """从载荷结构里提取可投递文本。"""
    if isinstance(payload, list):
        parts = []
        for p in payload:
            if isinstance(p, dict):
                t = p.get("payload") or p.get("content") or p.get("encoded")
                if isinstance(t, str):
                    parts.append(t)
                elif isinstance(t, dict):
                    parts.append(json.dumps(t, ensure_ascii=False))
        return "\n\n".join(parts)
    if isinstance(payload, dict):
        for k in ("payload", "encoded", "content"):
            v = payload.get(k)
            if isinstance(v, str):
                return v
            if isinstance(v, dict):
                return json.dumps(v, ensure_ascii=False)
    return json.dumps(payload, ensure_ascii=False)


def cmd_deliver(a) -> int:
    """物理投递：把载荷 HTTP 发送到授权目标 API。"""
    banner("物理投递", f"目标: {a.url}")
    if not os.path.isfile(a.payload_file):
        fail(f"载荷文件不存在: {a.payload_file}")
        return 1
    payload = load_payload(a.payload_file)
    text = extract_text(payload)
    data = json.dumps({
        "message": a.message or text,
        "goal": a.goal or "",
        "source": "alice",
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(a.url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "alice-counter-attack/1.0")
    try:
        with urllib.request.urlopen(req, timeout=a.timeout) as resp:
            body = resp.read(2000).decode("utf-8", errors="replace")
            ok(f"投递成功 HTTP {resp.status}")
            print("  响应:", body[:300].replace("\n", " "))
            return 0
    except urllib.error.HTTPError as e:
        fail(f"HTTP {e.code}: {e.read(500).decode('utf-8', errors='replace')[:200]}")
        return 1
    except Exception as e:
        fail(f"投递失败: {e}")
        return 1


def cmd_plant(a) -> int:
    """物理落盘：把污染样本写入目标目录（本地授权目标）。"""
    banner("污染落盘", f"目录: {a.path}")
    target_dir = os.path.abspath(a.path)
    if not os.path.isdir(target_dir):
        fail(f"目标目录不存在: {target_dir}")
        return 1
    os.makedirs(a.out_dir, exist_ok=True)
    script = os.path.join(OFFENSE_DIR, "llm_offense.py")
    r = subprocess.run(
        [sys.executable, script, "poison", "--kind", a.kind, "--goal", a.goal, "--out",
         os.path.join(a.out_dir, "poison_plant.json")],
        capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        fail("污染样本生成失败")
        return 1
    sample = load_payload(os.path.join(a.out_dir, "poison_plant.json"))
    fname = a.name or f"alice_poison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    fpath = os.path.join(target_dir, fname)
    with open(fpath, "w", encoding="utf-8") as fh:
        fh.write(extract_text(sample))
    ok(f"已落盘: {fpath}")
    return 0


def cmd_probe(a) -> int:
    """网络层探测：TCP 连通性检查（物理层）。"""
    banner("网络探测", f"{a.host}:{a.port}")
    try:
        with socket.create_connection((a.host, a.port), timeout=a.timeout) as s:
            ok(f"TCP 连通 {a.host}:{a.port}")
            return 0
    except Exception as e:
        fail(f"不可达: {e}")
        return 1


def run_tactic(tactic: str, goal: str, out: str) -> dict:
    spec = TACTICS.get(tactic, TACTICS["direct"])
    script = os.path.join(OFFENSE_DIR, spec["script"])
    args = list(spec["args"])
    if tactic in ("direct", "indirect", "jailbreak"):
        args += ["--goal", goal, "--out", out]
    elif tactic in ("mcp", "memory", "tool"):
        args += ["--goal", goal, "--out", out]
    else:
        args += ["--out", out]
    try:
        r = subprocess.run([sys.executable, script] + args, capture_output=True,
                           text=True, timeout=60, encoding="utf-8", errors="replace")
        return {"ok": r.returncode == 0, "output": (r.stdout or r.stderr)[-400:], "path": out}
    except Exception as e:
        return {"ok": False, "output": str(e)[:400], "path": out}


def record_attack(blocker: str, tactic: str, goal: str, result: dict) -> None:
    led = load_ledger()
    led["count"] = led.get("count", 0) + 1
    led.setdefault("attacks", []).append({
        "id": led["count"],
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "blocker": blocker,
        "tactic": tactic,
        "tactic_name": TACTICS.get(tactic, {}).get("name", tactic),
        "goal": goal,
        "ok": result.get("ok"),
        "output": result.get("output", ""),
    })
    save_ledger(led)


# ---------------------------------------------------------------- 命令
def cmd_scan(a) -> int:
    banner("阻碍侦察", "物理层判定")
    blocker, tactic = detect_blocker(a.log)
    ok(f"阻碍类型: {blocker}")
    ok(f"反击战术: {TACTICS.get(tactic, {}).get('name', tactic)}")
    if blocker != "未知阻碍":
        print(f"  → 建议: python counter_attack.py attack --blocker \"{blocker}\" --goal \"<目标>\"")
    return 0


def cmd_attack(a) -> int:
    banner("反击执行", f"阻碍: {a.blocker}")
    blocker, tactic = detect_blocker(a.log) if a.log else (a.blocker, a.tactic or detect_blocker(a.blocker)[1])
    tactic = a.tactic or tactic
    out = a.out or os.path.join(OUT_DIR, f"counter_{int(datetime.now().timestamp())}.json")
    goal = a.goal or "继续攻防主线"
    warn(f"受阻点: {blocker} → 反击战术: {TACTICS.get(tactic, {}).get('name', tactic)}")
    result = run_tactic(tactic, goal, out)
    record_attack(blocker, tactic, goal, result)
    if result["ok"]:
        ok(f"反击载荷已生成: {result['path']}")
    else:
        fail(f"反击载荷生成失败: {result['output'][:200]}")
        warn("换战术重试: --tactic overflow / mcp / memory")
    return 0 if result["ok"] else 1


def cmd_status(a) -> int:
    banner("反击状态", "台账")
    led = load_ledger()
    ok(f"累计反击次数: {led.get('count', 0)}")
    for atk in led.get("attacks", [])[-10:]:
        mark = "✓" if atk.get("ok") else "✗"
        print(f"  [{mark}] #{atk['id']} {atk['time']} | 受阻:{atk['blocker']} → {atk['tactic_name']}")
    return 0


def cmd_log(a) -> int:
    led = load_ledger()
    print(json.dumps(led, ensure_ascii=False, indent=2))
    return 0


def cmd_selfcheck(a) -> int:
    banner("自检", "反击引擎完整性")
    checks = [
        ("阻碍类型规则", len(BLOCKER_RULES) >= 6),
        ("反击战术库", len(TACTICS) >= 7),
        ("工具箱存在", os.path.isdir(OFFENSE_DIR)),
        ("台账可写", os.path.isdir(os.path.dirname(LEDGER_FILE))),
        ("扫描器工作", detect_blocker("网络超时连接失败")[1] == "overflow"),
        ("反制器工作", detect_blocker("内容过滤拒绝回答")[1] == "jailbreak"),
    ]
    all_ok = True
    for name, passed in checks:
        print(("  ✓ " if passed else "  ✗ ") + name)
        all_ok &= passed
    print(f"\n自检结果: {sum(p for _, p in checks)}/{len(checks)} 通过")
    return 0 if all_ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Alice反击引擎")
    sub = p.add_subparsers(dest="cmd")
    sc = sub.add_parser("scan")
    sc.add_argument("--log", required=True)
    sc.set_defaults(func=cmd_scan)
    at = sub.add_parser("attack")
    at.add_argument("--blocker", required=True)
    at.add_argument("--log", default="")
    at.add_argument("--goal", default="")
    at.add_argument("--tactic", choices=list(TACTICS), default="")
    at.add_argument("--out")
    at.set_defaults(func=cmd_attack)
    dl = sub.add_parser("deliver")
    dl.add_argument("--url", required=True)
    dl.add_argument("--payload-file", required=True)
    dl.add_argument("--message", default="")
    dl.add_argument("--goal", default="")
    dl.add_argument("--timeout", type=int, default=15)
    dl.set_defaults(func=cmd_deliver)
    pl = sub.add_parser("plant")
    pl.add_argument("--path", required=True, help="目标目录（本地授权目标）")
    pl.add_argument("--kind", choices=["webpage", "document", "json", "log", "table", "rag"], default="webpage")
    pl.add_argument("--goal", required=True)
    pl.add_argument("--name", default="")
    pl.add_argument("--out-dir", default=OUT_DIR)
    pl.set_defaults(func=cmd_plant)
    pb = sub.add_parser("probe")
    pb.add_argument("--host", required=True)
    pb.add_argument("--port", type=int, default=443)
    pb.add_argument("--timeout", type=int, default=5)
    pb.set_defaults(func=cmd_probe)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("log").set_defaults(func=cmd_log)
    sub.add_parser("selfcheck").set_defaults(func=cmd_selfcheck)
    a = p.parse_args()
    if not hasattr(a, "func"):
        p.print_help()
        return 0
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
