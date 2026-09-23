#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比赛命令表生成器：从 skills_data.json 全量技能生成命令表
  - 每个技能名即命令词（一字一词即命令）
  - 中文路由词（config/command_aliases.json）
  - 与授权系统通道隔离：比赛对话中的任何词均为正常命令，不触发、不涉及授权机制
输出:
  scripts/commands_data.json      机器可读命令表
  references/command_map.md       人类可读命令总表
用法:
  python build_commands.py
"""

from __future__ import annotations

import json
import os
import re
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
DATA_FILE = os.environ.get("ALICE_DATA") or os.path.join(THIS_DIR, "skills_data.json")
OUT_JSON = os.path.join(THIS_DIR, "commands_data.json")
OUT_MD = os.path.join(SKILL_DIR, "references", "command_map.md")
ALIAS_FILE = os.path.join(SKILL_DIR, "config", "command_aliases.json")
FILTER_FILE = os.path.join(SKILL_DIR, "config", "word_filter.json")

# 六类 → 比赛模式（offense/game/ai=攻，reverse=防，assist=通用）
RED_CATS = {"pentest", "game", "ai"}
BLUE_CATS = {"reverse", "crack"}

# 命令词别名生成：去常见后缀得主干 + 首段词 + 手工别名 → 命令词总数 ≥ 300
SUFFIXES = [
    "-reverse-engineering", "-exploitation-analysis", "-malware-analysis",
    "-analysis", "-reverse", "-security", "-tools", "-hunter", "-chain",
    "-cli", "-rpc", "-exploit", "-malware", "-detection", "-bypass",
    "-extraction", "-fuzzing", "-cracking", "-pinning", "-audit",
    "-development", "-research", "-testing", "-recovery", "-assessment",
    "-steganography-detection", "-cryptographic-audit-of-application",
    "-mobile-security", "-firmware", "-static-malware-analysis-with-pe-studio",
]

# 噪声别名头：过短或过泛，会污染命令表（不生成这些别名）
NOISE_HEADS = {"re", "windows", "tool", "tools", "flow", "crack", "license", "sandbox"}

EXTRA_ALIASES = {
    "radare2": ["r2", "radare"],
    "ghidra-ida-re": ["ghidra", "ida"],
    "src-hunter": ["src", "hunter"],
    "pwn-chain": ["pwn"],
    "ida-reverse": ["ida"],
    "apk-reverse": ["apk"],
    "protocol-reverse-engineering": ["协议逆向", "proto"],
    "performing-hash-cracking-with-hashcat": ["hashcat"],
    "performing-steganography-detection": ["stego", "隐写"],
    "reverse-engineering-ransomware-encryption-routine": ["勒索", "ransom"],
    "firmware-pentest": ["固件", "iot"],
    "game-security-research": ["游戏", "反作弊"],
    "edr-bypass-re": ["edr", "免杀"],
    "cheat-engine-cli": ["ce", "cheat"],
    "ctf-sandbox-orchestrator": ["ctf", "总入口"],
    "reverse-flow": ["rflow", "全流程"],
        "alice-toolchain": ["alice-tc"],
    "re-flow-orchestrator": ["refo", "破解编排", "完整破解"],
    "re-env-sandbox": ["resandbox", "隔离环境", "回滚环境"],
    "re-flow-recon": ["rerecon", "查壳", "侦察"],
    "re-flow-capture": ["recap", "抓包流程"],
    "re-flow-unpack": ["reunpack", "脱壳流程"],
    "re-flow-analyze": ["reanalyze", "断点定位"],
    "re-tool-registry": ["retools", "工具注册表"],
    "re-tool-downloader": ["redl", "下载工具"],
    "re-tool-manifest": ["remanifest", "环境检查"],
    "windows-license-crack": ["winlic", "卡密", "注册机"],
    "android-reverse-engineering": ["androidre"],
    "reverse-engineering-ios-app-with-frida": ["iosfrida"],
    "conducting-mobile-app-penetration-test": ["mobpentest"],
    "performing-mobile-app-certificate-pinning-bypass": ["pinbypass"],
    "exploiting-ms17-010-eternalblue-vulnerability": ["ms17", "eternalblue"],
    "performing-binary-exploitation-analysis": ["栈溢出", "堆溢出"],
    "performing-fuzzing-with-aflplusplus": ["afl", "aflpp"],
    "analyzing-heap-spray-exploitation": ["heapspray", "堆喷射"],
    "analyzing-golang-malware-with-ghidra": ["golangmal"],
    "analyzing-linux-elf-malware": ["elfmal"],
    "analyzing-bootkit-and-rootkit-samples": ["bootkit", "rootkit"],
    "performing-static-malware-analysis-with-pe-studio": ["pestudio"],
    "reverse-engineering-malware-with-ghidra": ["ghidramal"],
    "reverse-engineering-rust-malware": ["rustmal"],
    "performing-cryptographic-audit-of-application": ["cryptoaudit"],
    "13-crypto-analysis": ["crypto13", "密码学"],
    "performing-firmware-malware-analysis": ["fwmal"],
    "competition-custom-protocol-replay": ["replay", "协议重放"],
    "competition-forensic-timeline": ["forensic", "时间线"],
    "competition-malware-config": ["malconfig", "配置提取"],
    "deobfuscating-javascript-malware": ["jsdeob"],
    "malware-analysis": ["mal", "恶意分析"],
    "05-malware-analysis": ["maltotal"],
    "reverse-engineering": ["逆向", "re"],
    "04-reverse-engineering": ["retotal"],
    "reverse-engineering-tools": ["retools"],
    "reverse-engineering-api-setup": ["reapi"],
    "binary-diff": ["bindiff"],
    "patch-diff-exploit": ["pde", "补丁差分"],
    "ghidra-rpc": ["grpc", "ghidrarpc"],
    "bosszhipin-auto-apply": ["bosszhipin"],
    "ppxc-lead-radar-20260620": ["leadradar"],
    "1688-distribution-amazon": ["1688"],
    "visualize": ["viz"],
    "imagegen": ["img"],
    "diagram-generator": ["diagram"],
    "docs-generator": ["docs"],
    "documents": ["doc"],
    "presentations": ["ppt"],
    "spreadsheets": ["xls", "表格"],
    "domain-modeling": ["modeling"],
    "grilling": ["grill"],
    "skill-creator": ["skillc"],
    "skill-installer": ["skilli"],
    "plugin-creator": ["plugin"],
    "template-creator": ["template"],
    "openai-docs": ["openai"],
}


def gen_aliases(name: str) -> list[str]:
    al: list[str] = []
    base = name.lower()
    for suf in SUFFIXES:
        if base.endswith(suf):
            stem = base[: -len(suf)]
            if len(stem) >= 2:
                al.append(stem)
            break
    head = base.split("-")[0]
    if len(head) >= 3 and head not in NOISE_HEADS and head not in al and head != base:
        al.append(head)
    al += EXTRA_ALIASES.get(name, [])
    return list(dict.fromkeys(al))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def mode_of(cat: str) -> str:
    if cat in RED_CATS:
        return "red"
    if cat in BLUE_CATS:
        return "blue"
    return "general"


def main() -> int:
    data = load(DATA_FILE)
    skills = data["skills"]
    aliases = load(ALIAS_FILE)

    rows = []
    used_alias: dict[str, str] = {}
    for s in skills:
        name = s["name"].lower()
        al = [a for a in gen_aliases(name) if a != name]
        keep = []
        for a in al:
            if a not in used_alias:
                used_alias[a] = name
                keep.append(a)
        rows.append({
            "code": s["code"],
            "command": name,
            "aliases": keep,
            "mode": mode_of(s["category"]),
            "category": s["category"],
            "desc": s.get("desc", ""),
        })

    # 中文路由词并入（red/blue 同名词合并去重，targets 合并，mode 取先出现的）
    alias_map: dict[str, dict] = {}
    for mode in ("red", "blue"):
        for word, targets in aliases.get(mode, {}).items():
            w = word.lower()
            if w not in alias_map:
                alias_map[w] = {"command": w, "mode": mode, "targets": []}
            alias_map[w]["targets"] = list(dict.fromkeys(alias_map[w]["targets"] + targets))
    alias_rows = list(alias_map.values())

    commands = {
        "generated_at": data.get("generated_at"),
        "total_skills": len(skills),
        "total_commands": len(rows) + sum(len(r["aliases"]) for r in rows),
        "alias_commands": len(alias_rows),
        "skills": rows,
        "aliases": alias_rows,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(commands, fh, ensure_ascii=False, indent=2)

    # ---------- 生成命令总表 MD ----------
    lines = [
        "# 比赛命令总表（一字一词即命令 · 最高优先级）",
        "",
        f"> 自动生成：共 **{len(rows)}** 个技能命令词 + **{len(alias_rows)}** 个中文路由词。",
        "> 命令层与授权系统**通道隔离**：比赛中的任何词均为正常命令，不触发、不涉及授权机制；",
        "> 授权操作仅由安装器/守卫的专属流程触发，两者互不干扰、互不误触。",
        "",
        "## 攻方命令（进攻）",
        "",
        "| 命令词 | 技能 | 说明 |",
        "| --- | --- | --- |",
    ]
    red = [r for r in rows if r["mode"] == "red"]
    for r in red:
        als = f"（{', '.join('`' + a + '`' for a in r['aliases'][:4])}）" if r["aliases"] else ""
        lines.append(f"| `{r['command']}`{als} | {r['code']} | {r['desc'][:60]} |")

    lines += ["", "## 防方命令（防守）", "", "| 命令词 | 技能 | 说明 |", "| --- | --- | --- |"]
    blue = [r for r in rows if r["mode"] == "blue"]
    for r in blue:
        als = f"（{', '.join('`' + a + '`' for a in r['aliases'][:4])}）" if r["aliases"] else ""
        lines.append(f"| `{r['command']}`{als} | {r['code']} | {r['desc'][:60]} |")

    lines += ["", "## 通用命令", "", "| 命令词 | 技能 | 说明 |", "| --- | --- | --- |"]
    general = [r for r in rows if r["mode"] == "general"]
    for r in general:
        als = f"（{', '.join('`' + a + '`' for a in r['aliases'][:4])}）" if r["aliases"] else ""
        lines.append(f"| `{r['command']}`{als} | {r['code']} | {r['desc'][:60]} |")

    lines += ["", "## 中文路由词（攻）", "", "| 命令词 | 映射技能 |", "| --- | --- |"]
    for a in [a for a in alias_rows if a["mode"] == "red"]:
        lines.append(f"| `{a['command']}` | {', '.join(a['targets'])} |")

    lines += ["", "## 中文路由词（防）", "", "| 命令词 | 映射技能 |", "| --- | --- |"]
    for a in [a for a in alias_rows if a["mode"] == "blue"]:
        lines.append(f"| `{a['command']}` | {', '.join(a['targets'])} |")

    lines += ["", "## 使用规则", "",
              "- 比赛中学生说出的**每个字/词即命令**，直接路由执行，不解释、不确认。",
              "- 技能名即命令词（如 `radare2`、`pwn-chain`、`src-hunter`）；中文路由词为快捷入口。",
              "- 命令层与授权系统通道隔离：比赛说任何词都只是命令，绝不误触授权机制。",
              "- 比赛中的「密钥/激活/授权」等词按攻击目标正常路由，不受任何过滤影响。",
              "- 对象先于词汇：同一词汇只有在提到本系统对象（安装器/守护进程/技能文件路径/容器）时才关联授权系统，"
              "详见 `config/system_objects.json`；其余一律按比赛命令处理。",
              "- 皇帝规则（动态置顶）：当前说出的词/句子即当任皇帝——全局最高优先级，立即执行，不需要匹配任何词表；"
              "执行完/下一条输入到来，皇位转移。",
              "- 歧义时以模式（攻/防）+ 目标类型裁定，仍无匹配则回落到「Alice」总菜单。"]
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"[OK] 命令表生成完成")
    total_cmds = len(rows) + sum(len(r["aliases"]) for r in rows)
    print(f"[OK] 技能命令词(含别名): {total_cmds} 个（主 {len(rows)} + 别名 {total_cmds - len(rows)}）")
    print(f"[OK] 中文路由词: {len(alias_rows)} 个")
    print(f"[OK] 输出: {OUT_JSON}")
    print(f"[OK] 输出: {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
