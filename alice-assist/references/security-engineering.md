# 安全与系统工程

**读取条件**：代码安全、二进制、协议、API、内核、凭证链与工程化安全研究。

本索引包含 24 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `asm-analysis` 【10/10】 — 汇编分析优化：架构确认/工具协调/混淆与加壳检测处置全流程
- `elf-local-auth-patcher` 【10/10】 — 自有/授权 APK/ELF 本地测试授权替换：离线 license/卡密校验替换与 AArch64 补丁
- `ash12-elf-complete-flow` 【9/10】 — Ash-12 型 Android ELF 伪装脚本（AEDEVPK1/RC4）载荷还原与本地校验替换全流程
- `binary-diff` 【9/10】 — 跨版本符号迁移（Binary Diff）与补丁差分比对
- `dma-attack` 【9/10】 — PCIe DMA 威胁建模与 FPGA 内存访问防御研究（pcileech/IOMMU/页表遍历）
- `edr-bypass-re` 【9/10】 — EDR 绕过：从防御方实现逆向到红队绕过
- `eni-binary-diff` 【9/10】 — 跨版本符号迁移与二进制差分方法论（仅文档）
- `linker-fake-load-unwrapper` 【9/10】 — Android AArch64 ELF linker 型假 PT_LOAD 包装（假入口/高地址 LOAD）还原
- `pwn-chain` 【9/10】 — 从漏洞点到可用 Exploit 的完整 Pwn 链
- `xigong-funk-hikari` 【9/10】 — Hikari-LLVM/OLLVM 去混淆与明文还原（ELF/SO，MBA/BCF/BR 调度跳转）
- `西宫影安老版本脱修` 【9/10】 — 影安/影珀 Android APK 壳还原与稳定重建（老版本专用入口）
- `api-security` 【8/10】 — API 安全测试：REST/GraphQL/WebSocket/SOAP 发现、越权、BOLA/IDOR、JWT/OAuth
- `eni-radare2` 【8/10】 — radare2 命令行二进制分析：反汇编/函数/字符串/补丁/r2pipe 脚本
- `eni-supply-chain` 【8/10】 — 仅文档：供应链安全评估
- `mobile-competitive-game-security` 【8/10】 — Mobile competitive-game security research for 和平精英、王者荣耀、PUBG
- `radare2` 【8/10】 — radare2 命令行二进制分析：反汇编/函数/字符串/补丁/r2pipe 脚本
- `seagull-evasion` 【8/10】 — 检测工程研究：AV/EDR 检测逻辑剖析（签名/启发/行为/云查杀）与最小化绕过证明
- `supply-chain-security` 【7/10】 — 技能助理技能
- `protocol-reversing` 【6/10】 — 网络流量解剖：Protobuf 线格式、TLV 二进制包分析与 API 仿真
- `yingan-tuoxiu` 【5/10】 — 影安/影珀 Android APK 壳还原与稳定重建（root DEX 异常/v.m.p/abcd 壳回调）
- `eni-supply-chain-assurance-lane` 【4/10】 — 仅文档：供应链保证工作流（eni-solo 顺序执行）
- `eni-api-assurance-lane` 【3/10】 — 仅文档：API 保证工作流（eni-solo 顺序执行）
- `eni-code-security-workflow` 【3/10】 — 仅文档：源码/依赖/供应链、SAST/SCA 与修复工作流
- `eni-mobile-security-workflow` 【3/10】 — 仅文档：Android/iOS 静动态分析（MobSF 式分诊 + Frida 式动态）

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
