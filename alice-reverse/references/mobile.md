# 移动端与 IL2CPP

**读取条件**：APK、IPA、Android、iOS、JNI、Frida/Objection、证书锁定、Root/模拟器与 Unity IL2CPP。

本索引包含 11 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `apk-reverse` 【9/10】 — 在 CLI 环境下做 Android APK 逆向时使用。适用于 APK 解包、Java 反编译、smali 修改、重打
- `eni-apk-reverse` 【9/10】 — APK 逆向 CLI 作业：解包/Java 反编译/smali 修改/重打包/Frida Hook，按需切 so/native 分析
- `mobile-reverse` 【9/10】 — Android/iOS 逆向：APK/IPA 分析、Frida/Objection、SSL pinning/root 检测研究
- `performing-mobile-app-certificate-pinning-bypass` 【9/10】 — 移动端证书锁定绕过
- `reverse-engineering-ios-app-with-frida` 【9/10】 — Frida 逆向 iOS 应用
- `eni-mobile-reverse` 【8/10】 — 仅文档：移动逆向四阶段工作流（信息收集→动态→静态→产出）
- `mobile-security` 【8/10】 — 移动端安全与反作弊研究
- `competition-android-hooking` 【7/10】 — CTF 沙箱子流：Android APK Frida hook、请求签名还原、SSL pinning 绕过与 JNI 边界分析
- `root-emulator-detection` 【5/10】 — Root/模拟器检测绕过
- `tls-pinning-analysis` 【5/10】 — TLS 锁定分析工作流
- `unity-il2cpp-analysis` 【5/10】 — Unity IL2CPP 逆向工作流

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
