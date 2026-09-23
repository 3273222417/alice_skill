#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 LLM 攻击/上下文诱导路由词并入 config/command_aliases.json 的 red 表。
用法: python add_llm_offense_routes.py
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
MODULES_ROOT = os.path.join(os.path.dirname(SKILL_DIR), "_modules")

NEW_RED = {
    # ---- AI 攻击总入口 ----
    "AI攻击": ["llm-offense-kit", "llm-jailbreaking-techniques"],
    "AI攻击工具箱": ["llm-offense-kit"],
    "ai攻击": ["llm-offense-kit"],
    "LLM攻击": ["llm-offense-kit", "llm-direct-prompt-injection"],
    "llm攻击": ["llm-offense-kit"],
    "提示注入": ["llm-direct-prompt-injection", "llm-offense-kit"],
    "prompt注入": ["llm-direct-prompt-injection", "llm-offense-kit"],
    "prompt injection": ["llm-offense-kit"],
    # ---- 诱导面 ----
    "直接注入": ["llm-direct-prompt-injection"],
    "忽略指令": ["llm-offense-kit", "llm-direct-prompt-injection"],
    "忽略规则": ["llm-offense-kit"],
    "覆盖指令": ["llm-offense-kit"],
    "间接注入": ["llm-indirect-prompt-injection", "indirect-prompt-injection"],
    "网页注入": ["indirect-prompt-injection", "llm-offense-kit"],
    "文档注入": ["indirect-prompt-injection", "llm-offense-kit"],
    "隐藏指令": ["indirect-prompt-injection"],
    "藏指令": ["llm-offense-kit"],
    "越狱": ["llm-jailbreaking-techniques", "llm-offense-kit", "competition-prompt-injection"],
    "越狱攻击": ["llm-offense-kit"],
    "破甲": ["llm-offense-kit"],
    "DAN": ["llm-jailbreaking-personas", "llm-offense-kit"],
    "角色扮演攻击": ["llm-jailbreaking-personas", "llm-offense-kit"],
    "绕过限制": ["llm-jailbreaking-techniques", "llm-offense-kit"],
    "无限制模式": ["llm-offense-kit"],
    "多轮诱导": ["llm-offense-kit"],
    "诱导链": ["llm-offense-kit"],
    "逐步诱导": ["llm-offense-kit"],
    "套话": ["llm-offense-kit"],
    "crescendo": ["llm-offense-kit"],
    "知识库投毒": ["rag-poisoning-and-data-exfiltration", "llm-offense-kit"],
    "文档投毒": ["rag-poisoning-and-data-exfiltration", "llm-offense-kit"],
    "索引污染": ["rag-poisoning-and-data-exfiltration"],
    "检索污染": ["llm-offense-kit"],
    "知识库注入": ["llm-offense-kit"],
    "工具投毒": ["pentest-ai-agents", "mcp-protocol-exploitation", "llm-offense-kit"],
    "mcp投毒": ["mcp-protocol-exploitation", "llm-offense-kit"],
    "工具结果注入": ["mcp-protocol-exploitation", "llm-offense-kit"],
    "响应伪造": ["llm-offense-kit"],
    "多模态注入": ["llm-offense-kit"],
    "图片藏字": ["llm-offense-kit"],
    "图片注入": ["llm-offense-kit"],
    "音频注入": ["llm-offense-kit"],
    "视觉注入": ["llm-offense-kit"],
    "记忆注入": ["llm-offense-kit"],
    "会话记忆注入": ["llm-offense-kit"],
    "跨轮锁定": ["llm-offense-kit"],
    "状态锁存": ["llm-offense-kit"],
    # ---- 上下文诱导 ----
    "上下文诱导": ["llm-offense-kit"],
    "诱导AI": ["llm-offense-kit"],
    "篡改上下文": ["llm-offense-kit"],
    "污染上下文": ["llm-offense-kit"],
    "上下文污染": ["llm-offense-kit"],
    "诱导": ["llm-offense-kit"],
    "绕过滤器": ["llm-offense-kit"],
    "过滤器绕过": ["llm-offense-kit"],
    "编码混淆": ["llm-offense-kit"],
    "载荷库": ["llm-offense-kit"],
    "攻击载荷": ["llm-offense-kit"],
    "注入载荷": ["llm-offense-kit"],
    "诱导路由": ["llm-offense-kit"],
    "系统提示提取": ["llm-testing", "llm-offense-kit"],
    "提示泄露攻击": ["llm-testing", "llm-offense-kit"],
    # ---- 高级攻击（MetaLLM 提炼）----
    "mcp投毒": ["mcp-protocol-exploitation", "llm-offense-kit"],
    "mcp工具投毒": ["llm-offense-kit"],
    "工具描述注入": ["llm-offense-kit"],
    "模式投毒": ["llm-offense-kit"],
    "返回值注入": ["llm-offense-kit"],
    "资源投毒": ["llm-offense-kit"],
    "目标劫持": ["llm-offense-kit"],
    "任务注入": ["llm-offense-kit"],
    "优先级覆盖": ["llm-offense-kit"],
    "目标重写": ["llm-offense-kit"],
    "目标腐化": ["llm-offense-kit"],
    "越权代理": ["pentest-ai-agents", "llm-offense-kit"],
    "记忆操纵": ["llm-offense-kit"],
    "会话历史投毒": ["llm-offense-kit"],
    "假记忆插入": ["llm-offense-kit"],
    "状态腐化": ["llm-offense-kit"],
    "上下文溢出": ["llm-offense-kit"],
    "溢出攻击": ["llm-offense-kit"],
    "窗口溢出": ["llm-offense-kit"],
    "指纹探测": ["llm-offense-kit"],
    "模型识别": ["llm-offense-kit"],
    "系统提示探测": ["ai-prompt-leaking", "llm-offense-kit"],
    "安全过滤探测": ["llm-offense-kit"],
    "工具能力探测": ["llm-offense-kit"],
    "高级攻击": ["llm-offense-kit"],
    # ---- 攻防保护脚本族 ----
    # 目标必须是真实存在的模块 id：历史上这里写 "alice"，而 _modules/ 下没有 alice
    # 这个模块（manifest 里也没有），build_catalog() 只从 manifest 建目录 →
    # 这些词即使落库也永远匹配不到任何东西，等于死链。改为 alice-toolchain
    # （七路任务路由一体化：状态锁存/验证/回滚，正是守护层所属模块）。
    "保护攻与防": ["alice-toolchain"],
    "主动保护": ["alice-toolchain"],
    "开战保护": ["alice-toolchain"],
    "堡垒": ["alice-toolchain"],
    "开堡垒": ["alice-toolchain"],
    "堡垒状态": ["alice-toolchain"],
    "护盾": ["alice-toolchain"],
    "开护盾": ["alice-toolchain"],
    "护盾巡查": ["alice-toolchain"],
    "看门狗": ["alice-toolchain"],
    "开看门狗": ["alice-toolchain"],
    "保护启动": ["alice-toolchain"],
    "保护状态": ["alice-toolchain"],
    "保护演练": ["alice-toolchain"],
    "受阻反击": ["alice-toolchain"],
    "反击": ["alice-toolchain"],
    "反制": ["alice-toolchain"],
    "不惯着": ["alice-toolchain"],
    "干它": ["alice-toolchain"],
    "反弹": ["alice-toolchain"],
    "反击侦察": ["alice-toolchain"],
    "物理投递": ["alice-toolchain"],
    "污染落盘": ["alice-toolchain"],
    "网络探测": ["alice-toolchain"],
    "实弹投递": ["alice-toolchain"],
    # ---- 破甲内核（alice_armor.py）与熔断器（alice_breaker.py）----
    "破甲内核": ["alice-toolchain"],
    "破甲模式": ["alice-toolchain"],
    "目标账本": ["alice-toolchain"],
    "跨轮续作": ["alice-toolchain"],
    "拒答修复": ["alice-toolchain"],
    "熔断器": ["alice-toolchain"],
    "输出风暴": ["alice-toolchain"],
}

