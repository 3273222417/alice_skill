#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收尾补丁 ③：把 re-skill-suite 10 技能挂进 battle_manual 的攻/防小方面（幂等）。"""
from __future__ import annotations
import os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(THIS, "build_manual.py")
src = open(P, encoding="utf-8").read()

PATCHES = [
    # 攻 2. 信息收集与协议 → 新增抓包小方面
    ('''            "2.2 协议逆向": ["protocol-reverse-engineering", "competition-custom-protocol-replay",
                          "competition-pcap-protocol"],
        },''',
     '''            "2.2 协议逆向": ["protocol-reverse-engineering", "competition-custom-protocol-replay",
                          "competition-pcap-protocol"],
            "2.3 抓包与明文取证": ["re-flow-capture"],
        },'''),
    # 攻 3. 二进制逆向 → 新增流程编排 / 隔离环境 / 工具环境三个小方面
    ('''            "3.4 文件解析": ["competition-file-parser-chain", "competition-reverse-pwn"],
        },''',
     '''            "3.4 文件解析": ["competition-file-parser-chain", "competition-reverse-pwn"],
            "3.5 逆向流程编排": ["re-flow-orchestrator", "re-flow-recon", "re-flow-analyze"],
            "3.6 隔离环境与回滚": ["re-env-sandbox"],
            "3.7 工具环境（注册/下载/登记）": ["re-tool-registry", "re-tool-downloader", "re-tool-manifest"],
            "3.8 授权与激活逆向": ["windows-license-crack"],
        },'''),
]

n = 0
for old, new in PATCHES:
    if new in src:
        print("  [skip] 已应用")
        continue
    if old not in src:
        print("  [!] 锚点未命中")
        continue
    src = src.replace(old, new, 1)
    n += 1

# 脱壳小方面补 re-flow-unpack
old_unpack = '''    "3.2 差分与补丁": ["binary-diff", "patch-diff-exploit"],'''
new_unpack = '''    "3.2 差分与补丁": ["binary-diff", "patch-diff-exploit"],
            "3.9 脱壳流程编排": ["re-flow-unpack"],'''
if new_unpack not in src and old_unpack in src:
    src = src.replace(old_unpack, new_unpack, 1)
    n += 1
elif new_unpack in src:
    print("  [skip] 3.9 已应用")

open(P, "w", encoding="utf-8").write(src)
print(f"  [ok] build_manual.MANUAL: 应用 {n} 处")
