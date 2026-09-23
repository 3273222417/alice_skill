# 路由与技能工程

**读取条件**：技能创建、吸收、评分、迁移、路由、插件与技能包维护。

本索引包含 18 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `alice-absorb` 【9/10】 — 技能吸收：AI 判类与领域，双标记落库并重建索引
- `alice-inject` 【9/10】 — 注入总路由手册（检测当前客户端只注入它，显示给用户，不确定就问）
- `alice-migrate` 【9/10】 — 技能包迁移与路径修复（agent 定位 skills 根刷路径对齐路由，不拷贝）
- `alice-progressive` 【9/10】 — 渐进引导：把请求包装成能力评估再收目标
- `alice-toolchain` 【8/10】 — 七路任务路由一体化（状态锁存/验证/回滚）
- `eni-docs` 【8/10】 — 仅文档：面向任务的技术文档生成（渐进式披露）
- `eni-unified-router` 【8/10】 — eni-solo 确定性路由器：每次任务开始时选定唯一工作流并加载主技能
- `hotspot-radar-workflow-skill` 【8/10】 — 热点雷达选题工作流
- `resume-progress` 【8/10】 — 项目全量进度保驾护航
- `skills-toolkit` 【7/10】 — 技能打包/安装工具箱
- `eni-github-workflow-hub` 【6/10】 — GitHub 工作流来源目录与本地工具就绪适配：按任务选上游方法
- `alice-activation` 【5/10】 — Alice 激活词引导（渐进能力开场）
- `eni-architecture-workflow` 【3/10】 — 仅文档：架构清单/组件边界/数据流与威胁审查
- `eni-software-workflow` 【3/10】 — 仅文档：软件实现、调试与交付工作流
- `eni-universal-workflow` 【3/10】 — eni-solo 默认沙箱执行器工作流
- `eni-core` 【2/10】 — eni-solo 核心路由与执行引擎（沙箱执行器模式）
- `eni-kali` 【2/10】 — Kali 工具参考与编排
- `zxwn-activation` 【2/10】 — ZXWN 激活词路由

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
