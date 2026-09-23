#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 command_aliases.json：
  1) 删除与授权对象词表冲突的键（如「策略」）
  2) 重建历史损坏键（中文被写成 ? 的 64 个键）为可读中文词
  3) 纯 ? 键（无法推断）直接删除
用法: python repair_aliases.py
"""
from __future__ import annotations

import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIAS_FILE = os.path.join(SKILL_DIR, "config", "command_aliases.json")
OBJECTS_FILE = os.path.join(SKILL_DIR, "config", "system_objects.json")

# 损坏键 -> 重建词（根据 targets 技能语义推断）
REBUILD = {
    "??DoS": "合约DoS",
    "AMM??": "AMM审计",
    "MCP????": "MCP协议攻击",
    "Agent????": "Agent工具滥用",
    "RAG??": "RAG投毒",
    "CORS??": "CORS漏洞",
    "CRLF??": "CRLF注入",
    "CDN??": "CDN绕过",
    "WAF??": "WAF绕过",
    "CNAME??": "CNAME欺骗",
    "ARP??": "ARP欺骗",
    "DHCP??": "DHCP攻击",
    "VLAN??": "VLAN跳跃",
    "802.1x??": "802.1x绕过",
    "STP??": "STP攻击",
    "DNS??": "DNS隧道",
    "BGP??": "BGP劫持",
    "OSPF??": "OSPF攻击",
    "DLL??": "DLL注入",
    "DLL????": "DLL劫持",
    "APC??": "APC注入",
    "COM??": "COM劫持",
    "WMI??": "WMI滥用",
    "PATH??": "PATH劫持",
    "crontab??": "crontab后门",
    "SSH??": "SSH隧道",
    "LKM??": "LKM后门",
    "Rootkit??": "Rootkit后门",
    "bash??": "bash后门",
    "shell??????": "shell反弹",
    "SS7??": "SS7攻击",
    "IMSI??": "IMSI捕获",
    "SIM???": "SIM卡攻击",
    "SIM??": "SIM克隆",
    "eSIM??": "eSIM攻击",
    "WiFi??": "WiFi攻击",
    "CBC??": "CBC翻转",
    "ECB??": "ECB重放",
    "IV??": "IV重用",
    "nonce??": "nonce重用",
    "Terraform??": "Terraform漏洞",
    "Web??": "Web漏洞",
    "SSRF?": "SSRF攻击",
    "XXE?": "XXE攻击",
    "XSS?": "XSS攻击",
    "JWT???": "JWT攻击",
    "OAuth???": "OAuth攻击",
    "??RCE?": "提示词RCE",
    "?SSRF": "盲SSRF",
    "AI???": "AI注入",
    "LLM?": "LLM攻击",
    "Agent?": "Agent攻击",
    "MCP?": "MCP攻击",
    "NFC?": "NFC攻击",
    "RFID?": "RFID攻击",
    "OTA?": "OTA攻击",
    "PLC?": "PLC攻击",
    "ICS?": "ICS攻击",
    "WiFi?": "WiFi攻击",
}

# 纯 ? 键（无法推断原文，直接删除）
PURE_QUESTION = {
    "??????", "????", "?????", "???", "???????",
}


def main() -> int:
    data = json.load(open(ALIAS_FILE, encoding="utf-8"))
    objects = json.load(open(OBJECTS_FILE, encoding="utf-8")).get("objects", [])
    obj_set = {o.lower() for o in objects}

    red = data.setdefault("red", {})
    blue = data.setdefault("blue", {})
    dropped, rebuilt, conflict = [], [], []

    # 1) 删除与对象词表冲突的键（red + blue）
    for table_name in ("red", "blue"):
        table = data[table_name]
        for k in list(table.keys()):
            if k.lower() in obj_set:
                del table[k]
                conflict.append(k)

    # 2) 重建损坏键（仅 red；blue 无损坏）
    for bad, good in REBUILD.items():
        if bad in red:
            val = red.pop(bad)
            if good not in red:
                red[good] = val
                rebuilt.append((bad, good))
            else:
                # 合并到已有词
                old = red[good]
                red[good] = list(dict.fromkeys(old + val))
                rebuilt.append((bad, good + " (合并)"))

    # 3) 删除纯 ? 键
    for bad in PURE_QUESTION:
        if bad in red:
            del red[bad]
            dropped.append(bad)

    json.dump(data, open(ALIAS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] 冲突删除: {conflict}")
    print(f"[OK] 损坏重建: {len(rebuilt)}")
    for bad, good in rebuilt:
        print(f"      {bad!r} -> {good}")
    print(f"[OK] 纯问号删除: {dropped}")
    print(f"[OK] red 总数: {len(red)} | blue 总数: {len(blue)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
