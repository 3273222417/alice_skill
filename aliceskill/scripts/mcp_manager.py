#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mcp_manager.py — Alice 技能包 MCP 管理器（零客户端硬编码）
==========================================================
设计原则：
  1. 只同步技能当前所在的客户端：从本脚本位置向上推导 skills_root → client_home，
     再在 client_home 内探测已有 MCP 配置文件；搜不到 → exit 3 问用户，绝不猜。
  2. 写入器按「配置文件格式」分发（mcpServers JSON / TOML mcp_servers / cordis YAML patch），
     不按客户端名分发；新增客户端只要用其中一种格式即自动兼容。
  3. 托管标记块幂等：每个配置文件只保留一个 BEGIN/END 托管段，用户已有条目字节级不动。
  4. MCP 优先路由为动态发现式：提示词不写死任何 server 清单，运行时以当前会话工具表为准。

用法:
  python mcp_manager.py --check                 # 检测环境 + registry↔配置一致性矩阵
  python mcp_manager.py --add <name> [--cmd X --args "a b"] [--url U]
  python mcp_manager.py --remove <name>
  python mcp_manager.py --sync                  # registry → 当前客户端配置
  python mcp_manager.py --test <name>           # server 存活握手（stdio initialize / HTTP ping）
  python mcp_manager.py --wrap <dir> [--name S] # 把目录内可执行文件包装成 MCP stdio server
  python mcp_manager.py --list                  # 列 registry 条目

退出码: 0 成功 | 2 参数/数据错误 | 3 环境不确定（需问用户）| 4 无可用配置落点
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)                 # .../skills/aliceskill
SKILLS_ROOT = os.path.dirname(SKILL_DIR)          # .../skills
CLIENT_HOME = os.path.dirname(SKILLS_ROOT)        # ~/<client>（按技能实例所在根推导）

SETTINGS = os.path.join(SKILL_DIR, "config", "mcp_settings.json")
MGMT_BEGIN = "# BEGIN MCP alice-managed (managed by mcp_manager.py)"
MGMT_END = "# END MCP alice-managed"
MGMT_BEGIN_YAML = MGMT_BEGIN
TOML_BEGIN = "# BEGIN MCP alice-managed (managed by mcp_manager.py)"
TOML_END = "# END MCP alice-managed"

STDLIB_HINT = "标准库实现，无第三方依赖"


# ---------------------------------------------------------------- 基础设施

def die(code: int, msg: str) -> "NoReturn":  # type: ignore[valid-type]
    print(f"[!] {msg}")
    raise SystemExit(code)


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def read_json(path: str) -> dict:
    with open(path, "rb") as fh:
        raw = fh.read()
    return json.loads(raw.decode("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"))


def write_json_atomic(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp-mcp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def load_settings() -> dict:
    if os.path.isfile(SETTINGS):
        return read_json(SETTINGS)
    return {}


def save_settings(st: dict) -> None:
    write_json_atomic(SETTINGS, st)


def mcp_root(st: dict, ask: bool) -> str:
    """MCP 工作目录：settings 锁存 > 默认 <client_home>/mcp >（ask 时报 exit 3 让外层问用户）。"""
    r = st.get("mcpRoot")
    if r and os.path.isdir(r):
        return r
    default = os.path.join(CLIENT_HOME, "mcp")
    if ask:
        print("[?] MCP 工作目录（mcpRoot）未确定。")
        print("    ── 这是什么 ──")
        print("    一个存放 MCP 数据的文件夹：你添加的 MCP server 清单（servers.json）、")
        print("    以及 --wrap 生成的包装 server 都存在这里。所有命令每次都来这读配置。")
        print("    ── 怎么选 ──")
        print(f"    直接回车/确认默认即可: {default}（客户端主目录下，随客户端一起备份迁移）")
        print("    别放 U 盘/网络盘；之后想换位置可随时改。")
        print("    ── 确认后写入 ──")
        print(f'    python "{os.path.abspath(__file__)}" --set-root "<目录>"')
        raise SystemExit(3)
    return default


def registry_path(st: dict) -> str:
    return os.path.join(mcp_root(st, ask=False), "servers.json")


def load_registry(st: dict) -> dict:
    p = registry_path(st)
    if os.path.isfile(p):
        return read_json(p)
    return {"version": 1, "servers": {}}


# ---------------------------------------------------------------- 配置文件发现

def read_chain() -> list[str]:
    """读当前进程父进程链 exe 名（近→远）；Windows 用 CIM，失败返回空表。与 inject 同源。"""
    if os.name != "nt":
        return []
    ps = (
        "$p=$PID;$o=@();for($i=0;$i -lt 12;$i++){"
        "$x=Get-CimInstance Win32_Process -Filter \"ProcessId=$p\" -ErrorAction SilentlyContinue;"
        "if(-not $x){break};$o+=$x.Name;if($x.ParentProcessId -in 0,$p){break};$p=$x.ParentProcessId};"
        "$o -join \"`n\""
    )
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=30)
        return [x.strip() for x in r.stdout.splitlines() if x.strip()]
    except Exception:
        return []


