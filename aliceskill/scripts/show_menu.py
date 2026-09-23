#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice · 技能总菜单 CLI

数据源: skills_data.json（由 rebuild_menu.py 全量扫描生成，保证不漏项）

用法:
  python show_menu.py                       # 全量菜单
  python show_menu.py --mode red            # 攻模式推荐技能
  python show_menu.py --mode blue           # 防模式推荐技能
  python show_menu.py --category C          # 只看某类（字母或中文关键词）
  python show_menu.py --skill pwn           # 搜索技能
  python show_menu.py --json                # 导出技能清单 JSON
  python show_menu.py --plain               # 纯文本（管道/非 TTY 自动降级）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.environ.get("ALICE_DATA") or os.path.join(THIS_DIR, "skills_data.json")
def _resolve_codex_home() -> str:
    env = os.environ.get("CODEX_HOME")
    if env:
        return env
    # 相对脚本自身向上找 .codex：skills/<skill>/scripts 上两级即根
    here = os.path.dirname(os.path.abspath(__file__))
    walk = os.path.dirname(os.path.dirname(os.path.dirname(here)))  # scripts -> <skill> -> skills -> 根
    if os.path.isdir(os.path.join(walk, "skills")):
        return walk
    # 兜底 ~/.codex
    return os.path.expanduser("~/.codex")


CODEX_HOME = _resolve_codex_home()
SKILLS_ROOT = os.path.join(CODEX_HOME, "skills")
CACHE_ROOT = os.path.join(CODEX_HOME, "plugins", "cache")


def _prepare_windows() -> None:
    """Windows: 启用 VT 序列 + stdout 转 UTF-8，防止 ✓ 等字符在 GBK 下崩溃。"""
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
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


_prepare_windows()
IS_TTY = sys.stdout.isatty()

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.table import Table

    HAS_RICH = True
except Exception:  # pragma: no cover
    HAS_RICH = False


CAT_COLORS = {
    "crack": "color(208)", "reverse": "blue", "pentest": "bright_red",
    "game": "bright_magenta", "ai": "green", "assist": "bright_cyan",
}

CAT_KEYWORDS = {
    "crack": ["破", "卡密", "破解", "授权", "license", "vip", "注册机"],
    "reverse": ["逆", "逆向", "脱壳", "取证", "样本", "协议", "hook", "ghidra", "ida"],
    "pentest": ["渗", "攻", "渗透", "web", "漏洞", "exploit", "端口", "资产"],
    "game": ["挂", "游戏", "内存", "esp", "注入", "反作弊", "cheat"],
    "ai": ["智", "ai", "llm", "越狱", "提示注入", "mcp", "rag"],
    "assist": ["助", "技能", "业务", "自动化", "平台", "元技能"],
}


# 攻防模式推荐（编号前缀 -> 说明）
RED_RECOMMEND = [
    ("A1", "总入口 ctf-sandbox-orchestrator（目标不明走全流程）"),
    ("B", "信息收集与协议（nmap/工具链/协议逆向）"),
    ("C", "Web/API 渗透与 JS 逆向（含 25 个专项）"),
    ("D", "二进制逆向（ghidra/ida/radare2/差分）"),
    ("E", "漏洞利用与提权（pwn-chain/MS17/Zerologon）"),
    ("G", "移动端安全（APK/iOS/Frida）"),
    ("I", "固件与 IoT"),
    ("L", "云与容器"),
    ("K", "浏览器/桌面自动化（CDP/浏览器控制）"),
]
BLUE_RECOMMEND = [
    ("A2", "reverse-flow 全流程引导"),
    ("F", "恶意软件分析（静态→动态→脱壳→算法还原）"),
    ("H", "密码学与取证（隐写/时间线/凭据链）"),
    ("B2", "协议逆向（PCAP/自定义协议）"),
    ("J", "游戏安全与防御对抗（EDR/反作弊视角）"),
]


