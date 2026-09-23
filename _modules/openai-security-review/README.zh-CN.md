# Codex OpenAI 安全审计 Skill

[English](README.md) | [简体中文](README.zh-CN.md)

一个面向已授权代码仓库和 Web 应用的 Codex 原生安全审计 skill。它把源码分析、浏览器观测、API 覆盖对比、权限矩阵、受控主动探针和 Markdown 报告串成一套完整工作流。

> 仅用于已授权的防御性测试。本项目不会执行爆破、破坏性请求、数据外传或高风险变更类攻击 payload。

完整能力清单和未来路线图见：[能力清单与未来路线图](docs/capabilities-and-roadmap.zh-CN.md)。

## 功能

- 创建带状态的审计工作区，保存 notes、evidence、JSON state 和 reports。
- 扫描源码攻击面：路由、API client、auth/session、角色权限、token、redirect、文件处理、SSRF-like URL fetcher、XSS sink、secret-like 配置。
- 后端框架识别、服务端路由图谱、授权信号分析、输入校验覆盖、source-to-sink 审查队列、服务端安全配置检查、API spec 覆盖对比。
- 根据源码信号生成漏洞假设队列。
- 使用 Playwright 和测试账号登录，账号密码从环境变量读取。
- 做安全只读验证，例如响应头、HTML 信号、source map、错误泄漏。
- 使用 Playwright 被动爬取同源页面，并阻止非只读请求。
- 从实际浏览器请求生成 runtime API/request map。
- 从源码提取 source API map。
- 对比源码 API 和运行时 API 覆盖情况，识别 source-only 和 runtime-only 接口。
- 对 anonymous、user、admin、tenant 等 profile 做角色/权限矩阵检查。
- 创建显式授权的主动验证计划。
- 在配置授权和运行时二次确认后执行低风险主动探针。
- 生成综合 Markdown 安全报告。

## 目录结构

```text
.
  README.md
  README.zh-CN.md
  LICENSE
  SKILL.md
  agents/openai.yaml
  docs/
  package.json
  references/osr.config.example.json
  references/review-playbook.md
  references/report-template.md
  scripts/
```

## 安装

从 GitHub 安装 skill：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Why-WU/codex-security-review \
  --path . \
  --name openai-security-review