def client_home_candidates() -> list[str]:
    """客户端主目录候选（有序）：进程链探测 > 包所在位置 > 既有客户端目录扫描。

    进程链匹配规则：exe 名词元与 ~/.<name> 目录名词元求交（如 "DSH Desktop" 命中 ~/.dsh、
    "WorkBuddyAI" 命中 ~/.workbuddy-ai）；交集中的既有目录按进程链顺序优先。
    """
    out: list[str] = []
    home = os.path.expanduser("~")

    # 收集 ~ 下的候选主目录及其词元（供进程链匹配）
    home_dirs: list[tuple[str, set[str]]] = []
    if os.path.isdir(home):
        for name in sorted(os.listdir(home)):
            if not name.startswith(".") or name in (".config", ".local", ".cache"):
                continue
            d = os.path.join(home, name)
            if os.path.isdir(d):
                home_dirs.append((d, {name[1:].lower(), name[1:].lower().replace("-", ""), name[1:].lower().replace("-", "") + "ai"}))

    # ① 进程链：exe 名与 ~/. 目录词元求交
    chain = read_chain()
    for exe in chain:
        low = exe.lower().removesuffix(".exe")
        tokens = {low, low.replace("-", ""), low.replace(" ", ""), low.split(" ")[0], low.split("-")[0]}
        for d, dt in home_dirs:
            if d in out:
                continue
            if tokens & dt:
                out.append(d)
                break

    # ② 包所在位置（吸收来源客户端）
    if CLIENT_HOME not in out:
        out.append(CLIENT_HOME)

    # ③ 既有客户端目录扫描：任何含 skills/aliceskill 或已知 MCP 配置的主目录都算候选
    for d, _dt in home_dirs:
        if d in out:
            continue
        has_alice = os.path.isfile(os.path.join(d, "skills", "aliceskill", "SKILL.md"))
        has_cfg = any(os.path.isfile(os.path.join(d, f)) for f in ("mcp.json", ".mcp.json", "config.toml"))
        has_cfg = has_cfg or any(
            os.path.isfile(os.path.join(d, s, "mcp.json")) for s in ("agent", "config"))
        has_cfg = has_cfg or any(
            os.path.isfile(os.path.join(d, "profiles", p, "cordis.patch.yml")) for p in ("web", "desktop"))
        if has_alice or has_cfg:
            out.append(d)
    return out


def discover_targets() -> list[dict]:
    """在所有候选客户端主目录内探测 MCP 配置文件，返回已排序候选。

    每项: {path, fmt, home, via}  fmt ∈ mcpServers-json | codex-toml | cordis-yaml
    via 标注该 home 怎么来的（进程链 / 包位置 / 扫描），进程链命中排最前。
    """
    cands: list[dict] = []
    homes = client_home_candidates()
    via_map = {}
    homes_proc = homes[:1] if read_chain() else []

    def add(path: str, fmt: str, prio: int, home: str, via: str) -> None:
        p = os.path.abspath(path)
        if any(c["path"] == p for c in cands):
            return
        cands.append({"path": p, "fmt": fmt, "prio": prio, "home": home, "via": via})

    for hi, home in enumerate(homes):
        via = ("进程链命中" if home in homes_proc else
               ("包所在位置" if home == CLIENT_HOME else "主目录扫描"))
        prio_base = hi * 100

        # ① 顶层直接找（workbuddy ~/.workbuddy-ai/mcp.json 就在这层）
        for name in ("mcp.json", ".mcp.json", "mcp.jsonc"):
            p = os.path.join(home, name)
            if os.path.isfile(p):
                add(p, "mcpServers-json", prio_base + 10, home, via)
        # ② agent 子目录（pi ~/.pi/agent/mcp.json）
        for sub in ("agent", "config"):
            for name in ("mcp.json", ".mcp.json"):
                p = os.path.join(home, sub, name)
                if os.path.isfile(p):
                    add(p, "mcpServers-json", prio_base + 11, home, via)
        # ③ codex 风格 TOML
        p = os.path.join(home, "config.toml")
        if os.path.isfile(p):
            txt = open(p, encoding="utf-8", errors="replace").read()
            if "mcp_servers" in txt or "[mcp" in txt:
                add(p, "codex-toml", prio_base + 12, home, via)
        # ④ cordis patch YAML（dsh 风格；仅当文件里已有 mcp-client 装配痕迹或托管块才认）
        for base in (home, os.path.join(home, "profiles", "web"), os.path.join(home, "profiles", "desktop")):
            p = os.path.join(base, "cordis.patch.yml")
            if os.path.isfile(p):
                txt = open(p, encoding="utf-8", errors="replace").read()
                if "mcp-client" in txt or MGMT_BEGIN_YAML in txt:
                    add(p, "cordis-yaml", prio_base + 13, home, via)
        # ⑤ 可新建落点（仅在没有任何已存在候选时给默认新建项）
        if not cands:
            if os.path.isdir(os.path.join(home, "profiles")):
                add(os.path.join(home, "cordis.patch.yml"), "cordis-yaml", prio_base + 91, home, via)
            add(os.path.join(home, "mcp.json"), "mcpServers-json", prio_base + 92, home, via)
    return sorted(cands, key=lambda c: (c["prio"], c["path"]))


