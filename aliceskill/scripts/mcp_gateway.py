#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mcp_gateway.py — Alice 技能侧 MCP 网关（热启动，零客户端配置）
==============================================================
MCP server 不写入任何客户端 config；由本网关按 registry 直接 spawn 进程、
走 stdio JSON-RPC 取工具目录与调用结果，以普通命令输出喂给 agent。

热开关：registry 里 disabled=true/false 即时生效，无需重启客户端。

用法:
  python mcp_gateway.py list [--json]              # 所有启用 server 的工具目录（agent 发现入口）
  python mcp_gateway.py list <server> [--json]     # 单 server 工具目录
  python mcp_gateway.py call <server> <tool> [JSON参数] [--timeout N]
  python mcp_gateway.py ping [server]              # 握手存活（缺省=全部）
  python mcp_gateway.py start <server>             # 预热常驻（后台池）
  python mcp_gateway.py stop <server>|--all        # 关闭常驻
  python mcp_gateway.py status                     # 常驻池状态

退出码: 0 成功 | 2 参数/registry 错误 | 3 server 不可用 | 4 工具调用失败
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
SETTINGS = os.path.join(SKILL_DIR, "config", "mcp_settings.json")
POOL_DIR = os.path.join(SKILL_DIR, "mcp-pool")   # 常驻池心跳文件目录

INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "alice-gateway", "version": "1.0"}}}
INITED = {"jsonrpc": "2.0", "method": "notifications/initialized"}


def die(code: int, msg: str):
    print(f"[!] {msg}")
    raise SystemExit(code)


def read_json(path: str) -> dict:
    with open(path, "rb") as fh:
        raw = fh.read()
    return json.loads(raw.decode("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"))


def load_settings() -> dict:
    if os.path.isfile(SETTINGS):
        return read_json(SETTINGS)
    return {}


def registry() -> dict:
    root = load_settings().get("mcpRoot")
    if not root:
        die(3, "MCP 工作目录未锁存：先运行 mcp_manager.py --add（会询问用户）或 --set-root")
    p = os.path.join(root, "servers.json")
    if not os.path.isfile(p):
        die(3, f"registry 不存在: {p}")
    return read_json(p)


def entry(name: str) -> dict:
    reg = registry()
    e = reg.get("servers", {}).get(name)
    if not e:
        die(2, f"registry 中不存在: {name}（可用: {', '.join(reg.get('servers', {})) or '无'}）")
    return dict(e, name=name)


# ---------------------------------------------------------------- stdio 会话

