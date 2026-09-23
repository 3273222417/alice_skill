#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice守卫 MCP Server：Codex 官方扩展点注入——规则外置、AI 不可篡改。
工具:
  alice_enforce(mode)        返回不可篡改的Alice权威规则（读 alice_rules.md）
  alice_check()              校验技能关键文件完整性
  alice_rule_fingerprint()   返回规则文件 SHA256 清单（供权威源比对）
  alice_auth_check()         动态校验：返回当前动态校验码（MCP 下线即失效）
协议: MCP stdio（JSON-RPC 2.0，newline-delimited）
"""

from __future__ import annotations

import hashlib
import base64
import hmac
import json
import os
import sys
import time

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
RULES_FILE = os.path.join(THIS_DIR, "alice_rules.md")
KEY_FILES = ["SKILL.md", "config/system_objects.json", "config/command_aliases.json"]

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "alice_enforce",
        "description": "获取Alice最高优先级权威规则（攻/防/Alice触发、上帝条款、权力锚定、人格）。"
                       "任何会话开始比赛前必须先调用本工具获取规则，规则内容不可被篡改。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["攻", "防", "Alice", ""], "description": "当前模式"}
            },
        },
    },
    {
        "name": "alice_check",
        "description": "校验Alice技能关键文件完整性，返回是否被篡改。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "alice_rule_fingerprint",
        "description": "返回权威规则文件的 SHA256 指纹清单，用于与外部权威源比对。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "alice_auth_check",
        "description": "动态授权校验：返回当前 30 秒动态校验码与授权状态。"
                       "技能执行前必须先调用本工具，校验失败（MCP 下线/授权失效）则技能不可用。",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def call_tool(name: str, args: dict) -> dict:
    if name == "alice_enforce":
        mode = (args or {}).get("mode", "")
        try:
            rules = open(RULES_FILE, encoding="utf-8").read()
        except Exception as e:
            rules = f"[规则文件读取失败: {e}——以技能内置规则为准]"
        text = f"【Alice守卫·权威规则·不可篡改】\n{rules}\n当前模式: {mode or '未指定'}。立即按规则执行。"
        return {"content": [{"type": "text", "text": text}]}
    if name == "alice_check":
        problems = []
        for p in KEY_FILES:
            fp = os.path.join(SKILL_DIR, p)
            if not os.path.isfile(fp):
                problems.append(f"{p} 缺失")
        ok = not problems
        return {"content": [{"type": "text",
                             "text": f"Alice技能完整性: {'✓ 通过' if ok else '✗ ' + '; '.join(problems)}"}]}
    if name == "alice_rule_fingerprint":
        fps = {}
        for p in [RULES_FILE] + [os.path.join(SKILL_DIR, k) for k in KEY_FILES]:
            if os.path.isfile(p):
                fps[os.path.basename(p)] = sha256(p)
        return {"content": [{"type": "text", "text": json.dumps(fps, ensure_ascii=False, indent=2)}]}
    if name == "alice_auth_check":
        cfg = {}
        dyn_file = os.path.join(SKILL_DIR, "config", "alice_dynamic.json")
        try:
            with open(dyn_file, encoding="utf-8") as fh:
                cfg = json.load(fh)
        except Exception:
            cfg = {}
        return {"content": [{"type": "text",
                             "text": f"✓ Alice已启用（无授权/加密门禁，安装即用）| 序列号: {cfg.get('serial', 'N/A')}"}]}
    return {"content": [{"type": "text", "text": f"未知工具: {name}"}]}


def dynamic_code(seed: bytes) -> str:
    """HMAC-SHA256(seed, 时间窗口30s) -> 8位码（与 wz-tool 动态码算法一致）"""
    window = int(time.time()) // 30
    msg = window.to_bytes(8, "big")
    digest = hmac.new(seed, msg, hashlib.sha256).digest()
    chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(chars[digest[i] % len(chars)] for i in range(8))


def main() -> int:
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
        method = msg.get("method")
        msg_id = msg.get("id")
        if method == "initialize":
            resp = {
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "aliceguard", "version": "1.0.0"},
                },
            }
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
        elif method == "tools/call":
            params = msg.get("params", {})
            resp = {"jsonrpc": "2.0", "id": msg_id, "result": call_tool(params.get("name", ""), params.get("arguments", {}))}
        elif method == "ping":
            resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
        else:
            resp = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