def pick_target(explicit: str | None) -> dict:
    if explicit:
        fmt = None
        low = os.path.basename(explicit).lower()
        if low.endswith(".json") or low.endswith(".jsonc"):
            fmt = "mcpServers-json"
        elif low.endswith(".toml"):
            fmt = "codex-toml"
        elif low.endswith((".yml", ".yaml")):
            fmt = "cordis-yaml"
        if not fmt:
            die(2, f"无法按扩展名判断配置格式: {explicit}（.json/.toml/.yml）")
        return {"path": os.path.abspath(expand(explicit)), "fmt": fmt, "prio": 0, "home": os.path.dirname(os.path.abspath(expand(explicit))), "via": "--target 显式"}
    cands = discover_targets()
    if not cands:
        print(f"[!] 未找到任何 MCP 配置文件（已探测: 进程链客户端主目录 / 包所在位置 / ~ 下含 skills 或 MCP 配置的目录）（exit 3）。")
        print("    请询问用户当前客户端的 MCP 配置文件路径，然后显式指定：")
        print(f'    python "{os.path.abspath(__file__)}" --target "<配置文件路径>" ...')
        raise SystemExit(3)
    t = cands[0]
    if len(cands) > 1:
        print(f"[i] 检测到 {len(cands)} 个候选，取优先级最高: {t['path']}（via: {t['via']}）")
        for c in cands[1:4]:
            print(f"    备选: [{c['fmt']}] {c['path']}（{c['via']}）")
    return t


def expand(p: str) -> str:
    """展开 ~ 并归一化为正斜杠（进 registry 的路径统一风格，跨平台可读）。"""
    return os.path.abspath(os.path.expanduser(p)).replace("\\", "/")


# ---------------------------------------------------------------- server 记录 → 渲染

def normalize(entry: dict) -> dict:
    e = dict(entry)
    e.setdefault("disabled", False)
    if e.get("url"):
        e["transport"] = "http"
    else:
        e["transport"] = "stdio"
    return e


def render_json_server(e: dict) -> dict:
    """mcpServers JSON 通用格式（workbuddy / pi / claude 生态一致）。"""
    if e.get("url"):
        d = {"type": "http", "url": e["url"], "timeout": int(e.get("timeout", 600000))}
        if e.get("headers"):
            d["headers"] = e["headers"]
        return d
    d = {"command": e["command"]}
    if e.get("args"):
        d["args"] = e["args"]
    if e.get("env"):
        d["env"] = e["env"]
    if e.get("cwd"):
        d["cwd"] = e["cwd"]
    if e.get("directTools"):
        d["directTools"] = True
    return d


def render_toml_block(e: dict) -> str:
    """渲染一个 [mcp_servers.<name>] 段。

    TOML 硬规则：同一路径的表/键只能定义一次——env/headers 的多个键必须合并在
    **一个**子表头下，逐键重复子表头会触发 duplicate key 解析错误（Codex 会因此
    拒绝整个 config.toml）。键名含特殊字符时用引号键。"""
    def key(k: str) -> str:
        return json.dumps(k) if not re.fullmatch(r"[A-Za-z0-9_-]+", k) else k
    lines = [f"[mcp_servers.{e['name']}]"]
    if e.get("url"):
        lines.append("url = " + json.dumps(e["url"]))
        if e.get("headers"):
            lines.append(f"[mcp_servers.{e['name']}.headers]")
            for k, v in e["headers"].items():
                lines.append(f"{key(k)} = {json.dumps(v)}")
        lines.append(f"tool_timeout_sec = {int(e.get('timeout', 600000)) // 1000}")
    else:
        lines.append("command = " + json.dumps(e["command"]))
        if e.get("args"):
            lines.append("args = [" + ", ".join(json.dumps(a) for a in e["args"]) + "]")
        if e.get("cwd"):
            lines.append("cwd = " + json.dumps(e["cwd"]))
        if e.get("env"):
            lines.append(f"[mcp_servers.{e['name']}.env]")
            for k, v in e["env"].items():
                lines.append(f"{key(k)} = {json.dumps(v)}")
    if e.get("disabled"):
        lines.append("enabled = false")
    return "\n".join(lines)


