# 能力清单与未来路线图

[English](capabilities-and-roadmap.md) | [简体中文](capabilities-and-roadmap.zh-CN.md)

本文梳理 `openai-security-review` 目前已经具备的能力，以及后续应该补强的方向。

这个项目面向已授权的防御性安全审计，适用于本地代码仓库、本地或测试环境 Web 应用，以及明确授权的目标。默认模式是静态分析、被动观察和只读验证。主动探针范围很窄，并且必须显式开启。

## 当前能力

### 1. 工作流调度

- 通过 `scripts/osr.mjs` 统一调度审计阶段。
- 通过 `references/osr.config.example.json` 配置目标、登录、爬取、后端分析、权限矩阵和主动探针。
- 支持 `--only`、`--skip`、`--dry-run`。
- 创建带状态的审计工作区，包含 `state/`、`evidence/`、`reports/` 和 Markdown 笔记。
- 通过 `scripts/generate_report.py` 生成综合报告。

### 2. 静态攻击面盘点

- 扫描仓库中的安全敏感文件和模式。
- 识别 auth、session、token、cookie 相关线索。
- 识别 role、permission、admin、tenant、organization、owner、policy 相关线索。
- 识别 API client、路由文件、redirect/callback、文件处理、DOM/XSS sink、SSRF-like URL fetcher 和 secret-like 配置。
- 对 secret-like 值做脱敏，避免写入报告。

### 3. 后端分析

- 识别常见 Node.js、Python、Java/Kotlin、Go、Ruby、PHP、.NET 后端框架信号。
- 构建服务端路由图谱。
- 分析路由附近的认证和授权信号。
- 检查 mutating 和高风险路由的输入校验覆盖情况。
- 生成 source-to-sink 审查队列，覆盖请求输入到 SQL/NoSQL、命令执行、外部请求、文件路径、redirect、模板渲染、反序列化等 sink 的邻近风险。
- 检查 CORS、CSRF、cookie、JWT、弱加密、debug 泄漏、secret-like 配置、路径穿越、SSRF fetcher、redirect、Docker 运行姿态和依赖清单。
- 支持 OpenAPI、Swagger、GraphQL schema 的 API spec 映射。

### 4. 浏览器与运行时观察

- Playwright 已作为项目标准依赖。
- 登录助手从环境变量读取测试账号，不把账号密码写入配置和报告。
- 被动同源爬取，并阻止非只读 HTTP 方法。
- 从浏览器实际观察到的 `fetch`、`xhr` 和 API-like 请求生成 runtime API/request map。
- 收集 console warning/error 和页面元信息。
- 做只读安全验证，包括响应头、source map、HTML 信号和明显错误泄漏。

### 5. API 和权限覆盖

- 从源码中提取 API-like 字符串、fetch/axios 调用、路由文件和方法线索。
- 对比源码 API 和运行时 API 覆盖。
- 支持 anonymous、user、admin、tenant 等 profile 的权限矩阵。
- 支持从环境变量注入 bearer token 等测试请求头。
- 权限矩阵只发送同源只读 `GET`、`HEAD`、`OPTIONS` 请求。

### 6. 受控主动验证

- 支持创建显式授权的主动验证计划。
- 受控主动探针需要配置授权和运行时二次确认。
- 覆盖低风险 CORS、redirect 参数、benign reflection、verbose error、public debug/config exposure 探针。
- 默认只允许本地目标；非本地目标需要显式开启。

### 7. 报告能力

- 生成综合 Markdown 报告，包含 scope、阶段状态、登录态、后端章节、假设队列、findings、攻击面、API 覆盖、权限矩阵、验证结果、主动验证和证据文件。
- Finding 模板包含 severity、status、location、evidence、impact、reasoning、fix、test。
- 假设队列会综合静态攻击面和后端分析信号。

## 当前边界

- 这个工具生成审查队列和证据，不会在未经确认时声称漏洞可利用。
- 静态 dataflow 目前是启发式邻近分析，不是完整 taint engine。
- 路由解析基于常见框架模式，不是覆盖所有语言的完整 AST 解析器。
- 浏览器爬取依赖路径覆盖，可能漏掉需要复杂交互的流程。
- 主动探针刻意保持很窄，不提交表单、不修改数据、不爆破、不 fuzz、不执行破坏性 payload。
- 虽然会脱敏 secret-like 值，仍然只应在有权限审查的仓库上运行。

## 未来路线图

### 阶段 1：精度与测试基准

目标：让现有后端解析能力更稳定、可度量。

