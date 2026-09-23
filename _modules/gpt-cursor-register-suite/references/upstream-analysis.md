# 上游源码分析（4 仓库实测结论）

抓取时间：2026-09-23；方式：GitHub REST `git/trees?recursive=1` + `raw.githubusercontent.com`。

## 1. lxf746/any-auto-register（3309★ / Python / AGPL-3.0）

文件规模 316 个。分层：

```
core/         base_platform, base_mailbox(84KB), base_sms(55KB), base_captcha,
              base_identity, proxy_pool, proxy_providers, tls, registry,
              capability_registry, http_client, oauth_browser, manual_oauth_browser,
              registration/{adapters,flows,helpers,models,errors}
platforms/    chatgpt, cursor, grok, kiro, trae, windsurf, tavily, blink,
              cerebras, openblocklabs, anything（每个 6 件套）
providers/    captcha/{local_solver,manual,twocaptcha,yescaptcha}
              mailbox/{moemail,cfworker,ddg_email,duckmail,freemail,laoudo,
                       aitre,testmail,tempmail_lol,tempmail_web,local_ms_pool}
              proxy/*
application/  tasks.py(36KB 任务编排), accounts, exports(19KB)
api/          40+ 路由（accounts/tasks/sms/stats/provider_settings...）
```

关键实现点：

- **平台声明式能力**：`supported_executors=["protocol","headless","headed"]`、
  `protocol_captcha_order=("2captcha","capsolver","auto")`、
  `capabilities=["switch_desktop","query_state","generate_link"]`。
  新平台只需实现 `build_protocol_mailbox_adapter()` 与 `build_browser_registration_adapter()`。
- **OtpSpec 抽象**：`OtpSpec(wait_message="等待 Cursor 邮箱验证码...", success_label="验证码")`，
  邮箱取码与平台解耦，手动输入作为兜底回调。
- **Cursor 协议核心**（platforms/cursor/core.py）：Next.js Server Action 三 ID + `text/x-component`
  + `next-router-state-tree` 头 + 双层 urlencode state；`curl_cffi impersonate="safari17_0"`。
  Turnstile sitekey `0x4AAAAAAAMNIvC45A4Wjjln`。
- **代理池**（core/proxy_pool.py）：`success/(success+fail)` 排序取次，`ok==0 and fail>=5` 自动禁用。
- **ChatGPT sentinel**（platforms/chatgpt/sentinel_vm.py，30KB）：本地 PoW 求解 VM 实现。

## 2. ddCat-main/cursor-auto-register（892★ / Python）

46 个文件，单进程实现，比上游更"贴机器"：

- `cursor_auth_manager.py`：写 `state.vscdb` 的 `itemTable`，字段
  `cursorAuth/cachedSignUpType=Auth_0`、`cachedEmail`、`accessToken`、`refreshToken`；
  先 `SELECT COUNT(*)` 判断存在与否再 INSERT/UPDATE。
- `reset_machine.py`：写 `storage.json` 四项 telemetry 标识
  （devDeviceId=uuid4 / machineId=sha256(32B) / macMachineId=sha512(64B) / sqmId={UUID大写}）。
- `cursor_shadow_patcher.py`：备份 → 字节级替换机器码 → 回写；含随机 MAC 生成。
- `get_email_code.py`（23KB）：`tempmail.plus/api/mails?email=&limit=20&epin=<pin>`，
  判定 `result is True`；Web 模式用 `pending_verification_codes` 挂起队列 + 180s 超时转人工。
- `cursor_pro_keep_alive.py`（22KB）：Token 保活与试用期维持。

## 3. verssache/chatgpt-creator（328★ / Go / MIT）

20 个文件，纯协议注册，最干净的参考实现：

- `internal/register/flow.go`：visitHomepage → getCSRF → signin → authorize →
  register → sendOTP → validateOTP → createAccount → callback，
  每步 `randomDelay(0.2~1.5s)`；按落地路径（create-account/password |
  email-verification | about-you | callback）分流，支持中途续跑。
- `internal/sentinel/{generator,challenge,fnv}.go`：PoW 完整实现。
  20 项 config 数组、`"gAAAAAB"+b64+"~S"`、`"gAAAAAC"+b64`、
  FNV-1a32 + murmur3 avalanche。
- `internal/register/client.go` + `internal/chrome/profiles.go`：
  `bogdanfinn/tls-client` chrome131 指纹，随机 patch 版本 UA，
  三件套 sec-ch-ua 与 UA 自洽，cookie `oai-did` 显式注入。
- `internal/email/generator.go`：generator.email 抓 `.subj_div_45g45gg`，
  **必须显式 `Cookie: surl=<domain>/<user>`**；黑名单域自动落盘 `blacklist.json`。
- `internal/register/batch.go`：atomic 名额抢占，**失败归还名额重试**直到成功数达标。

## 4. AuuCoder/gptGrok2api（262★ / Python）

708 个文件，注册机 → API 网关的重度工程化：

- API 兼容层 + 账号状态机（`app/control/account/state_machine.py`、`refresh.py` 33KB、`scheduler.py`）
- 多后端账号存储：local / redis / sql 可切
- 注册侧：`api/register.py`（16KB）与 `register_test.py`（17KB，测试完备）
- 部署：docker compose + WARP SOCKS5 + privoxy + FlareSolverr
- 账号 → API 自动投递 NovaApi / Sub2API（`docs/AUTO_UPLOAD_SUB2API_CPA.md`）

## 复用结论

| 需求 | 抄哪个 |
|:--|:--|
| 注册机工程骨架 / 插件化 | any-auto-register |
| OpenAI sentinel PoW | chatgpt-creator（Go 逻辑最清晰）或 any-auto-register sentinel_vm |
| TLS 指纹 | chatgpt-creator（Go）/ any-auto-register（curl_cffi） |
| Cursor 协议注册 | any-auto-register platforms/cursor/core.py |
| Cursor 本地落地（注入/机器码） | ddCat-main cursor-auto-register |
| 账号池 → API 网关 | gptGrok2api |