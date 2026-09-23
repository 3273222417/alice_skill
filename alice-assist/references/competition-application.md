# 竞赛应用与协议链

**读取条件**：Web 运行时、协议、解析器、消息队列、竞态、模板、PCAP 与应用攻击链案例。

本索引包含 18 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `competition-web-runtime` 【7/10】 — CTF 沙箱子流：Web/API/SSR/队列应用调试、隐藏路由与前后端行为分歧
- `competition-browser-persistence` 【6/10】 — CTF 沙箱子流：浏览器 cookie/localStorage/IndexedDB 等客户端状态持久化与会话重放
- `competition-bundle-sourcemap-recovery` 【6/10】 — CTF 沙箱子流：source map/构建 manifest/前端 bundle 还原隐藏路由与接口
- `competition-crypto-mobile` 【6/10】 — CTF 沙箱子流：编解码/隐写与 APK/IPA 移动信任边界、请求签名还原
- `competition-custom-protocol-replay` 【6/10】 — CTF 沙箱子流：自定义二进制/文本协议还原、握手重建与有状态会话重放
- `competition-file-parser-chain` 【6/10】 — CTF 沙箱子流：文件上传/导入/预览/解压到反序列化解析链路追踪
- `competition-graphql-rpc-drift` 【6/10】 — CTF 沙箱子流：GraphQL/RPC schema 与 handler 漂移、隐藏操作还原
- `competition-ios-runtime` 【6/10】 — CTF 沙箱子流：IPA 运行时分析、ObjC/Swift 方法追踪、Keychain 与 pinning 绕过
- `competition-jwt-claim-confusion` 【6/10】 — CTF 沙箱子流：JWT/JWS/JWE 校验路径、alg 混淆、受众/签发者校验缺陷
- `competition-pcap-protocol` 【6/10】 — CTF 沙箱子流：PCAP 会话重建、协议解码与包到进程关联
- `competition-queue-worker-drift` 【6/10】 — CTF 沙箱子流：队列/异步 worker/cron 重试行为与 payload 副作用链
- `competition-race-condition-state-drift` 【6/10】 — CTF 沙箱子流：竞态窗口、幂等失败、并发状态漂移类缺陷复现
- `competition-request-normalization-smuggling` 【6/10】 — CTF 沙箱子流：解析器差分、HTTP 规范化缺口与请求走私路线
- `competition-runtime-routing` 【6/10】 — CTF 沙箱子流：反向代理、Host/转发头、vhost 路由与多节点路由解析
- `competition-stego-media` 【6/10】 — CTF 沙箱子流：图像/音频/视频/文档/容器隐写载荷还原
- `competition-supply-chain` 【6/10】 — CTF 沙箱子流：CI/CD、registry、依赖漂移、制品溯源与发布链篡改
- `competition-template-render-path` 【6/10】 — CTF 沙箱子流：SSR/模板渲染/hydration 边界与模板到 handler 执行缺口
- `competition-websocket-runtime` 【6/10】 — CTF 沙箱子流：WebSocket/SSE 握手、订阅状态与实时帧驱动行为

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。
