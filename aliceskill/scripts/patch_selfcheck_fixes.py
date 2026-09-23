#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自检修复补丁：清理死链模块 id + 补齐缺失的方法论路由词。

自检发现的两类真实缺陷：
  1. config/command_aliases.json 中有 4 个模块 id 指向已不存在的模块（死链），
     路由命中后取不到模块正文；生成脚本里也写死了同样 4 个 id，
     重跑生成器会把死链写回文档。
  2. 5 个方法论路由词（方法论/系统化调试/头脑风暴/计划编写/完成前验证）在 red 表缺失，
     check_method_routes.py 因此 FAIL。

修法（数据源优先）：
  - 别名表里的死链按语义替换为已存在的等价模块，并去重；
  - 生成脚本里，死链作为「字典键」的条目整条删除（避免与已有键重复），
    作为「列表元素」的替换为等价模块；
  - 每个 .py 改完立即用 ast.parse 校验语法，语法不过就整文件回滚不写。

幂等：重复执行结果一致。

用法:
  python patch_selfcheck_fixes.py            # 落盘
  python patch_selfcheck_fixes.py --dry-run  # 只预览
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
MODULES_ROOT = os.path.abspath(os.path.join(SKILL_DIR, "..", "_modules"))

# 死链 id -> 已存在的等价模块 id（脚本启动时校验替代目标真实存在）
DEAD_TO_LIVE = {
    "analyzing-packed-malware-with-upx-unpacker": "re-flow-unpack",
    "deobfuscating-powershell-obfuscated-malware": "code-obfuscate",
    "exploiting-zerologon-vulnerability-cve-2020-1472": "competition-identity-windows",
    "ai-agent-tool-abuse-and-privilege-escalation": "pentest-ai-agents",
}

# check_method_routes.py 的期望映射
METHOD_WORDS = {
    "方法论": ["alice-progressive", "research-rigor"],
    "系统化调试": ["hardware-breakpoint-observation"],
    "头脑风暴": ["alice-progressive"],
    "计划编写": ["alice-progressive"],
    "完成前验证": ["research-rigor"],
}

GEN_FILES = ["absorb_routes.py", "add_llm_offense_routes.py", "add_method_routes.py",
             "build_commands.py", "build_manual.py", "build_master.py"]

log: list[str] = []


def note(msg: str) -> None:
    log.append(msg)
    print(msg)


def exists_mod(name: str) -> bool:
    return os.path.isfile(os.path.join(MODULES_ROOT, name, "SKILL.md"))


# ---- 生成脚本改写：区分「字典键」与「列表元素」 ----
def patch_py(raw: str) -> tuple[str, int, int]:
    """返回 (新内容, 删除键数, 替换列表元素数)。"""
    removed = 0
    replaced = 0
    for dead, live in DEAD_TO_LIVE.items():
        # 反复扫描，直到该 id 不再出现
        while True:
            m = re.search(r'"' + re.escape(dead) + r'"', raw)
            if not m:
                break
            tail = raw[m.end():]
            if re.match(r'\s*:', tail):
                # 字典键：删除 "id": <value> 这一项（value 为字符串或同行列表）
                val = re.match(r'\s*:\s*(?:"(?:[^"\\]|\\.)*"|\[[^\]]*\])', tail)
                if not val:
                    raise SystemExit(f"[ABORT] 无法解析字典项: {dead}")
                start, end = m.start(), m.end() + val.end()
                # 连同前导或后继的逗号与空白一起吃掉
                pre = raw[:start]
                pre_trim = pre.rstrip()
                post = raw[end:]
                if pre_trim.endswith(","):
                    pre = pre_trim[:-1] + (" " if post[:1] in " \t" else "")
                    end = start  # 不额外吃
                    raw = pre + post
                elif post.lstrip().startswith(","):
                    consumed = len(post) - len(post.lstrip()) + 1
                    raw = raw[:start] + post[consumed:]
                else:
                    raw = raw[:start] + post
                removed += 1
            else:
                # 列表元素：替换为等价模块
                raw = raw[:m.start()] + f'"{live}"' + raw[m.end():]
                replaced += 1
    return raw, removed, replaced


def main() -> int:
    dry = "--dry-run" in sys.argv

    for live in set(DEAD_TO_LIVE.values()):
        if not exists_mod(live):
            raise SystemExit(f"[ABORT] 替代模块不存在: {live}")

    # ---- 1. 别名表 ----
    alias_file = os.path.join(SKILL_DIR, "config", "command_aliases.json")
    data = json.load(open(alias_file, encoding="utf-8"))
    changed = 0
    for table in ("red", "blue"):
        for word, targets in list(data.get(table, {}).items()):
            out, seen, dropped = [], set(), []
            for t in targets:
                nt = DEAD_TO_LIVE.get(t, t)
                if not exists_mod(nt):
                    seen.add(nt)
                    continue
                if nt in seen:
                    dropped.append(nt)
                    continue
                seen.add(nt)
                out.append(nt)
                if nt != t:
                    note(f"[1] {table}/{word}: {t} -> {nt}")
                    changed += 1
            if dropped:
                note(f"[1] {table}/{word}: 去掉重复 {sorted(set(dropped))}")
            data[table][word] = out
    for word, targets in METHOD_WORDS.items():
        if data["red"].get(word) != targets:
            data["red"][word] = list(targets)
            note(f"[1] red/{word}: 补齐路由 -> {targets}")
            changed += 1
    if changed and not dry:
        tmp = alias_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, alias_file)
        note("    [OK] 已原子写入 config/command_aliases.json")

    # ---- 2. 生成脚本内的死链字面量 ----
    for fname in GEN_FILES:
        path = os.path.join(THIS_DIR, fname)
        if not os.path.isfile(path):
            continue
        raw = open(path, encoding="utf-8").read()
        if not any(d in raw for d in DEAD_TO_LIVE):
            continue
        new, removed, replaced = patch_py(raw)
        try:
            ast.parse(new)
        except SyntaxError as exc:
            raise SystemExit(f"[ABORT] {fname} 改写后语法错误，已放弃该文件: {exc}")
        if removed or replaced:
            note(f"[2] {fname}: 删除字典项 {removed} 处，替换列表元素 {replaced} 处"
                 + (" (dry-run)" if dry else ""))
            if not dry:
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    fh.write(new)
                os.replace(tmp, path)

    if not changed and not dry:
        note("[OK] 别名表无需改动（已修复过）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