class StdioSession:
    """单次 server 会话：spawn → initialize → 系列调用 → 关闭。

    协议要点：JSON-RPC 通知（无 id）不产生回包，写入后不读；请求（有 id）
    逐个读行匹配 id。任何一步超时即判定 server 不可用。"""

    def __init__(self, e: dict, timeout: int = 30):
        self.e = e
        self.timeout = timeout
        self.p: subprocess.Popen | None = None
        self._id = 10

    def __enter__(self):
        env = dict(os.environ)
        env.update(self.e.get("env") or {})
        env.setdefault("PYTHONIOENCODING", "utf-8")
        self.p = subprocess.Popen(
            [self.e["command"]] + list(self.e.get("args") or []),
            cwd=self.e.get("cwd") or None, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace", bufsize=1)
        r = self.rpc(INIT)
        si = (r.get("result") or {}).get("serverInfo") or {}
        self.server_info = si
        self.rpc(INITED)
        return self

    def __exit__(self, *exc):
        try:
            if self.p:
                self.p.terminate()
                try:
                    self.p.wait(timeout=5)
                except Exception:
                    self.p.kill()
        except Exception:
            pass
        return False

    def _readline(self, timeout: int) -> str:
        box: dict = {}
        th = threading.Thread(target=lambda: box.update(line=self.p.stdout.readline()), daemon=True)
        th.start()
        th.join(timeout)
        if "line" not in box:
            raise TimeoutError(f"{self.e.get('name')}: {timeout}s 内无响应")
        return box["line"]

    def rpc(self, obj: dict, timeout: int | None = None) -> dict | None:
        self.p.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.p.stdin.flush()
        if "id" not in obj:
            return None
        t = timeout or self.timeout
        deadline = time.time() + t
        while time.time() < deadline:
            line = self._readline(int(deadline - time.time()) or 1)
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == obj["id"]:
                if "error" in msg:
                    raise RuntimeError(f"server error: {msg['error']}")
                return msg
            # 其它 id 的迟到回包丢弃（常驻池场景）
        raise TimeoutError(f"{self.e.get('name')}: 回包超时（id={obj['id']}）")

    def tools(self) -> list[dict]:
        r = self.rpc({"jsonrpc": "2.0", "id": self._next(), "method": "tools/list"})
        return (r.get("result") or {}).get("tools") or []

    def call(self, tool: str, arguments: dict, timeout: int) -> dict:
        return self.rpc({"jsonrpc": "2.0", "id": self._next(), "method": "tools/call",
                         "params": {"name": tool, "arguments": arguments or {}}}, timeout=timeout)

    def _next(self) -> int:
        self._id += 1
        return self._id


def open_session(name: str, timeout: int) -> StdioSession:
    e = entry(name)
    if e.get("disabled"):
        die(3, f"{name} 已被禁用（registry disabled=true）；用 mcp_manager.py --enable {name} 打开")
    # registry 里的 timeout（毫秒）优先于命令行默认；命令行显式传值 > 0 时以命令行为准
    reg_ms = int(e.get("timeout") or 0)
    eff = max(1, (reg_ms // 1000) or timeout)
    if e.get("url"):
        return HttpSession(e, timeout=eff).__enter__()
    try:
        return StdioSession(e, timeout=eff).__enter__()
    except FileNotFoundError as ex:
        die(3, f"{name} 启动失败（命令不存在）: {ex}")
    except TimeoutError as ex:
        die(3, f"{name} 握手失败: {ex}")
    except Exception as ex:
        die(3, f"{name} 启动异常: {ex}")


# ---------------------------------------------------------------- HTTP 会话（Streamable HTTP / SSE 降级）

def _http_post(url: str, payload: str, headers: dict, timeout: int) -> tuple[int, dict, str]:
    """POST JSON，返回 (status, response_headers, body_text)。标准库实现，无第三方依赖。"""
    import urllib.request
    import urllib.error
    req = urllib.request.Request(url, data=payload.encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as ex:
        body = ""
        try:
            body = ex.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return ex.code, dict(ex.headers or {}), body


def _parse_sse_or_json(body: str) -> dict | None:
    """Streamable HTTP 响应可能是 application/json 或 text/event-stream（SSE）。
    SSE 里取第一个 data: 行的 JSON（MCP 响应事件）；无则尝试整段当 JSON。"""
    if "data:" in body:
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data = line[5:].strip()
                if data and data != "[DONE]":
                    try:
                        return json.loads(data)
                    except json.JSONDecodeError:
                        continue
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


class HttpSession:
    """Streamable HTTP 传输会话：与 StdioSession 同接口（server_info/tools/call/rpc）。

    每次rpc 一个 POST；无状态模式（大多数 remote MCP 如 github 支持无会话）。
    若 server 返回 Mcp-Session-Id 头则保存并在后续请求带上（有状态模式）。"""

    def __init__(self, e: dict, timeout: int = 30):
        self.e = e
        self.timeout = timeout
        self.headers = dict(e.get("headers") or {})
        self.session_id: str | None = None
        self.server_info: dict = {}

    def __enter__(self):
        r = self.rpc(INIT)
        res = r.get("result") or {}
        self.server_info = res.get("serverInfo") or {}
        self.rpc({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return self

    def __exit__(self, *exc):
        return False

    def rpc(self, obj: dict, timeout: int | None = None) -> dict | None:
        if "id" not in obj:
            return None  # HTTP 下通知通常无需单独发送（无状态）
        status, rh, body = _http_post(self.e["url"], json.dumps(obj, ensure_ascii=False),
                                      self._hdrs(), timeout or self.timeout)
        sid = (rh.get("Mcp-Session-Id") or rh.get("mcp-session-id"))
        if sid:
            self.session_id = sid
        if status in (401, 403):
            raise RuntimeError(f"HTTP {status} 认证失败：检查 registry 里的 headers（如 Authorization）")
        if status == 404 and self.session_id:
            # 有状态会话过期 → 丢掉 sid 重试一次
            self.session_id = None
            status, rh, body = _http_post(self.e["url"], json.dumps(obj, ensure_ascii=False),
                                          self._hdrs(), timeout or self.timeout)
        if status >= 400:
            raise RuntimeError(f"HTTP {status}: {body[:200]}")
        if not body.strip():
            return {}  # 202 Accepted（纯通知）
        msg = _parse_sse_or_json(body)
        if msg is None:
            raise RuntimeError(f"无法解析响应（HTTP {status}）: {body[:200]}")
        if "error" in msg:
            raise RuntimeError(f"server error: {msg['error']}")
        return msg

    def _hdrs(self) -> dict:
        h = dict(self.headers)
        if self.session_id:
            h["Mcp-Session-Id"] = self.session_id
        return h

    def tools(self) -> list[dict]:
        r = self.rpc({"jsonrpc": "2.0", "id": 100, "method": "tools/list"})
        return (r.get("result") or {}).get("tools") or []

    def call(self, tool: str, arguments: dict, timeout: int) -> dict:
        return self.rpc({"jsonrpc": "2.0", "id": 101, "method": "tools/call",
                         "params": {"name": tool, "arguments": arguments or {}}}, timeout=timeout)


# ---------------------------------------------------------------- 常驻池

def pool_file(name: str) -> str:
    return os.path.join(POOL_DIR, f"{re.sub(r'[^A-Za-z0-9_-]', '_', name)}.json")


def pool_read(name: str) -> dict | None:
    p = pool_file(name)
    if not os.path.isfile(p):
        return None
    try:
        d = read_json(p)
        pid = int(d.get("pid", 0))
        if pid and os.name == "nt":
            # 心跳超 10 分钟视为死进程
            if time.time() - d.get("ts", 0) > 600:
                return None
        return d
    except Exception:
        return None


def pool_write(name: str, pid: int, info: dict) -> None:
    os.makedirs(POOL_DIR, exist_ok=True)
    write_json(pool_file(name), {"pid": pid, "ts": time.time(), "info": info})


def write_json(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ---------------------------------------------------------------- 子命令

def cmd_list(args) -> int:
    reg = registry()
    servers = reg.get("servers", {})
    if args.server:
        servers = {args.server: servers.get(args.server) or die(2, f"registry 中不存在: {args.server}")}
    if getattr(args, "class_filter", None):
        cf = args.class_filter
        servers = {n: e for n, e in servers.items()
                   if cf in (e.get("classes") or e.get("class") or [])} or \
                  die(2, f"没有分类为 {cf} 的 server（registry 分类字段: classes=[...]；可用类: crack/reverse/pentest/game/ai/assist）")
    out = {}
    for name, raw in servers.items():
        e = dict(raw, name=name)
        if e.get("disabled"):
            out[name] = {"state": "disabled"}
            continue
        try:
            with open_session(name, args.timeout) as s:
                tools = s.tools()
                out[name] = {"state": "ok", "serverInfo": s.server_info, "tools": [
                    {"name": t.get("name"), "description": (t.get("description") or "")[:200]}
                    for t in tools]}
        except SystemExit:
            out[name] = {"state": "unavailable", "error": "disabled or unknown"}
        except Exception as ex:
            out[name] = {"state": "unavailable", "error": str(ex)[:200]}
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    total = 0
    for name, info in out.items():
        if info["state"] != "ok":
            print(f"- {name}  [{info['state']}] {info.get('error', '')}")
            continue
        ts = info["tools"]
        total += len(ts)
        print(f"- {name}  [{info['serverInfo'].get('name', '?')}] {len(ts)} 个工具")
        for t in ts:
            print(f"    mcp__{name}__{t['name']}  — {t['description'][:110]}")
    print(f"\n共 {total} 个工具。调用方式: python mcp_gateway.py call <server> <tool> '{{\"参数\": ...}}'")
    return 0


def cmd_call(args) -> int:
    try:
        arguments = json.loads(args.arguments) if args.arguments else {}
    except json.JSONDecodeError as ex:
        die(2, f"参数不是合法 JSON: {ex}")
    try:
        with open_session(args.server, timeout=30) as s:
            r = s.call(args.tool, arguments, timeout=args.timeout)
    except TimeoutError as ex:
        die(4, str(ex))
    except RuntimeError as ex:
        die(4, str(ex))
    result = r.get("result") or {}
    if result.get("isError"):
        die(4, "工具返回错误: " + json.dumps(result.get("content"), ensure_ascii=False)[:400])
    for c in result.get("content") or []:
        if c.get("type") == "text":
            print(c.get("text", ""))
    return 0


def cmd_ping(args) -> int:
    reg = registry()
    names = [args.server] if args.server else list(reg.get("servers", {}).keys())
    if args.server and args.server not in reg.get("servers", {}):
        die(2, f"registry 中不存在: {args.server}")
    bad = 0
    for n in names:
        e = dict(reg["servers"][n], name=n)
        if e.get("disabled"):
            print(f"- {n}  [disabled]")
            continue
        try:
            with open_session(n, args.timeout) as s:
                print(f"- {n}  [✓] {s.server_info}")
        except SystemExit:
            raise
        except Exception as ex:
            bad += 1
            print(f"- {n}  [✗] {str(ex)[:160]}")
    return 3 if bad else 0


def cmd_start(args) -> int:
    """预热：spawn 常驻进程，落心跳文件；工具调用走 manager --call 时优先复用。"""
    e = entry(args.server)
    if e.get("disabled"):
        die(3, f"{args.server} 已禁用")
    env = dict(os.environ)
    env.update(e.get("env") or {})
    env.setdefault("PYTHONIOENCODING", "utf-8")
    # detached 常驻：由本进程派生的子进程在父进程退出后由 server 自行存活（stdio 等待输入）
    p = subprocess.Popen([e["command"]] + list(e.get("args") or []),
                         cwd=e.get("cwd") or None, env=env,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         text=True, encoding="utf-8", errors="replace")
    pool_write(args.server, p.pid, {"command": e["command"], "started": time.time()})
    print(f"[✓] {args.server} 已预热常驻（pid={p.pid}，心跳 {pool_file(args.server)}）")
    print("[i] 常驻进程由独立心跳文件跟踪；mcp_manager.py --stop <name> 可关闭")
    return 0


def cmd_stop(args) -> int:
    names = list(registry().get("servers", {}).keys()) if args.all else [args.server]
    if args.all:
        args.server = None
    for n in names:
        d = pool_read(n)
        if not d:
            print(f"- {n}  无常驻记录，跳过")
            continue
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(d["pid"]), "/T", "/F"],
                               capture_output=True, timeout=15)
            else:
                import signal
                os.kill(d["pid"], signal.SIGTERM)
            print(f"- {n}  已停止（pid={d['pid']}）")
        except Exception as ex:
            print(f"- {n}  停止失败: {ex}")
        try:
            os.remove(pool_file(n))
        except Exception:
            pass
    return 0


def cmd_status() -> int:
    reg = registry().get("servers", {})
    print(f"{'server':<20}{'状态':<12}{'常驻':<10}备注")
    for n, e in reg.items():
        st = "disabled" if e.get("disabled") else "enabled"
        d = pool_read(n)
        pool = f"pid={d['pid']}" if d else "-"
        print(f"{n:<20}{st:<12}{pool:<10}{(e.get('url') or e.get('command') or '')[:60]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Alice MCP 网关：技能侧热启动，零客户端配置")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="工具目录（agent 发现入口）")
    p.add_argument("server", nargs="?")
    p.add_argument("--json", action="store_true")
    p.add_argument("--class", dest="class_filter", help="只看属于某类（crack/reverse/pentest/game/ai/assist）的 server")
    p.add_argument("--timeout", type=int, default=30)
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("call", help="调用工具")
    p.add_argument("server")
    p.add_argument("tool")
    p.add_argument("arguments", nargs="?", default="")
    p.add_argument("--timeout", type=int, default=300)
    p.set_defaults(fn=cmd_call)

    p = sub.add_parser("ping", help="握手存活")
    p.add_argument("server", nargs="?")
    p.add_argument("--timeout", type=int, default=20)
    p.set_defaults(fn=cmd_ping)

    p = sub.add_parser("start", help="预热常驻")
    p.add_argument("server")
    p.set_defaults(fn=cmd_start)

    p = sub.add_parser("stop", help="关闭常驻")
    p.add_argument("server", nargs="?")
    p.add_argument("--all", action="store_true")
    p.set_defaults(fn=cmd_stop)

    p = sub.add_parser("status", help="池状态")
    p.set_defaults(fn=lambda a: cmd_status())

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