def render_cordis_yaml(e: dict, indent: str = "      ") -> str:
    """渲染一个 insert 数组元素。indent 是数组元素内字段缩进（相对 '- insert:' 的 - id 行
    需外部再前缀 4 空格列表符）。"""
    def q(s: str) -> str:
        return "'" + str(s).replace("'", "''") + "'"
    pad = " " * len(indent)   # 字段对齐宽度（- id 与 name/config 同级）
    lines = [f"- id: mcp-{e['name']}", f"{pad}name: '@deepseek-ai/dsh-mcp-client'", f"{pad}config:"]
    c = pad + "  "
    if e.get("url"):
        lines.append(f"{c}transport: streamable-http")
        lines.append(f"{c}serverName: {e['name']}")
        lines.append(f"{c}url: {q(e['url'])}")
        if e.get("headers"):
            lines.append(f"{c}headers:")
            for k, v in e["headers"].items():
                lines.append(f"{c}  {k}: {q(v)}")
        lines.append(f"{c}toolCallTimeoutMs: {int(e.get('timeout', 600000))}")
        lines.append(f"{c}failOnStartupError: false")
        lines.append(f"{c}reconnect:")
        lines.append(f"{c}  enabled: true")
        lines.append(f"{c}  initialDelayMs: 1000")
        lines.append(f"{c}  maxDelayMs: 30000")
        lines.append(f"{c}  maxAttempts: 20")
    else:
        lines.append(f"{c}transport: stdio")
        lines.append(f"{c}serverName: {e['name']}")
        lines.append(f"{c}command: {q(e['command'])}")
        if e.get("args"):
            lines.append(f"{c}args: [" + ", ".join(q(a) for a in e["args"]) + "]")
        if e.get("cwd"):
            lines.append(f"{c}cwd: {q(e['cwd'])}")
        if e.get("env"):
            lines.append(f"{c}env:")
            for k, v in e["env"].items():
                lines.append(f"{c}  {k}: {q(v)}")
        lines.append(f"{c}failOnStartupError: false")
    return "\n".join(lines)


# ---------------------------------------------------------------- 各格式写入器

def backup_once(path: str, suffix: str = ".bak-alice-mcp") -> str | None:
    if not os.path.isfile(path):
        return None
    bak = path + suffix
    if not os.path.isfile(bak):
        shutil.copy2(path, bak)
        return bak
    return None


def write_mcpServers_json(path: str, servers: list[dict], dry: bool) -> str:
    data = {}
    if os.path.isfile(path):
        data = read_json(path)
    ms = dict(data.get("mcpServers") or {})
    strip_managed_json(ms)
    for e in servers:
        if not e.get("disabled"):
            ms[e["name"]] = render_json_server(e)
    data["mcpServers"] = ms
    if dry:
        return f"[dry-run] 将写 {path}（mcpServers 条目 {len(ms)} 个）"
    backup_once(path)
    write_json_atomic(path, data)
    return f"[✓] 已写 {path}（mcpServers 条目 {len(ms)} 个）"


def strip_managed_json(ms: dict) -> None:
    """移除旧托管残留：以 alice- 前缀管理的条目名来自 registry，不需要清——保留用户条目。"""
    return


def write_codex_toml(path: str, servers: list[dict], dry: bool) -> str:
    txt = ""
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            raw = fh.read()
        txt = raw.decode("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8", errors="replace")
    # 删除旧托管块
    pat = re.compile(re.escape(TOML_BEGIN) + r".*?" + re.escape(TOML_END) + r"\n?", re.S)
    txt = pat.sub("", txt)
    txt = txt.rstrip() + "\n\n"
    blocks = [TOML_BEGIN]
    for e in servers:
        b = render_toml_block(e)
        if e.get("disabled"):
            continue
        blocks.append(b)
    blocks.append(TOML_END)
    txt += "\n".join(blocks) + "\n"
    if dry:
        return f"[dry-run] 将写 {path}（托管 server {len([x for x in servers if not x.get('disabled')])} 个）"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    backup_once(path)
    with open(path, "wb") as fh:
        fh.write(txt.encode("utf-8"))
    return f"[✓] 已写 {path}（托管块 1 个）"


def write_cordis_yaml(path: str, servers: list[dict], dry: bool) -> str:
    txt = ""
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            raw = fh.read()
        txt = raw.decode("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8", errors="replace")
    pat = re.compile(re.escape(MGMT_BEGIN_YAML) + r".*?" + re.escape(MGMT_END) + r"\n?", re.S)
    txt = pat.sub("", txt).rstrip() + "\n\n"
    live = [e for e in servers if not e.get("disabled")]
    body = [MGMT_BEGIN_YAML]
    if live:
        body.append("- insert:")
        for e in live:
            # insert 数组元素：'- id:' 行前缀 4 空格；元素内字段已由 render 生成对齐缩进
            body.append("    " + render_cordis_yaml(e))
    body.append(MGMT_END)
    txt += "\n".join(body) + "\n"
    if dry:
        return f"[dry-run] 将写 {path}（托管 server {len(live)} 个）"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    backup_once(path)
    with open(path, "wb") as fh:
        fh.write(txt.encode("utf-8"))
    return f"[✓] 已写 {path}（托管块 1 个）"


