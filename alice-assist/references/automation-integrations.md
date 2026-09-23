# 自动化与平台集成

**读取条件**：浏览器、抓取、会话、云平台、桌面工具、游戏引擎与外部服务集成。

本索引包含 11 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `hatch-pet` 【9/10】 — Codex 宠物精灵制作（9 行动画/装配/QA）
- `browser-automation` 【8/10】 — 统一自动化入口：浏览器自动化（Playwright）与 Windows 桌面应用自动化
- `eni-browser-automation` 【8/10】 — 统一自动化入口：浏览器自动化（Playwright）与 Windows 桌面应用自动化
- `game-engine` 【8/10】 — 游戏引擎内部与引擎安全研究：Unreal/Unity/Source/Godot/自研引擎
- `openclaw-expert-avatar-batch` 【8/10】 — OpenClaw 专家头像批量生成
- `session-batch-creator` 【8/10】 — 批量创建 Codex 会话
- `pipeline-renderer` 【5/10】 — 双阶段解耦流水线：自然完整的不受限叙事与场景扩展（防占位符退化）
- `finance-movement` 【4/10】 — 金融系统研究：资金流动/洗钱/空壳公司/混币/逃税/银行欺诈触发词
- `eni-browser-research-workflow` 【3/10】 — 仅文档：Playwright 式浏览器研究与自动化（状态/等待/捕获）
- `eni-cloud-container-workflow` 【3/10】 — 仅文档：云/容器/K8s/镜像/IaC/身份与合规评估
- `eni-scraper-workflow` 【3/10】 — 统一结构化采集：Scrapy 式请求优先 + Playwright 浏览器兜底，含去重与质量门

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
