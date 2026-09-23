#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
吸收 re-skill-suite（10 技能）进Alice技能库与路由（已归属Alice）
================================================================
① scripts/skills_data.json    追加 10 条技能（分类/编号/描述自动生成）
② config/command_aliases.json 合并中文路由词（red 表，合并 targets，不覆盖）
③ contracts/alice_contract.json  同步技能总数
④ scripts/rebuild_menu.py     补分类规则（保证以后重扫不会掉进 Z 类）

用法:
  python absorb_re_suite.py            # 执行吸收（幂等）
  python absorb_re_suite.py --check    # 只校验当前入库状态
"""
from __future__ import annotations

import argparse
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
DATA_FILE = os.environ.get("ALICE_DATA") or os.path.join(THIS_DIR, "skills_data.json")
ALIAS_FILE = os.path.join(SKILL_DIR, "config", "command_aliases.json")
OBJECTS_FILE = os.path.join(SKILL_DIR, "config", "system_objects.json")
CONTRACT_FILE = os.path.join(SKILL_DIR, "contracts", "alice_contract.json")
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

# ---------------------------------------------------------------- 新增技能
# 技能名 -> (分类, 类别内序号由脚本自动排)
NEW_SKILLS: dict[str, str] = {
    "re-env-sandbox": "D",        # 隔离环境 / 快照回滚 / 反虚拟机排查
    "re-flow-recon": "D",         # 查壳 / 行为侦察 / 路线决策
    "re-flow-analyze": "D",       # 断点定位 / 数据流追踪 / 补丁回归
    "re-flow-unpack": "D",        # 脱壳 / OEP / IAT 修复
    "re-tool-registry": "D",      # 逆向工具注册表（下载清单）
    "re-tool-downloader": "D",    # 工具下载执行器
    "re-tool-manifest": "D",      # 环境登记簿 / 快照检查
    "windows-license-crack": "D", # 授权/激活逆向 + 运行时绕过
    "re-flow-capture": "B",       # 抓包 / HTTPS 解密 / 协议明文
    "re-flow-orchestrator": "A",  # 完整破解任务总编排状态机
}

# 新增中文路由词（red 表）—— 严格规避 config/system_objects.json 对象词表
NEW_ROUTES: dict[str, list[str]] = {
    # ---- re-env-sandbox ----
    "隔离环境": ["re-env-sandbox"],
    "回滚环境": ["re-env-sandbox"],
    "隔离分析场": ["re-env-sandbox"],
    "隔离分析环境": ["re-env-sandbox"],
    "反虚拟机检测": ["re-env-sandbox"],
    "符号服务器": ["re-env-sandbox"],
    "驱动签名排查": ["re-env-sandbox"],
    "可回滚环境": ["re-env-sandbox"],
    # ---- re-flow-recon ----
    "查壳": ["re-flow-recon"],
    "侦察报告": ["re-flow-recon"],
    "目标画像": ["re-flow-recon"],
    "行为侦察": ["re-flow-recon"],
    "路线决策": ["re-flow-recon"],
    "壳类型": ["re-flow-recon"],
    "架构判断": ["re-flow-recon"],
    # ---- re-flow-analyze ----
    "关键校验函数": ["re-flow-analyze"],
    "断点定位": ["re-flow-analyze"],
    "下断点分析": ["re-flow-analyze"],
    "数据流追踪": ["re-flow-analyze"],
    "调用链回溯": ["re-flow-analyze"],
    "hook还是patch": ["re-flow-analyze"],
    "patch还是hook": ["re-flow-analyze"],
    "回归验证": ["re-flow-analyze"],
    "补丁回归": ["re-flow-analyze"],
    # ---- re-flow-unpack ----
    "脱壳流程": ["re-flow-unpack"],
    "找OEP": ["re-flow-unpack"],
    "修复IAT": ["re-flow-unpack"],
    "dump内存": ["re-flow-unpack"],
    "Scylla导出": ["re-flow-unpack"],
    "反调试对抗": ["re-flow-unpack"],
    # ---- re-flow-capture ----
    "抓包流程": ["re-flow-capture"],
    "HTTPS解密": ["re-flow-capture"],
    "证书校验抓包": ["re-flow-capture"],
    "强制转发": ["re-flow-capture"],
    "协议明文": ["re-flow-capture"],
    "流量取证": ["re-flow-capture"],
    # ---- re-flow-orchestrator ----
    "完整破解": ["re-flow-orchestrator"],
    "破解流程": ["re-flow-orchestrator"],
    "破解任务": ["re-flow-orchestrator"],
    "破解编排": ["re-flow-orchestrator"],
    "逆向总编排": ["re-flow-orchestrator"],
    "破解下一步": ["re-flow-orchestrator"],
    # ---- re-tool-registry ----
    "工具注册表": ["re-tool-registry"],
    "下载清单": ["re-tool-registry"],
    "搭逆向环境": ["re-tool-registry"],
    "逆向工具目录": ["re-tool-registry"],
    "工具源": ["re-tool-registry"],
    # ---- re-tool-downloader ----
    "下载工具": ["re-tool-downloader"],
    "装工具": ["re-tool-downloader"],
    "工具下载": ["re-tool-downloader"],
    "安装逆向工具": ["re-tool-downloader"],
    "获取工具最新版本": ["re-tool-downloader"],
    # ---- re-tool-manifest ----
    "已装工具": ["re-tool-manifest"],
    "环境检查": ["re-tool-manifest"],
    "工具清单": ["re-tool-manifest"],
    "环境快照检查": ["re-tool-manifest"],
    "还缺什么工具": ["re-tool-manifest"],
    "工具登记": ["re-tool-manifest"],
    # ---- windows-license-crack ----
    "卡密": ["windows-license-crack"],
    "注册机": ["windows-license-crack"],
    "授权破解": ["windows-license-crack"],
    "软件破解": ["windows-license-crack"],
    "许可证破解": ["windows-license-crack"],
    "跨机器授权": ["windows-license-crack"],
    "激活失败排查": ["windows-license-crack"],
    "单文件破解": ["windows-license-crack"],
    "NativeAOT逆向": ["windows-license-crack"],
    "MPRESS脱壳": ["windows-license-crack"],
    "运行时绕过": ["windows-license-crack"],
    "动态插桩绕过": ["windows-license-crack"],
}


def load(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default if default is not None else {}


def save(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def read_desc(name: str) -> str:
    p = os.path.join(SKILLS_ROOT, name, "SKILL.md")
    if not os.path.isfile(p):
        return ""
    with open(p, encoding="utf-8", errors="replace") as fh:
        txt = fh.read(4000)
    m = re.search(r"^description:\s*(.*)$", txt, re.M)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")[:120]


def absorb() -> int:
    data = load(DATA_FILE)
    skills = data.get("skills", [])
    have = {s["name"] for s in skills}
    obj_words = {o.lower() for o in load(OBJECTS_FILE).get("objects", [])}

    # ---- ① 技能入库 ----
    added = []
    max_n: dict[str, int] = {}
    for s in skills:
        n = int(re.sub(r"\D", "", s.get("code", "") or 0) or 0)
        max_n[s["category"]] = max(max_n.get(s["category"], 0), n)
    for name, cat in NEW_SKILLS.items():
        if name in have:
            continue
        max_n[cat] = max_n.get(cat, 0) + 1
        skills.append({
            "code": f"{cat}{max_n[cat]}",
            "name": name,
            "category": cat,
            "desc": read_desc(name),
            "rel": name,
            "builtin": False,
        })
        added.append((f"{cat}{max_n[cat]}", name))
    skills.sort(key=lambda x: (x["category"], int(re.sub(r"\D", "", x["code"]) or 0)))
    data["skills"] = skills
    save(DATA_FILE, data)
    print(f"[OK] 技能入库: 新增 {len(added)} | 总数 {len(skills)}")
    for code, name in added:
        print(f"     + {code} {name}")

    # ---- ② 中文路由词合并 ----
    al = load(ALIAS_FILE)
    red = al.setdefault("red", {})
    conflicts = [w for w in NEW_ROUTES if w.lower() in obj_words]
    if conflicts:
        print(f"[!] 与授权对象词表冲突，已跳过: {conflicts}")
    n_add, n_merge = 0, 0
    for word, targets in NEW_ROUTES.items():
        if word.lower() in obj_words:
            continue
        if word in red:
            new = list(dict.fromkeys(list(red[word]) + targets))
            if new != red[word]:
                red[word] = new
                n_merge += 1
        else:
            red[word] = list(targets)
            n_add += 1
    # 既有词补挂新技能（合并，不夺权）
    for word, targets in {"反虚拟机": ["re-env-sandbox"], "脱壳": ["re-flow-unpack"],
                          "keygen": ["windows-license-crack"]}.items():
        if word in red:
            new = list(dict.fromkeys(list(red[word]) + targets))
            if new != red[word]:
                red[word] = new
                n_merge += 1
    save(ALIAS_FILE, al)
    print(f"[OK] 路由词合并: 新增 {n_add} 合并 {n_merge} | red 总数 {len(red)}")

    # ---- ③ 契约同步 ----
    c = load(CONTRACT_FILE)
    c.setdefault("domains", {})["skills"] = len(skills)
    c["domains"]["note"] = f"A-N 14 大分类，全量技能 {len(skills)}"
    save(CONTRACT_FILE, c)
    print(f"[OK] 契约同步: domains.skills = {len(skills)}")
    return 0


def check() -> int:
    data = load(DATA_FILE)
    al = load(ALIAS_FILE)
    names = {s["name"] for s in data.get("skills", [])}
    red = al.get("red", {})
    bad = []
    for name in NEW_SKILLS:
        if name not in names:
            bad.append(f"技能未入库: {name}")
    for word, targets in NEW_ROUTES.items():
        for t in targets:
            if t not in names:
                bad.append(f"路由词 {word} 指向不存在的技能 {t}")
            elif word not in red or t not in red[word]:
                bad.append(f"路由词未生效: {word} -> {t}")
    if bad:
        for b in bad:
            print("  [✗] " + b)
        return 1
    print("[✓] 吸收状态校验通过：10 技能全部入库，路由词全部生效")
    print(f"    技能总数 {len(names)} | red 路由词 {len(red)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="吸收 re-skill-suite 进Alice")
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    return check() if a.check else absorb()


if __name__ == "__main__":
    raise SystemExit(main())