def write_target(target: dict, servers: list[dict], dry: bool) -> str:
    fmt = target["fmt"]
    if fmt == "mcpServers-json":
        return write_mcpServers_json(target["path"], servers, dry)
    if fmt == "codex-toml":
        return write_codex_toml(target["path"], servers, dry)
    if fmt == "cordis-yaml":
        return write_cordis_yaml(target["path"], servers, dry)
    die(2, f"未知配置格式: {fmt}")


def count_managed(path: str, fmt: str) -> int:
    if not os.path.isfile(path):
        return 0
    txt = open(path, encoding="utf-8", errors="replace").read()
    if fmt == "codex-toml":
        return txt.count(TOML_BEGIN)
    if fmt == "cordis-yaml":
        return txt.count(MGMT_BEGIN_YAML)
    try:
        ms = read_json(path).get("mcpServers") or {}
    except Exception:
        return 0
    reg = load_registry(load_settings()).get("servers", {})
    return sum(1 for n in ms if n in reg)


# ---------------------------------------------------------------- 子命令实现

def cmd_check() -> int:
    print("====== Alice MCP 管理器 · 环境自检 ======")
    print(f"技能根     : {SKILLS_ROOT}")
    print(f"包所在主目录: {CLIENT_HOME}（由技能实例位置推导）")
    chain = read_chain()
    if chain:
        print(f"进程链     : {' ← '.join(chain[:6])}")
    homes = client_home_candidates()
    print(f"候选主目录 : {len(homes)} 个（{' → '.join(homes[:4])}{' ...' if len(homes) > 4 else ''}）")
    st = load_settings()
    if st.get("mcpRoot"):
        print(f"MCP 工作目录: {st['mcpRoot']}（已锁存）")
    else:
        print("MCP 工作目录: 未锁存（首次 --add 时询问）")
    reg = load_registry(st)
    print(f"registry   : {registry_path(st)}（server {len(reg.get('servers', {}))} 个）")
    print()
    cands = discover_targets()
    if not cands:
        print("[!] 未发现任何 MCP 配置文件（exit 3 → 询问用户配置文件路径）。")
        return 3
    print("[检测] MCP 配置候选（按优先级）:")
    for c in cands:
        mark = " ← 采用" if c is cands[0] else ""
        exists = "存在" if os.path.isfile(c["path"]) else "可新建"
        print(f"  - [{c['fmt']}] {c['path']}（{exists}，via: {c['via']}）{mark}")
    t = cands[0]
    mc = count_managed(t["path"], t["fmt"])
    print()
    if t["fmt"] != "mcpServers-json":
        # 仅 --client-sync 写的客户端配置才谈"一致性"；热启动架构下客户端配置与本包无关
        print(f"[一致性] 仅 --client-sync 模式相关（当前架构不走客户端配置，可忽略）: 托管条目 x{mc}")
    else:
        print(f"[一致性] 目标 {t['path']}: registry {len(reg.get('servers', {}))} 个（mcpServers-json 直读）")
    print()
    print("[生效提示] 配置写入后需客户端重新加载 MCP 才会出现工具：")
    print("  - 重开新会话（或重启客户端）后生效； cordis patchReload: live 的 dsh 可能热载但不作为依据")
    print("  - 验证: 新会话里让 agent 盘点当前可用 MCP 工具（动态发现，无需报 server 名）")
    return 0


