# 运行时观测与补丁

**读取条件**：Hook、断点、Frida 追踪、参数观测、字节补丁、跳转修改与系统调用关联。

本索引包含 15 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `dynamic-instrumentation` 【6/10】 — Frida 动态 Hook、内存补丁、API 参数追踪与反调试绕过脚本生成
- `hardware-breakpoint-observation` 【6/10】 — 硬件断点观察工作流
- `native-api-hooking` 【5/10】 — 原生 API 钩取工作流
- `stealth-hook-methodology` 【5/10】 — 低噪声观察方法论（反 Hook 对抗）
- `syscall-ebpf-frida-correlation` 【5/10】 — syscall/eBPF 与 Frida 关联
- `syscall-filter-evidence` 【5/10】 — 系统调用过滤取证
- `syscall-observation-lab` 【5/10】 — 系统调用观察实验
- `aob-scan` 【4/10】 — 特征码扫描（AOB 字节数组定位）
- `code-inject` 【4/10】 — 代码注入（code cave/自动汇编/加载 DLL）
- `jmp-modify` 【4/10】 — 条件跳转改无条件（je→jmp）
- `jump-patch` 【4/10】 — 跳转指令补丁（je/jne/jmp/nop）
- `nop-remove` 【4/10】 — NOP 填充移除指令（跳过校验）
- `patch-apply` 【4/10】 — 二进制补丁写入
- `patch-rollback` 【4/10】 — 补丁回滚恢复原文件
- `exec-hook` 【3/10】 — 执行流重定向（Hook/跳板/拦截）

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
