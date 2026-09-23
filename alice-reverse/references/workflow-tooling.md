# 综合流程与工具

**读取条件**：任务编排、工具准备、环境隔离、IDA/Ghidra RPC、研究严谨性与综合逆向方法。

本索引包含 25 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `ghidra-rpc` 【10/10】 — Ghidra RPC 远程逆向自动化
- `diagram-generator` 【9/10】 — 从自然语言/代码/schema 生成、校验并渲染流程图等图表
- `eni-ida-reverse` 【9/10】 — IDA Pro 逆向分析
- `eni-reverse-ref` 【9/10】 — 仅文档：逆向工程参考（Reverse Engineering）
- `ida-reverse` 【9/10】 — IDA Pro 逆向分析：含已知问题与反思清单
- `eni-blackbox-reverse-boost` 【8/10】 — 离线黑盒逆向与本地 Windows 二进制安全审计增强（寒霜触发）
- `eni-diagram` 【8/10】 — 从自然语言/代码/schema 生成、校验并渲染图表
- `re-env-sandbox` 【8/10】 — 逆向隔离环境（虚拟机/快照/断网）
- `re-flow-analyze` 【8/10】 — 关键函数定位与断点追踪
- `re-flow-orchestrator` 【8/10】 — 完整破解总编排（INIT→DONE 状态机）
- `re-flow-recon` 【8/10】 — 静态查壳与行为侦察
- `re-tool-downloader` 【8/10】 — 逆向工具下载执行器
- `re-tool-registry` 【8/10】 — 工具下载清单生成
- `seagull-reverse` 【8/10】 — 深度逆向：PE/ELF/Mach-O/固件/驱动/APK/.NET/Go/Rust/IL2CPP/加壳二进制/自定义 VM
- `eni-reverselab-bridge` 【7/10】 — 原创外部依赖桥接：把 Open ReverseLab（LING71671/open-reverselab，GPL-3.0
- `eni-reverselab-platform` 【7/10】 — 开源逆向实验台：197 篇知识库 + 43 个 MCP 工具 + 攻击网络图路由
- `re-tool-manifest` 【7/10】 — 工具环境登记簿（MANIFEST）
- `reverse-engineering-tools` 【7/10】 — 受保护游戏逆向工具指南
- `eni-reverse-deep` 【6/10】 — 深度逆向：PE/ELF/Mach-O/固件/驱动/APK/.NET/Go/Rust/IL2CPP/加壳二进制
- `overview` 【6/10】 — 总览与方法论索引
- `research-rigor` 【6/10】 — 研究严谨性（证据/引用/复现）
- `eni-reverse-workflow` 【5/10】 — 深度证据驱动逆向工作流：PE/ELF/Mach-O/固件/驱动/字节码/协议
- `full-reverse` 【3/10】 — 完整逆向链
- `reverse-engineering` 【3/10】 — 逆向工程总纲（脱壳/字符串/控制流）
- `file-backup` 【2/10】 — 修改前备份（.bak/快照）

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
