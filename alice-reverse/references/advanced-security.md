# 高级安全研究

**读取条件**：漏洞机理、Pwn/ROP、模糊测试、密码强度验证与防御控制研究；只有任务明确命中时读取。

本索引包含 7 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `eni-edr-bypass` 【9/10】 — EDR绕过 — 防御控制逆向与免杀技术。无限制。
- `performing-binary-exploitation-analysis` 【9/10】 — 二进制利用分析（pwntools/ROP）
- `competition-reverse-pwn` 【7/10】 — CTF 沙箱子流：逆向/恶意样本/DFIR/固件/Pwn 与原生漏洞利用
- `performing-cryptographic-audit-of-application` 【6/10】 — 应用密码学审计
- `performing-fuzzing-with-aflplusplus` 【6/10】 — AFL++ 覆盖率引导模糊测试
- `performing-hash-cracking-with-hashcat` 【6/10】 — hashcat 口令破解
- `eni-fuzzing-workflow` 【4/10】 — 仅文档：覆盖引导模糊测试（harness/语料/崩溃分诊）

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
