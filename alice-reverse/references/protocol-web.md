# 协议、API 与 Web 运行时

**读取条件**：TCP/UDP、自定义协议、API 签名、HAR、JavaScript、WebCrypto、WebSocket/gRPC 与流量还原。

本索引包含 15 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `js-reverse` 【9/10】 — JavaScript 逆向：混淆还原、签名/HMAC 定位、浏览器环境补丁与前端加密提取
- `protocol-reverse-engineering` 【9/10】 — 协议逆向（封包分析/解析/文档化）
- `reverse-engineering-api` 【9/10】 — Web API 逆向生成 Python 客户端
- `eni-js-reverse` 【8/10】 — 仅文档：js-reverse-mcp 前端 JS 逆向（签名链路定位/页面取证/补环境复现）
- `re-flow-capture` 【7/10】 — 网络抓包（Wireshark/Fiddler/Frida）
- `reverse-engineering-api-setup` 【5/10】 — API 逆向外部工具装配
- `webcrypto-hooking` 【5/10】 — WebCrypto 钩取工作流
- `webpack-vite-nextjs-reversing` 【5/10】 — Webpack/Vite/NextJS 逆向
- `websocket-grpc-analysis` 【5/10】 — WebSocket/gRPC 分析工作流
- `websocket-live-reversing` 【5/10】 — WebSocket 实时逆向
- `encrypt-detect` 【4/10】 — 流量加密识别（AES/XOR/Base64 模式）
- `protocol-reconstruction` 【4/10】 — 协议重建工作流
- `proxy-traffic-analysis` 【4/10】 — 代理流量分析工作流
- `coldbrew-api-reverse` 【3/10】 — 前端签名、HAR、鉴权链路、加密参数还原时使用。
- `coldbrew-protocol-reverse` 【3/10】 — 自定义协议、TCP/UDP 帧、回放与字段还原时使用。

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