```

安装后重启 Codex，然后安装运行依赖：

```bash
cd ~/.codex/skills/openai-security-review
npm install
npm run setup
```

如果提示缺少 Chromium：

```bash
npx playwright install chromium
```

## 快速开始

可以直接对 Codex 说：

```text
Use openai-security-review to audit /path/to/repo. The target URL is http://localhost:5173.
```

更推荐使用配置文件和统一调度器：

```bash
cd ~/.codex/skills/openai-security-review
cp references/osr.config.example.json ./osr.config.json
```

编辑 `osr.config.json`：

```json
{
  "target": {
    "repo": "/path/to/repo",
    "url": "http://localhost:5173"
  },
  "workspace": {
    "path": "/tmp/openai-security-review-demo"
  }
}
```

预览将执行哪些阶段：

```bash
npm run scan -- --config ./osr.config.json --dry-run
```

执行审计：

```bash
npm run scan -- --config ./osr.config.json
```

最终报告位置：

```text
<workspace>/reports/report.md
```

## 登录态配置

如果目标应用需要登录，在配置中启用 `auth`：

```json
{
  "auth": {
    "enabled": true,
    "loginUrl": "http://localhost:5173/login",
    "usernameEnv": "OSR_USERNAME",
    "passwordEnv": "OSR_PASSWORD",
    "usernameSelector": "input[name=\"email\"]",
    "passwordSelector": "input[name=\"password\"]",
    "submitSelector": "button[type=\"submit\"]",
    "successUrlContains": "/dashboard"
  }
}
```

账号密码通过环境变量提供：

```bash
export OSR_USERNAME="test@example.com"
export OSR_PASSWORD="test-account-password"
npm run scan -- --config ./osr.config.json
```

账号密码不会写入配置、证据文件或报告。

## API 图谱和覆盖率

工作流可以生成：

- `state/api_map.json`：Playwright 观察到的运行时请求。
- `state/source_api_map.json`：源码中发现的 API 线索。
- `state/api_coverage.json`：源码和运行时的覆盖对比。

对应 Markdown 证据文件：

```text
evidence/api_map.md
evidence/source_api_map.md
evidence/api_coverage.md
```

## 后端分析

在 `osr.config.json` 中启用后端阶段：

```json
{
  "backend": {
    "enabled": true,
    "frameworkHints": [],
    "fingerprint": true,
    "routeMap": true,
    "authzMap": true,
    "dataflowRiskMap": true,
    "validationCoverage": true,
    "serverChecks": true,
    "apiSpecMap": true,
    "apiSpecPaths": [],
    "runtimeValidation": false,
    "runtimeProbePaths": []
  }
}
```

后端阶段会生成框架、路由、授权、校验、数据流、服务端安全配置和 API 契约覆盖相关的 state 文件。JavaScript/TypeScript 的后端扫描会收敛到明确的服务端路径和框架信号，例如 `server/`、`backend/`、`routes/`、`controllers/`、`middleware/`、`pages/api/` 和 Next.js `app/**/route.ts`，避免把普通前端 API client 当成服务端漏洞。

只运行后端阶段：

```bash
npm run scan -- --config ./osr.config.json --only backend
```

后端运行时验证默认关闭。启用后也只发送同源 `GET`、`HEAD`、`OPTIONS` 请求，不发送请求体。

## 角色/权限矩阵

启用 `accessMatrix` 后，可以比较不同 profile 对只读接口的访问情况：

```json
{
  "accessMatrix": {
    "enabled": true,
    "maxEndpoints": 50,
    "includeSourceOnly": true,
    "includeUnknownSourceAsGet": false,
    "profiles": [
      {
        "name": "anonymous"
      },
      {
        "name": "admin",
        "storageState": "/tmp/openai-security-review-demo/state/authenticated-storage-state.json",
        "expectAccess": true
      }
    ],
    "paths": []
  }
}
```

权限矩阵只发送同源只读请求，方法限定为 `GET`、`HEAD`、`OPTIONS`。它会记录每个 profile 的状态码，并提示匿名访问敏感路径、预期可访问却失败、预期拒绝却成功等信号。

如果 API 使用 bearer token，可以通过环境变量注入请求头：

```json
{
  "name": "admin-api",
  "headersFromEnv": {
    "Authorization": "OSR_ADMIN_AUTH_HEADER"
  },
  "expectAccess": true
}
```

然后设置：

```bash
export OSR_ADMIN_AUTH_HEADER="Bearer test-token"
```

## 受控主动探针

主动探针默认关闭。要启用，需要显式配置：

```json
{
  "active": {
    "enabled": true,
    "authorized": true,
    "executeSafeProbes": true,
    "probeClasses": ["cors", "redirect", "xss", "error", "exposure"],
    "allowRemote": false,
    "timeout": 10
  }
}
```

运行时还需要二次确认。交互式运行时，调度器会在静态和被动检查结束后给出两个选项：`ACTIVE` 或 `NOT ACTIVE`（默认）；非交互模式下请显式传入 `--confirm-active`：

```bash
npm run scan -- --config ./osr.config.json --confirm-active
```

受控主动探针覆盖：

- CORS 任意 Origin 检查。
- benign open redirect 参数检查。
- benign reflection marker 检查。
- verbose error/debug 泄漏检查。
- public config/debug 暴露检查。

它不会爆破、提交表单、修改数据或执行破坏性 payload。非本地目标默认拒绝，除非显式启用 `allowRemote`。

## 常用命令

只跑静态源码映射和报告生成：

```bash
npm run scan -- --config ./osr.config.json --only workspace,inventory,hypotheses,source-map,report
```

跳过浏览器阶段：

```bash
npm run scan -- --config ./osr.config.json --skip auth,crawl,access-matrix,active
```

在非交互模式下确认并运行受控主动探针：

```bash
npm run scan -- --config ./osr.config.json --confirm-active
```

检查运行环境：

```bash
npm run check
```

## 输出文件

典型工作区结构：

```text
00-scope.md
01-inventory.md
02-findings.md
03-hypotheses.md
state/
  manifest.json
  attack_surface.json
  hypotheses.json
  passive_validation.json
  passive_crawl.json
  api_map.json
  source_api_map.json
  api_coverage.json
  backend_fingerprint.json
  server_route_map.json
  authz_map.json
  dataflow_risk_map.json
  validation_coverage.json
  server_security_checks.json
  api_spec_map.json
  backend_runtime_validation.json
  role_matrix.json
  active_validation.json
  active_probe.json
evidence/
  passive_validation.md
  passive_crawl.md
  api_map.md
  source_api_map.md
  api_coverage.md
  backend_fingerprint.md
  server_route_map.md
  authz_map.md
  dataflow_risk_map.md
  validation_coverage.md
  server_security_checks.md
  api_spec_map.md
  backend_runtime_validation.md
  role_matrix.md
  active_validation_plan.md
  active_probe.md
reports/
  report.md
```

## 安全边界

- 只用于你拥有或明确授权测试的系统。
- 优先用于本地或 staging 环境。
- 使用专用测试账号和合成数据。
- 凭据只放在环境变量里。
- 被动爬取会阻止非只读请求。
- 权限矩阵只做同源只读请求。
- 主动探针需要配置授权和运行时二次确认。
- 更深入的项目特定验证器应单独审查后再使用。
