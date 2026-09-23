#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""re-skill-suite 吸收补丁：生成器分类规则 + 命令别名 + 手册中文名。幂等。"""
from __future__ import annotations
import os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS = os.path.dirname(os.path.abspath(__file__))

def patch(path, pairs, label):
    p = os.path.join(THIS, path)
    src = open(p, encoding="utf-8").read()
    n = 0
    for old, new in pairs:
        if new in src:
            print(f"  [skip] {label}: 已含 {old[:28]}...")
            continue
        if old in src:
            src = src.replace(old, new, 1)
            n += 1
        else:
            print(f"  [!] {label}: 未命中 {old[:48]}")
    open(p, "w", encoding="utf-8").write(src)
    print(f"  [ok] {label}: 应用 {n} 处")

# ---- ① rebuild_menu.py 分类规则：新技能名/路径优先落类 ----
patch("rebuild_menu.py", [
    ('"traffic-analysis", "tls-pinning"',
     '"traffic-analysis", "tls-pinning",\n           "re-flow-capture", "flow-capture"'),
    ('"api-call-graph", "call-graph-recovery", "webpack-vite"',
     '"api-call-graph", "call-graph-recovery", "webpack-vite",\n           "re-env-sandbox", "re-flow-recon", "re-flow-analyze", "re-flow-unpack",\n           "re-tool-", "windows-license-crack"'),
    ('"reverse-skill", "threat-modeling"',
     '"reverse-skill", "threat-modeling", "re-flow-orchestrator", "flow-orchestrator"'),
], "rebuild_menu.CAT_RULES")

# ---- ② build_commands.py 命令别名（一字一词即命令） ----
patch("build_commands.py", [
    ('    "alice-toolchain": ["alice-tc"],',
     '''    "alice-toolchain": ["alice-tc"],
    "re-flow-orchestrator": ["refo", "破解编排", "完整破解"],
    "re-env-sandbox": ["resandbox", "隔离环境", "回滚环境"],
    "re-flow-recon": ["rerecon", "查壳", "侦察"],
    "re-flow-capture": ["recap", "抓包流程"],
    "re-flow-unpack": ["reunpack", "脱壳流程"],
    "re-flow-analyze": ["reanalyze", "断点定位"],
    "re-tool-registry": ["retools", "工具注册表"],
    "re-tool-downloader": ["redl", "下载工具"],
    "re-tool-manifest": ["remanifest", "环境检查"],
    "windows-license-crack": ["winlic", "卡密", "注册机"],'''),
], "build_commands.EXTRA_ALIASES")

# ---- ③ 手册中文名映射 ----
CH_PAIRS = [
    ('    "reverse-engineering-tools", "competition-file-parser-chain": "文件解析链",',
     '''    "reverse-engineering-tools", "competition-file-parser-chain": "文件解析链",
    "re-flow-orchestrator": "破解总编排", "re-env-sandbox": "隔离环境",
    "re-flow-recon": "逆向侦察", "re-flow-capture": "抓包流程",
    "re-flow-unpack": "脱壳流程", "re-flow-analyze": "定位与验证",
    "re-tool-registry": "工具注册表", "re-tool-downloader": "工具下载器",
    "re-tool-manifest": "环境登记簿", "windows-license-crack": "授权逆向与绕过",'''),
]
for f in ("build_master.py", "build_manual.py"):
    src = open(os.path.join(THIS, f), encoding="utf-8").read()
    if '"re-flow-orchestrator"' in src:
        print(f"  [skip] {f}.CH: 已含新技能中文名")
        continue
    old, new = CH_PAIRS[0]
    if old in src:
        open(os.path.join(THIS, f), "w", encoding="utf-8").write(src.replace(old, new, 1))
        print(f"  [ok] {f}.CH: 已补 10 个中文名")
    else:
        print(f"  [!] {f}.CH: 锚点未命中，跳过（回退英文名展示）")
print("[完成] 生成器补丁就绪")