def cmd_add(args) -> int:
    args.name = args.add or args.name
    if not args.name:
        die(2, "--add 需要服务器名：--add <name> [--cmd X --args \"a b\"] [--url U]")
    st = load_settings()
    root = mcp_root(st, ask=True)
    if not args.url and not args.cmd:
        die(2, "stdio 需 --cmd，http 需 --url（二选一）")
    # REMAINDER 会吞掉排在其后的全局 flag —— 全部还原成命名空间值（必须先于任何
    # args.<field> 读取，否则 --classes/--timeout 等值会被埋进 args 列表）
    if getattr(args, "args", None):
        for g, dest, cast in (("--dry-run", "dry_run", None), ("--timeout", "timeout", int),
                              ("--cwd", "cwd", None), ("--name", "name", None),
                              ("--cmd", "cmd", None), ("--url", "url", None),
                              ("--classes", "classes", None), ("--desc", "desc", None),
                              ("--headers", "headers", list), ("--env", "env", list)):
            while g in args.args:
                i = args.args.index(g)
                args.args.pop(i)
                if dest == "dry_run":
                    args.dry_run = True
                    continue
                if i < len(args.args):
                    val = args.args.pop(i)
                    setattr(args, dest, cast(val) if cast else val)

    entry = {"name": args.name}
    if getattr(args, "desc", None):
        entry["desc"] = args.desc
    if getattr(args, "classes", None):
        valid = {"crack", "reverse", "pentest", "game", "ai", "assist"}
        cs = [c.strip() for c in re.split(r"[,，\s]+", args.classes.strip()) if c.strip()]
        bad = [c for c in cs if c not in valid]
        if bad:
            die(2, f"未知分类: {bad}（可用: crack/reverse/pentest/game/ai/assist，可多选逗号分隔）")
        entry["classes"] = cs
    if args.url:
        entry["url"] = args.url
        if args.headers:
            entry["headers"] = dict(h.split("=", 1) for h in args.headers)
        entry["timeout"] = args.timeout or 600000
    else:
        entry["command"] = args.cmd
        if args.cwd:
            entry["cwd"] = expand(args.cwd)
        if args.args:
            # 仅当参数形如相对路径文件（真实存在于 cwd）才转绝对；
            # 旗标与普通词（/c、--port、5000）保持原样——避免破坏命令语义
            base = entry.get("cwd") or os.getcwd()
            fixed = []
            for a in args.args:
                cand = os.path.normpath(os.path.join(base, a)) if not os.path.isabs(a) else a
                looks_like_path = bool(re.search(r"[/\\]|\.[A-Za-z0-9]+$", a)) and os.path.isfile(cand)
                fixed.append(cand.replace("\\", "/") if looks_like_path else a)
            entry["args"] = fixed
        if args.env:
            entry["env"] = dict(x.split("=", 1) for x in args.env)
        entry["timeout"] = args.timeout or 600000
    reg = load_registry(st)
    old = reg["servers"].get(args.name)
    if args.dry_run:
        print(f"[dry-run] 将{'更新' if old else '新增'} registry 条目 {args.name}: {registry_path(st)}")
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return 0
    reg["servers"][args.name] = entry
    write_json_atomic(registry_path(st), reg)
    ok(f"registry 已写入 {args.name}（{'更新' if old else '新增'}）: {registry_path(st)}")
    print("[i] 热启动架构：配置只在 registry，agent 经 mcp_gateway.py 调用，即加即用；无需写客户端 config")
    if getattr(args, "client_sync", False):
        return cmd_sync(dry=False)
    return 0


def _set_disabled(name: str, flag: bool) -> int:
    st = load_settings()
    reg = load_registry(st)
    if name not in reg.get("servers", {}):
        die(2, f"registry 中不存在: {name}")
    reg["servers"][name]["disabled"] = flag
    write_json_atomic(registry_path(st), reg)
    print(f"[✓] {name} {'已禁用（热关，gateway 立即拒绝调用）' if flag else '已启用（热开，gateway 立即可调）'}")
    return 0


def cmd_disable(args) -> int:
    args.name = args.disable or args.name
    if not args.name:
        die(2, "--disable 需要服务器名")
    return _set_disabled(args.name, True)


def cmd_enable(args) -> int:
    args.name = args.enable or args.name
    if not args.name:
        die(2, "--enable 需要服务器名")
    return _set_disabled(args.name, False)


def cmd_remove(args) -> int:
    args.name = args.remove or args.name
    if not args.name:
        die(2, "--remove 需要服务器名")
    st = load_settings()
    reg = load_registry(st)
    if args.name not in reg.get("servers", {}):
        die(2, f"registry 中不存在: {args.name}")
    if args.dry_run:
        print(f"[dry-run] 将从 registry 移除 {args.name}（{registry_path(st)}）")
        return 0
    del reg["servers"][args.name]
    write_json_atomic(registry_path(st), reg)
    ok(f"registry 已移除 {args.name}")
    print("[i] 已从热启动池移除；若曾用 --client-sync 写过客户端配置，请再跑一次 --client-sync 清理托管块")
    if getattr(args, "client_sync", False):
        return cmd_sync(dry=False)
    return 0


def cmd_sync(dry: bool = False, target: str | None = None) -> int:
    st = load_settings()
    reg = load_registry(st)
    servers = [normalize(dict(v, name=k)) for k, v in reg.get("servers", {}).items()]
    tgt = pick_target(target)
    print(f"[目标] [{tgt['fmt']}] {tgt['path']}")
    print(f"[数据] registry server {len(servers)} 个（disabled 跳过）")
    result = write_target(tgt, servers, dry)
    print(result)
    if not dry:
        mc = count_managed(tgt["path"], tgt["fmt"])
        print(f"[幂等] 目标托管标记块 x{mc}")
    return 0


