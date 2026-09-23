# 固件、内核与驱动

**读取条件**：固件镜像、分区/启动链、Binwalk、Windows/Linux/macOS 内核与驱动。

本索引包含 7 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `performing-firmware-extraction-with-binwalk` 【9/10】 — 固件提取（binwalk）
- `windows-kernel` 【8/10】 — Windows 内核安全与保护机制
- `competition-firmware-layout` 【7/10】 — CTF 沙箱子流：固件镜像分区表/启动链/升级包与设备信任边界分析
- `kernel-driver-analysis` 【5/10】 — 内核驱动分析工作流
- `linux-kernel-reversing` 【5/10】 — Linux 内核逆向工作流
- `macos-kernel-reversing` 【5/10】 — macOS 内核逆向工作流
- `eni-firmware-workflow` 【4/10】 — 仅文档：固件/IoT 提取、文件系统、仿真与验证

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
