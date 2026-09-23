# 竞赛云与平台链

**读取条件**：云元数据、容器、Kubernetes、内核、Linux/Windows 横向与平台攻击链案例。

本索引包含 6 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `competition-agent-cloud` 【6/10】 — CTF 沙箱子流：AI agent 提示注入、MCP 工具链、云容器 CI/CD 与供应链投毒类赛题
- `competition-cloud-metadata-path` 【6/10】 — CTF 沙箱子流：云 metadata 服务、实例身份与 link-local 凭据到提权的信任链
- `competition-container-runtime` 【6/10】 — CTF 沙箱子流：容器运行时分析、挂载密钥、sidecar 与入口漂移排查
- `competition-k8s-control-plane` 【6/10】 — CTF 沙箱子流：K8s API 权限、SA 信任、RBAC 边界与 admission 行为分析
- `competition-kernel-container-escape` 【6/10】 — CTF 沙箱子流：内核攻击面、namespace/cgroup 边界与容器逃逸原语验证
- `competition-windows-pivot` 【6/10】 — CTF 沙箱子流：Kerberos/WinRM/SMB/RDP 凭据重放与主机间横向

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