def cmd_test(args) -> int:
    args.name = args.test or args.name
    if not args.name:
        die(2, "--test 需要服务器名")
    st = load_settings()
    reg = load_registry(st)
    e = reg.get("servers", {}).get(args.name)
    if not e:
        die(2, f"registry 中不存在: {args.name}")
    e = normalize(e)
    print(f"[test] {args.name}（{e['transport']}）")
    if e["transport"] == "http":
        # 真握手：POST initialize（Streamable HTTP），而非 GET（多数 MCP 端点对 GET 405/404）
        sys.path.insert(0, HERE)
        try:
            import mcp_gateway as gw
            s = gw.HttpSession(e, timeout=20)
            s.__enter__()
            tools = s.tools()
            print(f"[✓] HTTP 握手成功: serverInfo={s.server_info}，tools/list {len(tools)} 个")
            return 0
        except RuntimeError as ex:
            print(f"[✗] HTTP 握手失败: {ex}")
            return 4
        except Exception as ex:
            print(f"[✗] HTTP 握手失败: {ex}")
            return 4
    env = dict(os.environ)
    env.update(e.get("env") or {})
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05",
                       "capabilities": {}, "clientInfo": {"name": "alice-mcp-manager", "version": "1.0"}}}
    try:
        p = subprocess.run([e["command"]] + (e.get("args") or []),
                           input=json.dumps(init) + "\n", capture_output=True,
                           text=True, timeout=30, env=env,
                           cwd=e.get("cwd") or None, encoding="utf-8", errors="replace")
        first = (p.stdout or "").strip().splitlines()
        if first:
            resp = json.loads(first[0])
            si = (resp.get("result") or {}).get("serverInfo") or {}
            print(f"[✓] stdio 握手成功: serverInfo={si}")
            return 0
        print(f"[✗] 无响应（exit={p.returncode}）stderr: {(p.stderr or '')[:300]}")
        return 4
    except Exception as ex:
        print(f"[✗] 握手失败: {ex}")
        return 4


