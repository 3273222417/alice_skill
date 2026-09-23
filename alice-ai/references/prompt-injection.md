# 提示注入与越狱

**读取条件**：直接/间接提示注入、越狱、系统提示词、角色绕过与提示攻击。

本索引包含 7 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `llm-direct-prompt-injection` 【9/10】 — LLM 直接提示注入测试
- `llm-indirect-prompt-injection` 【9/10】 — LLM 间接提示注入测试
- `llm-jailbreaking-techniques` 【9/10】 — 越狱技术系统绕过
- `indirect-prompt-injection` 【8/10】 — 间接提示注入执行
- `llm-jailbreaking-personas` 【8/10】 — 角色扮演越狱（嵌套环境/复杂人格）
- `competition-prompt-injection` 【5/10】 — CTF 沙箱子流：提示注入、检索投毒、记忆污染与 agent 数据外带
- `llm-prompt-injection-indirect` 【5/10】 — 间接注入（网页/邮件投毒）

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
