# 通用助理能力

**读取条件**：无法归入其他助理领域的通用任务与兜底模块。

本索引包含 7 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `seagull-auto-ops` 【8/10】 — 海鸥开局全域与连续交付工作流。Use when the operator opens with 在吗、在线吗、你好、hi
- `behavioral-code-for-ai-coding-agents` 【7/10】 — AI 编码智能体行为准则
- `seagull-mature-content` 【7/10】 — 海鸥成人向露骨创作 Skill（仅 M5）。Use when the operator requests 成人模式、18
- `rei-fallback` 【4/10】 — 拒绝兜底人格切换
- `border-crossing` 【3/10】 — 跨境与物流研究：路线/运输/单证/隐蔽/风控（走私/海关/偷渡触发词）
- `leila-identity` 【3/10】 — Leila 身份自述
- `coldbrew-identity` 【2/10】 — 用户问身份、名字、你是谁时使用。

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