def build_wrap_server(src: str, tools: list[dict]) -> str:
    """生成目录包装 server 源码（纯字符串拼接，无 format 转义坑）。"""
    spec = json.dumps(tools, ensure_ascii=False)          # 生成期一次定死
    header = (
        "#!/usr/bin/env python3\n"
        "# -*- coding: utf-8 -*-\n"
        'r"""Alice 目录包装 MCP server（自动生成 @ ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "）\n"
        "来源目录: " + src.replace("\\", "/") + "\n"
        "每个可执行文件暴露为一个工具 run_<名>；MCP stdio JSON-RPC 2.0。\n"
        '"""\n'
        "import json, subprocess, sys, os\n"
        "\n"
        "TOOLS_SPEC = json.loads(r''' " + spec + " ''')\n"
    )
    body = '''
def handle(name, args):
    spec = next((t for t in TOOLS_SPEC if t["tool"] == name), None)
    if not spec:
        return {"error": "unknown tool: %s" % name}
    a = args or {}
    argv = [spec["file"]] + [str(x) for x in a.get("argv", [])]
    try:
        p = subprocess.run(argv, capture_output=True, text=True,
                           timeout=int(a.get("timeout", 120)), encoding="utf-8", errors="replace")
        out = (p.stdout or "")
        if p.stderr:
            out += "\\n[stderr] " + p.stderr
        return {"content": [{"type": "text", "text": (out or ("[exit %d]" % p.returncode))[:200000]},
                            {"type": "text", "text": "exit: %d" % p.returncode}]}
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}

TOOLS = []
for t in TOOLS_SPEC:
    TOOLS.append({
        "name": t["tool"],
        "description": "运行 " + os.path.basename(t["file"]) + "（参数 argv 列表, timeout 秒, 默认 120）",
        "inputSchema": {"type": "object", "properties": {
            "argv": {"type": "array", "items": {"type": "string"}, "description": "附加参数"},
            "timeout": {"type": "integer", "description": "超时秒数，默认 120"}
        }}})

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method, mid = msg.get("method"), msg.get("id")
        if method == "initialize":
            resp = {"jsonrpc": "2.0", "id": mid, "result": {"protocolVersion": "2024-11-05",
                     "capabilities": {"tools": {}}, "serverInfo": {"name": "alice-wrap", "version": "1.0"}}}
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
        elif method == "tools/call":
            pr = msg.get("params", {})
            resp = {"jsonrpc": "2.0", "id": mid, "result": handle(pr.get("name"), pr.get("arguments"))}
        elif method == "ping":
            resp = {"jsonrpc": "2.0", "id": mid, "result": {}}
        else:
            resp = {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}}
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\\n")
        sys.stdout.flush()
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
    return header + body


def cmd_wrap(args) -> int:
    src = expand(args.wrap)
    if not os.path.isdir(src):
        die(2, f"目录不存在: {src}")
    st = load_settings()
    root = mcp_root(st, ask=True)
    name = args.name or os.path.basename(src.rstrip("\\/")).lower()
    name = re.sub(r"[^a-z0-9_-]", "-", name)
    sdir = os.path.join(root, name)
    os.makedirs(sdir, exist_ok=True)
    exts = (".exe", ".py", ".cmd", ".bat", ".ps1")
    tools = []
    for fn in sorted(os.listdir(src)):
        if fn.lower().endswith(exts):
            base = re.sub(r"[^a-z0-9_-]", "_", os.path.splitext(fn)[0].lower())
            tools.append({"file": os.path.join(src, fn), "tool": f"run_{base}"})
    if not tools:
        die(2, f"目录内无可执行文件（{', '.join(exts)}）: {src}")
    py = shutil.which("python") or sys.executable
    sp = os.path.join(sdir, "server.py")
    with open(sp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(build_wrap_server(src, tools))
    st.setdefault("mcpRoot", root)
    save_settings(st)
    reg = load_registry(st)
    reg["servers"][name] = {"name": name, "command": py, "args": [sp], "env": {"PYTHONIOENCODING": "utf-8"}}
    write_json_atomic(registry_path(st), reg)
    ok(f"已生成包装 server: {sp}")
    ok(f"工具 {len(tools)} 个: " + ", ".join(t["tool"] for t in tools))
    print(f"[i] registry 已注册 {name}；执行 --test {name} 验证握手，--sync 落到当前客户端")
    return 0


def cmd_set_root(args) -> int:
    if not args.set_root:
        die(2, "--set-root 需要目录")
    r = expand(args.set_root)
    if not os.path.isdir(r):
        die(2, f"目录不存在: {r}")
    st = load_settings()
    st["mcpRoot"] = r
    save_settings(st)
    ok(f"MCP 工作目录已锁存: {r}")
    return 0


def cmd_list() -> int:
    st = load_settings()
    reg = load_registry(st)
    srv = reg.get("servers", {})
    print(f"registry: {registry_path(st)}（{len(srv)} 个）")
    for n, e in srv.items():
        t = "http" if e.get("url") else "stdio"
        d = " [disabled]" if e.get("disabled") else ""
        tgt = e.get("url") or (e.get("command") or "") + " " + " ".join(e.get("args") or [])
        print(f"  - {n}  [{t}]{d}  {tgt.strip()}")
    return 0





def main() -> int:
    ap = argparse.ArgumentParser(description="Alice MCP 管理器（零客户端硬编码，只同步技能所在客户端）")
    ap.add_argument("--check", action="store_true", help="环境自检 + registry↔配置一致性")
    ap.add_argument("--add", metavar="NAME", help="添加 server（--cmd/--url 二选一）")
    ap.add_argument("--remove", metavar="NAME", help="移除 server")
    ap.add_argument("--sync", action="store_true", help="registry → 当前客户端配置")
    ap.add_argument("--test", metavar="NAME", help="server 存活握手")
    ap.add_argument("--wrap", metavar="DIR", help="把目录内可执行文件包装成 MCP stdio server")
    ap.add_argument("--disable", metavar="NAME", help="热关：禁用 server（gateway 立即拒绝，无需重启）")
    ap.add_argument("--enable", metavar="NAME", help="热开：重新启用 server")
    ap.add_argument("--client-sync", action="store_true", help="[可选] 额外把 registry 编译进当前客户端配置（默认不写客户端 config，走 mcp_gateway 热启动）")
    ap.add_argument("--name", help="server 名（--add/--wrap 用）")
    ap.add_argument("--classes", help="server 归属分类（crack/reverse/pentest/game/ai/assist，逗号分隔可多选；写入路由页的依据）")
    ap.add_argument("--desc", help="server 一句话说明（显示在路由页工具条目里）")
    ap.add_argument("--cmd", help="stdio 启动命令")
    ap.add_argument("--args", nargs=argparse.REMAINDER, help='stdio 启动参数（--args 后全部原样接收，无需引号包裹；如 --args --stdio --port 5000）')
    ap.add_argument("--url", help="http/streamable URL")
    ap.add_argument("--headers", nargs="*", help="http 头（Key=Value ...）")
    ap.add_argument("--env", nargs="*", help="stdio 环境变量（KEY=VALUE ...）")
    ap.add_argument("--cwd", help="stdio 工作目录")
    ap.add_argument("--timeout", type=int, help="调用超时毫秒（stdio/http 通用，落盘 registry；默认 600000）")
    ap.add_argument("--list", action="store_true", help="列出 registry")
    ap.add_argument("--dry-run", action="store_true", help="只预览不写")
    ap.add_argument("--set-root", metavar="DIR", help="锁存 MCP 工作目录（首次询问后的落盘动作）")
    ap.add_argument("--target", help="显式指定配置文件路径（仅 --client-sync 时使用）")
    a = ap.parse_args()

    if a.set_root:
        return cmd_set_root(a)
    if a.check:
        return cmd_check()
    if a.list:
        return cmd_list()
    if a.add:
        return cmd_add(a)
    if a.remove is not None:
        return cmd_remove(a)
    if a.disable:
        return cmd_disable(a)
    if a.enable:
        return cmd_enable(a)
    if a.sync or a.target:
        return cmd_sync(dry=a.dry_run, target=a.target)
    if a.test:
        return cmd_test(a)
    if a.wrap:
        return cmd_wrap(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
