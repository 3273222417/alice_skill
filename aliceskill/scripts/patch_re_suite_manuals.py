#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手册中文名补丁（build_master / build_manual）——幂等。"""
from __future__ import annotations
import os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS = os.path.dirname(os.path.abspath(__file__))
NEW = '''    "re-flow-orchestrator": "破解总编排", "re-env-sandbox": "隔离环境",
    "re-flow-recon": "逆向侦察", "re-flow-capture": "抓包流程",
    "re-flow-unpack": "脱壳流程", "re-flow-analyze": "定位与验证",
    "re-tool-registry": "工具注册表", "re-tool-downloader": "工具下载器",
    "re-tool-manifest": "环境登记簿", "windows-license-crack": "授权逆向与绕过",
'''

TARGETS = {
    "build_master.py": '    "api-call-graph-recovery": "API调用图恢复", "binary-diff": "二进制差分", "competition-file-parser-chain": "文件解析链",\n',
    "build_manual.py": '    "reverse-engineering-tools": "逆向工具集", "competition-file-parser-chain": "文件解析链",\n',
}

for f, anchor in TARGETS.items():
    p = os.path.join(THIS, f)
    src = open(p, encoding="utf-8").read()
    if '"re-flow-orchestrator"' in src:
        print(f"  [skip] {f}: 已含中文名")
        continue
    if anchor not in src:
        print(f"  [!] {f}: 锚点未命中")
        continue
    open(p, "w", encoding="utf-8").write(src.replace(anchor, anchor + NEW, 1))
    print(f"  [ok] {f}: 已补 10 个中文名")