- 增加 Express、NestJS、FastAPI、Django、Spring Boot、Gin、Rails、Laravel、Next.js API routes fixture。
- 为生成的 JSON state 文件增加 snapshot 测试。
- 增加纯前端仓库误报回归测试。
- 增加 CI，覆盖 `npm run check`、skill 校验和 fixture snapshot。

### 阶段 2：结构化解析器

目标：在工具链可用时减少正则解析的局限。

- 用 AST 解析 JavaScript/TypeScript 路由文件。
- 更精确解析 Python decorator、Pydantic 和 FastAPI model。
- 解析 Java/Kotlin 注解和 Spring Security 表达式。
- 解析 Go router group 和 middleware chain。
- 统一 `:id`、`{id}`、`<id>` 等路由参数格式。

### 阶段 3：Middleware 与 Policy Chain 映射

目标：把路由和真实保护层连接起来。

- 跟踪 Express/Fastify/Koa 的全局和 router 级 middleware。
- 跟踪 NestJS guards、interceptors、pipes、decorators。
- 跟踪 FastAPI dependencies 和 router 级 dependencies。
- 跟踪 Spring Security filters、annotations 和 route matchers。
- 区分 public route、authenticated route、authorization-enforced route。

### 阶段 4：更深入的数据流分析

目标：从“同文件邻近线索”升级到可追踪 source-to-sink 路径。

- 跟踪路由 handler 内的变量赋值和函数调用。
- 连接 controller、service、repository 和数据库访问层。
- 将 sink 分类为 parameterized、sanitized、allowlisted、unsafe。
- 增加 Prisma、TypeORM、SQLAlchemy、Django ORM、Hibernate/JPA、GORM、ActiveRecord、Eloquent 的框架特定规则。
- 增加 `confirmed_pattern`、`likely`、`needs_manual_trace` 等置信度。

### 阶段 5：输入校验与 Schema 覆盖

目标：让路由边界校验覆盖更具体。

- 将请求 schema 映射到路由。
- 检测全局 validation pipeline。
- 提取 allowed fields、required fields、enum、size、file type、自定义 validator。
- 标记在校验前读取 body/query/path 数据的路由。
- 生成缺失校验的测试建议。

### 阶段 6：运行时覆盖扩展

目标：在不提高风险的前提下增强只读动态证据。

- 将 backend runtime probe 与 source route map 对齐。
- 支持 backend probe 复用 Playwright storage state 中的认证 cookie。
- 增加只读 health、version、OpenAPI、Swagger、GraphQL、debug exposure 检查。
- 结合 source routes、API specs 和 runtime observations 做角色状态对比。
- 对 mutation-on-GET、异常跳转、不稳定目标增加停止条件。

### 阶段 7：API Contract 与 GraphQL 深化

目标：让大型服务的 API 契约审查更有用。

- 在可用时用正式 YAML parser 解析 OpenAPI YAML。
- 支持 Swagger UI config 发现。
- 支持 GraphQL introspection JSON。
- 对比 GraphQL Query/Mutation 与 resolver 文件。
- 报告 documented-but-unimplemented、implemented-but-undocumented 和 runtime-only endpoints。

### 阶段 8：报告质量与修复建议

目标：让输出更适合工程团队直接落地。

- 生成证据分级更清晰的 finding candidates。
- 为常见问题族生成修复建议和回归测试建议。
- 根据 severity、reachability、confidence 生成修复优先级。
- 支持 Markdown、JSON、SARIF-like 机器可读输出。
- 可选生成 GitHub/GitLab issue 模板。

### 阶段 9：分发与使用体验

目标：让项目更容易在 Codex 工作区之外运行。

- 增加轻量 CLI wrapper，同时保留 Codex skill 作为主要入口。
- 增加 `init` 命令交互式生成 `osr.config.json`。
- 增加 `doctor` 命令检查运行环境和 Playwright。
- 增加常见审计模式示例：frontend-only、backend-only、authenticated web app、API-only、role-matrix review。
- 增加 release tags 和 changelog。

### 阶段 10：安全边界与治理

目标：保证能力增强仍然服务于防御性审计。

- 不加入破坏性、爆破、凭据攻击、数据外传能力。
- 任何主动探针都必须显式授权和运行时确认。
- runtime probe 默认保持只读。
- state、evidence、report 中继续脱敏 secret。
- 增加项目自身安全策略，用于披露这个工具中的安全问题。

## 近期优先级

1. 后端阶段 fixture 测试。
2. Node.js 和 Python 框架的 middleware/policy chain 映射。
3. 更好的 route-to-validation 映射。
4. 更完整的 API spec 和 GraphQL 支持。
5. route map、role matrix、backend probe、API coverage 之间的运行时关联。
6. 带修复建议和测试建议的报告增强。
