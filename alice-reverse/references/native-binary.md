# 原生与托管二进制

**读取条件**：PE、ELF、SO、DLL、EXE、.NET、反汇编、函数、导入表、字符串与交叉引用。

本索引包含 10 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `dotnet-reverse` 【9/10】 — .NET / C# 二进制逆向。当目标是 .NET assembly（PE 头含 CLR、.exe/.dll 托管程序）
- `binary-analysis` 【6/10】 — 静态二进制逆向：PE/ELF 结构分析、模式扫描、反汇编与补丁生成
- `coldbrew-native-reverse` 【4/10】 — PE/ELF/SO、JNI、OLLVM、dump、补丁时使用。
- `import-analyze` 【4/10】 — 导入表分析（DLL 依赖）
- `string-extract` 【4/10】 — 字符串提取与模式匹配
- `dn-decompile` 【3/10】 — .NET 程序集反编译（ILSpy/dotPeek）
- `dn-edit` 【3/10】 — .NET IL 编辑修改
- `dn-save` 【3/10】 — .NET 程序集保存回写
- `function-decompile` 【3/10】 — 函数反编译与关键逻辑识别
- `xref-trace` 【3/10】 — 交叉引用追踪

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
