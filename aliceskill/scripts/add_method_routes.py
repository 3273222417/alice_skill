#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将方法论 A 类 28 技能的中文路由词并入 config/command_aliases.json 的 red 表。
用法: python add_method_routes.py
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

NEW_RED = {
    "方法论": ["writing-plans", "systematic-debugging", "test-driven-development", "brainstorming", "domain-modeling"],
    "系统化调试": ["systematic-debugging"],
    "调试方法论": ["systematic-debugging"],
    "按流程调试": ["systematic-debugging"],
    "测试驱动": ["test-driven-development"],
    "测试驱动开发": ["test-driven-development"],
    "头脑风暴": ["brainstorming"],
    "创意风暴": ["brainstorming"],
    "领域建模": ["domain-modeling"],
    "建模": ["domain-modeling"],
    "计划编写": ["writing-plans"],
    "写计划": ["writing-plans"],
    "计划执行": ["executing-plans"],
    "执行计划": ["executing-plans"],
    "完成前验证": ["verification-before-completion"],
    "交付验证": ["verification-before-completion"],
    "威胁建模": ["threat-modeling"],
    "风险评估": ["threat-modeling"],
    "stide建模": ["threat-modeling"],
    "方案拷问": ["grilling"],
    "拷问方案": ["grilling"],
    "压力测试方案": ["grilling"],
    "拷问": ["grill-me", "grilling"],
    "拷问我": ["grill-me"],
    "带文档拷问": ["grill-with-docs"],
    "批量拷问": ["batch-grill-me"],
    "并行调度": ["dispatching-parallel-agents"],
    "并行智能体": ["dispatching-parallel-agents"],
    "多代理并行": ["dispatching-parallel-agents"],
    "子代理开发": ["subagent-driven-development"],
    "子代理驱动": ["subagent-driven-development"],
    "评审代理": ["review-agent"],
    "代码评审": ["requesting-code-review", "review-agent"],
    "请求评审": ["requesting-code-review"],
    "接收评审": ["receiving-code-review"],
    "开发收尾": ["finishing-a-development-branch"],
    "分支收尾": ["finishing-a-development-branch"],
    "git工作树": ["using-git-worktrees"],
    "工作树": ["using-git-worktrees"],
    "技能编写": ["writing-skills"],
    "写技能": ["writing-skills"],
    "ctf总入口": ["ctf-sandbox-orchestrator"],
    "比赛总入口": ["ctf-sandbox-orchestrator"],
    "全流程": ["reverse-flow"],
    "逆向全流程": ["reverse-flow"],
        "报告生成": ["docs-generator"],
    "写报告": ["docs-generator"],
    "图示生成": ["diagram-generator"],
    "画图": ["diagram-generator"],
    "超级能力": ["using-superpowers"],
    "superpowers": ["using-superpowers"],
    "专家分身": ["openclaw-expert-avatar-batch"],
}


def main() -> int:
    with open(ALIAS_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    red = data.setdefault("red", {})
    added, merged = 0, 0
    for word, targets in NEW_RED.items():
        if word in red:
            old = red[word]
            new = list(dict.fromkeys(old + targets))
            if new != old:
                red[word] = new
                merged += 1
        else:
            red[word] = list(targets)
            added += 1
    with open(ALIAS_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print(f"[OK] 方法论路由词: 新增 {added} 合并 {merged} | red 总数 {len(red)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
