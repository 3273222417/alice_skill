#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HELP.md 同步 re-skill-suite 吸收（方法论表补 A29 + 新增逆向流程板块 + 统计更新）。幂等。"""
from __future__ import annotations
import os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS)
P = os.path.join(SKILL_DIR, "references", "HELP.md")
src = open(P, encoding="utf-8").read()


def rep(old, new, label):
    global src
    if new in src:
        print(f"  [skip] {label}")
        return
    if old not in src:
        print(f"  [!] 锚点未命中: {label}")
        return
    src = src.replace(old, new, 1)
    print(f"  [ok] {label}")


# ① 方法论表补 A29
rep("| A28 | 技能编写 | `writing-skills` | 写新技能 |\n",
    "| A28 | 技能编写 | `writing-skills` | 写新技能 |\n"
    "| A29 | 破解总编排 | `re-flow-orchestrator` | 完整破解任务状态机总指挥 |\n",
    "方法论表 A29")

# ② 分类速查表：D 行补新技能指向
rep("| D 二进制逆向 | EXE/ELF/SO/DLL 逆向 | `攻 二进制`、`攻 脱壳`、`攻 OLLVM` |",
    "| D 二进制逆向 | EXE/ELF/SO/DLL 逆向 | `攻 二进制`、`攻 脱壳`、`攻 OLLVM`；"
    "新增流程编排链：`攻 完整破解`、`攻 查壳`、`攻 隔离环境`、`攻 脱壳流程`、"
    "`攻 下载工具`、`攻 已装工具`、`攻 卡密` |",
    "分类速查 D 行")

# ③ 5.7 补 re-skill-suite 吸收段
rep("### 已吸收的路由词（148 新增 + 40 合并）",
    """### 已吸收：re-skill-suite（10 技能 · 逆向破解全流程链）
```
re-flow-orchestrator  破解总编排（INIT→ENV→SANDBOX→RECON→CAPTURE→UNPACK→ANALYZE→BYPASS→PACKAGE→DONE）
re-env-sandbox        隔离环境 / 回滚 / 反虚拟机 / 符号服务器
re-flow-recon         查壳 / 行为侦察 / 路线决策 / 目标画像
re-flow-capture       抓包 / HTTPS 解密 / 强制转发 / 协议明文
re-flow-unpack        脱壳 / 找 OEP / 修复 IAT / 反调试对抗
re-flow-analyze       定位关键校验函数 / 断点 / 数据流追踪 / 补丁回归
re-tool-registry      工具注册表（下载清单）  re-tool-downloader 工具下载执行
re-tool-manifest      环境登记簿（已装工具 / 环境检查）
windows-license-crack 授权/激活逆向 + 运行时绕过（卡密 / 注册机 / 验签绕过）
```
一句话开打：`攻 完整破解`、`攻 隔离环境`、`攻 查壳`、`攻 脱壳流程`、`攻 抓包流程`、
`攻 下载工具`、`攻 已装工具`、`攻 卡密`、`攻 注册机`。

### 已吸收的路由词（148 新增 + 40 合并）""",
    "5.7 re-skill-suite 段")

# ④ 统计行
rep("> 生成于 2026-08-10 · 全量数据：309 技能 / 14 大分类 / 204 小分类 / 539 命令词 / 1576 中文路由词",
    "> 生成于 2026-08-10 · 更新 2026-09-18（吸收 re-skill-suite 10 技能）"
    " · 全量数据：320 技能 / 15 大分类 / 566 命令词 / 1951 中文路由词",
    "统计行")

open(P, "w", encoding="utf-8", newline="\n").write(src)
print("[完成] HELP.md 同步")