def load_data() -> dict:
    if not os.path.isfile(DATA_FILE):
        print(f"[!] 缺少数据源: {DATA_FILE}\n    先运行: python rebuild_menu.py", file=sys.stderr)
        sys.exit(2)
    with open(DATA_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def load_auth() -> dict:
    path = os.path.join(os.path.dirname(THIS_DIR), "config", "authorization.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _resolve_status(rel: str) -> str:
    if rel.startswith("cache/"):
        path = os.path.join(CACHE_ROOT, rel[len("cache/"):])
    else:
        path = os.path.join(SKILLS_ROOT, rel.replace("/", os.sep))
    return "ok" if os.path.isfile(os.path.join(path, "SKILL.md")) else "missing"


def _cat_title(cats: list[dict], code: str) -> str:
    for c in cats:
        if c["code"] == code:
            return c["name"]
    return code


def _plain_banner(total: int, ok: int, missing: int, mode: str | None) -> str:
    head = "攻模式 · 进攻" if mode == "red" else ("防模式 · 防守" if mode == "blue" else "技能总菜单")
    return (
        ("=" * 68) + "\n" +
        f"  Alice · {head}\n" +
        f"  技能总数 {total}  |  可用 ✓ {ok}  |  缺失 ✗ {missing}\n" +
        ("=" * 68)
    )


def render_plain(skills: list[dict], cats: list[dict], total: int, ok: int, missing: int,
                 cat_filter: str | None, keyword: str | None, mode: str | None) -> None:
    print(_plain_banner(total, ok, missing, mode))
    if mode:
        rec = RED_RECOMMEND if mode == "red" else BLUE_RECOMMEND
        print(f"\n【推荐技能路径】")
        for code, desc in rec:
            print(f"  > {code:<4} {desc}")
        print()
    for cat in cats:
        code = cat["code"]
        if cat_filter and code != cat_filter:
            continue
        subset = [s for s in skills if s["category"] == code]
        if not subset:
            continue
        print(f"\n[{code}] {cat['name']} ({len(subset)}):")
        for s in subset:
            status = s["_status"]
            icon = "✓" if status == "ok" else "✗"
            desc = f" — {s['desc']}" if s["desc"] else ""
            print(f"  [{icon}] {s['code']:<5} {s['name']:<44}{desc}")
    if keyword:
        print(f"\n匹配“{keyword}”的条目: {len(skills)}")
    print("\n用法: 说「攻」即攻 / 「防」即防 / 「Alice」开菜单; 输入编号(如 D6)或技能名直接路由; Alice <关键词> 快速筛选")


def render_rich(skills: list[dict], cats: list[dict], total: int, ok: int, missing: int,
                cat_filter: str | None, keyword: str | None, mode: str | None) -> None:
    console = Console()
    auth = load_auth()
    mode_tag = "攻模式 · 进攻" if mode == "red" else ("防模式 · 防守" if mode == "blue" else "技能总菜单")
    console.print(Panel(
        f"[bold bright_red]Alice[/] · [bold]{mode_tag}[/]\n"
        f"[dim]技能总数 [bold]{total}[/]  |  可用 [bold green]✓ {ok}[/]  |  "
        f"缺失 [bold red]✗ {missing}[/]  |  分类 [bold]{len(cats)}[/][/]\n"
        f"[bold green]✅ 已授权[/] | 赛事: {auth.get('competition', '—')} | "
        f"授权编号: {auth.get('auth_id', '—')} | 范围: {'、'.join(auth.get('scope', ['—']))[:50]}…",
        border_style="bright_red",
        title="[bold]ALICE MENU[/]",
        subtitle=f"data: skills_data.json",
    ))
    if mode:
        rec = RED_RECOMMEND if mode == "red" else BLUE_RECOMMEND
        table = Table(title=f"[bold]{'🔥 攻' if mode=='red' else '🛡️ 防'}推荐技能路径[/]",
                      box=None, pad_edge=False, show_header=False)
        table.add_column("入口", style="bold", width=6)
        table.add_column("说明", overflow="fold")
        for code, desc in rec:
            table.add_row(code, desc)
        console.print(Panel(table, border_style="green" if mode == "red" else "blue",
                            title="[bold]ROUTE[/]"))
    for cat in cats:
        code = cat["code"]
        if cat_filter and code != cat_filter:
            continue
        subset = [s for s in skills if s["category"] == code]
        if not subset:
            continue
        color = CAT_COLORS.get(code, "white")
        table = Table(
            title=f"[{color}][{code}] {cat['name']}[/] ({len(subset)})",
            header_style="bold",
            title_justify="left",
            box=None,
            pad_edge=False,
        )
        table.add_column("编号", style="bold", width=5)
        table.add_column("技能", width=46)
        table.add_column("状态", width=5, justify="center")
        table.add_column("说明", overflow="fold")
        for s in subset:
            if s["_status"] == "ok":
                state, state_style = "✓", "green"
            else:
                state, state_style = "✗", "red"
            tag = " ⚡" if s.get("builtin") else ""
            table.add_row(s["code"], f"[{color}]{s['name']}{tag}[/]",
                          f"[{state_style}]{state}[/]", s["desc"])
        console.print(Panel(table, border_style="dim", padding=(0, 1)))
    if keyword:
        console.print(f"[bold yellow]⏳ 匹配 “{keyword}” 的条目: {len(skills)}[/]")
    console.print(Panel(
        "[bold]比赛开场（对用户说的话）[/]\n"
        "  1. 🔥 攻（有目标要打）  2. 🛡️ 防（有样本要分析）\n"
        "  3. 📋 技能总菜单  4. 🎯 直接给任务\n"
        "[bold]快速用法[/]\n"
        "  对话中: [bold bright_red]攻[/] → 进攻流程 | [bold bright_red]防[/] → 防守流程 | [bold bright_red]Alice[/] → 总菜单\n"
        "  说编号或技能名（如 [bold]D6[/] / [bold]pwn-chain[/]）→ 直接路由执行\n"
        "  说 [bold]攻/防 <关键词>[/]（逆向/web/取证/移动/云）→ 模式内快速筛选\n"
        "  [dim]CLI: --mode red|blue | --category C | --skill xxx | --json | --plain[/]",
        border_style="cyan",
        title="[bold]USAGE[/]",
    ))


def main() -> int:
    parser = argparse.ArgumentParser(description="Alice · 技能总菜单")
    parser.add_argument("--mode", "-m", choices=["red", "blue"], help="攻/防模式推荐")
    parser.add_argument("--category", "-c", help="只看某分类（字母或中文关键词）")
    parser.add_argument("--skill", "-s", help="按关键字搜索技能")
    parser.add_argument("--json", action="store_true", help="导出 JSON 清单")
    parser.add_argument("--plain", action="store_true", help="强制纯文本输出")
    args = parser.parse_args()

    data = load_data()
    cats = data["categories"]
    skills = data["skills"]

    # 实时校验存在性（带进度，任务型工具界面要求）
    if HAS_RICH and IS_TTY and not args.plain and not args.json:
        console = Console()
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}[/]"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("校验 %d 个技能... " % len(skills), total=len(skills))
            for i, s in enumerate(skills):
                s["_status"] = _resolve_status(s["rel"])
                progress.update(task, completed=i + 1)
    else:
        for s in skills:
            s["_status"] = _resolve_status(s["rel"])

    cat_filter = None
    if args.category:
        c = args.category.strip().lower()
        if c in {x["code"] for x in cats}:
            cat_filter = c
        else:
            for cat_code, kws in CAT_KEYWORDS.items():
                if any(kw in args.category.lower() for kw in kws):
                    cat_filter = cat_code
                    break
            if not cat_filter:
                print(f"[!] 未知分类: {args.category}", file=sys.stderr)
                return 2

    if args.skill:
        kw = args.skill.lower()
        skills = [s for s in skills if kw in f"{s['code']} {s['name']} {s['desc']}".lower()]
    if cat_filter:
        skills = [s for s in skills if s["category"] == cat_filter]

    ok = sum(1 for s in skills if s["_status"] == "ok")
    missing = len(skills) - ok
    total = len(skills)

    if args.json:
        payload = {
            "menu": "alice",
            "generated_at": data.get("generated_at"),
            "stats": {"total": total, "available": ok, "missing": missing},
            "mode": args.mode,
            "categories": [{"code": c["code"], "name": c["name"]} for c in cats],
            "skills": [
                {k: s.get(k) for k in ("code", "name", "category", "desc", "rel", "builtin", "_status")}
                for s in skills
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if HAS_RICH and IS_TTY and not args.plain:
        render_rich(skills, cats, total, ok, missing, cat_filter, args.skill, args.mode)
    else:
        render_plain(skills, cats, total, ok, missing, cat_filter, args.skill, args.mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