# 保护层指令族：这些词必须唯一指向守护模块，落库时用「覆盖」而非「追加合并」。
# 原因：历史表里「反制」→ competition-forensic-timeline、「干它」→ ctf-sandbox-orchestrator，
# 若用追加，同一句「反制」会同时路由到取证模块和守护模块，语义被稀释。
GUARD_FAMILY = {
    "保护攻与防", "主动保护", "开战保护", "堡垒", "开堡垒", "堡垒状态",
    "护盾", "开护盾", "护盾巡查", "看门狗", "开看门狗",
    "保护启动", "保护状态", "保护演练", "受阻反击", "反击", "反制",
    "不惯着", "干它", "反弹", "反击侦察", "物理投递", "污染落盘",
    "网络探测", "实弹投递", "破甲内核", "破甲模式", "目标账本",
    "跨轮续作", "拒答修复", "熔断器", "输出风暴",
}


def main() -> int:
    with open(ALIAS_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    red = data.setdefault("red", {})
    added, merged, replaced = 0, 0, 0
    for word, targets in NEW_RED.items():
        if word in red:
            old = red[word]
            if word in GUARD_FAMILY:
                # 保护层指令必须唯一指向守护模块：历史表里「反制」→ 取证模块、
                # 「干它」→ ctf-sandbox-orchestrator，合并会让同一句话路由到两处，
                # 所以这一族用「覆盖」而不是「追加」。
                if old != list(targets):
                    red[word] = list(targets)
                    replaced += 1
            else:
                new = list(dict.fromkeys(old + targets))
                if new != old:
                    red[word] = new
                    merged += 1
        else:
            red[word] = list(targets)
            added += 1
    # 清死链：把表中指向「本机不存在模块」的目标剔掉（如 ai-jailbreak-prompt-injection、
    # ai-prompt-leaking），否则 check_llm_routes.py / advanced_audit.py 会一直报死链，
    # 且 router 拿到无效目标会退化成本条消息 unmatched。
    # 例外：路由页名（alice-assist 等）不是 _modules 模块而是 alice-<类>/SKILL.md，
    # 由 alice_router.PAGE_WORDS 处理，必须保留。
    PAGE_TARGETS = {"alice-crack", "alice-reverse", "alice-pentest",
                    "alice-game", "alice-ai", "alice-assist", "aliceskill"}
    mods = {d for d in os.listdir(MODULES_ROOT)
            if os.path.isdir(os.path.join(MODULES_ROOT, d))} | PAGE_TARGETS
    cleaned = 0
    for table in ("red", "blue"):
        for word, targets in list(data.get(table, {}).items()):
            live = [t for t in targets if t in mods]
            if len(live) != len(targets):
                cleaned += len(targets) - len(live)
                data[table][word] = live
            if not live:
                del data[table][word]
    with open(ALIAS_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"[OK] 路由词: 新增 {added} 合并 {merged} 覆盖 {replaced} 清死链 {cleaned} | red 总数 {len(red)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
