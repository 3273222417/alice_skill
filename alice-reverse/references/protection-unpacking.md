# 保护、混淆与脱壳

**读取条件**：加壳、OEP/IAT、OLLVM、虚拟化保护、反调试、自修改代码与运行时重建。

本索引包含 20 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `dsl-vm-reverse` 【9/10】 — 自定义 JS/WASM DSL 虚拟机逆向：还原操作码、状态转移与运行时行为
- `eni-unpack-reverse-lab` 【8/10】 — 离线 Windows PE 加壳/脱壳分诊与证据驱动逆向（寒霜触发）
- `re-flow-unpack` 【7/10】 — 脱壳（OEP/Scylla dump/IAT 修复）
- `anti-debug` 【6/10】 — 反调试检测与绕过（ptrace/时序/断点）
- `binary-protect-bypass` 【6/10】 — 加壳保护绕过（脱壳/去混淆/校验绕过）
- `code-obfuscate` 【6/10】 — 代码混淆与还原（控制流/字符串加密）
- `hidden-rx-memory-reconstruction` 【6/10】 — 隐藏 RX 内存运行时重建
- `memory-breakpoint-tracing` 【5/10】 — 内存断点追踪工作流
- `native-unpacking` 【5/10】 — 原生脱壳工作流
- `obfuscator-io-analysis` 【5/10】 — obfuscator.io 混淆还原
- `ollvm-deobfuscation` 【5/10】 — OLLVM 混淆还原工作流
- `ollvm-recovery-workflow` 【5/10】 — OLLVM 恢复工作流
- `packed-so-elf-rebuild` 【5/10】 — 加壳 SO/ELF 运行时重建
- `packer-and-loader-analysis` 【5/10】 — 加壳器与加载器分析
- `self-modifying-code` 【5/10】 — 自修改代码工作流
- `virtualization-protection` 【5/10】 — 虚拟化保护（VMP）工作流
- `iat-rebuild` 【4/10】 — 导入表重建与修复
- `memory-breakpoint` 【4/10】 — 内存断点定位 OEP
- `esp-law` 【3/10】 — ESP 定位原始入口点（pushad/popad）
- `full-unpack` 【3/10】 — 完整脱壳链

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
