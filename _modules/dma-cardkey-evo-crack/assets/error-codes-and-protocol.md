# Evo 授权链 —— 错误码对照与协议样本（实测）

> 来源：2026-09-18 对 `Evo_Crack.exe` 的 8 组动态验证。
> 只放协议结构与错误码，**不含任何真实卡密**。

---

## 1. 错误码对照表（客户端弹窗 / 日志里出现）

| 错误码 | 触发条件 | 对应链路阶段 | 排查动作 |
|---|---|---|---|
| **4** | 无网络 / 授权服务器不可达 | DNS 或 TCP 失败 | 检查网络、hosts、代理 |
| **8** | 服务器返回非法响应（响应解析失败） | TCP 通、HTTP 返回但 body 不合法 | 检查 mock 返回体格式 |
| **1201** | 真实服务器响应但业务拒绝，或响应解密失败 | 业务层 | **链路已打通**，问题在凭据/协议 |

**判读技巧**：`4 -> 8 -> 1201` 的变化说明链路在推进（DNS -> TCP -> 业务），
可以用来定位卡在哪一环。**1201 不是"绕过失败"，而是"进展信号"。**

---

## 2. 验证矩阵（8 组，全部以 rc=3 退出）

| # | 配置 | 错误码 | 结论 |
|---|---|---|---|
| 1 | 无网络 | 4 | 链路第一跳就断 |
| 2 | Mock 返回非法响应 | 8 | HTTP 通了，body 不合法 |
| 3 | 真实服务器（经 Clash 代理） | 1201 | 业务层拒绝 |
| 4 | `EVO_PASS_ACCEPT_ANY_AUTH=1` | 1201 | 开关只影响本地 fixture |
| 5 | `--accept-any-auth` | 1201 | 同上 |
| 6 | `--accept-any-auth --elevated` | 1201 | 提权不改变校验结果 |
| 7 | `EVO_PASS_PRESERVE_INVALID_AUTH=1` | 1201 | 诊断模式，同上 |
| 8 | Mock（hosts 把 scheats.club 指向 127.0.0.1） | 8 | 劫持生效，但响应体不被接受 |

**结论**：两个开关只影响**本地 fixture 行为**（是否伪造），
真实校验链仍需上游 200 + 合法响应体。**无有效卡密时无法通过。**

---

## 3. 上游请求样本（实测 3 次采样一致的结构）

```
POST /1 HTTP/1.1
connection: close
content-length: 378
host: freakluke.me:8880

<378 字节二进制 body>
```

### body 结构

```
offset 0    uint32 LE = 378        自描述长度（= body 总长）
offset 4    uint32 LE = 变化值      nonce / tick
                                   采样值: 0x67429 / 0x6a4e3 / 0x892a0 / 0x900a0
offset 8..  高熵密文                AES-256-CBC
尾部        8 字节 0 对齐 + 24~32 字节尾块（HMAC / 校验）
```

### 加密证据（API 调用链）

```
BCryptOpenAlgorithmProvider("AES")
BCryptSetProperty(ChainingModeCBC)
BCryptGetProperty
BCryptGenerateSymmetricKey
BCryptEncrypt / BCryptDecrypt
BCryptGenRandom
```

### 相关错误串（来自 dump，说明 AES 是 fixture 用的）

```
AES fixture key/IV size invalid
BCryptOpenAlgorithmProvider failed
BCryptSetProperty(CBC) failed
BCryptGetProperty failed
BCryptGenerateSymmetricKey failed
BCryptEncrypt failed
AES fixture decrypt input invalid
BCryptDecrypt failed
BCryptGenRandom failed
```

---

## 4. 响应体字段（服务端 -> 客户端，JSON）

| 字段 | 含义 | 被重写的正则 |
|---|---|---|
| `Hwid` | 机器码回执 | `\"Hwid\"\s*:\s*\"[^\"]*\"` |
| `UserId` | 用户 ID | `\"UserId\"\s*:\s*\"[^\"]*\"` |
| `server_time` | 服务器时间 | `\"server_time\"\s*:\s*\"[^\"]*\"` |
| `token` | 会话令牌 | `(\"\S*\"\s*:\s*\")([^\"]*)(\")` |
| `user_id` | 用户 ID（小写变体） | `(\"user_?id\"\s*:\s*\")([^\"]*)(\")` |
| `username` | 用户名 | 同上 |
| `hwid` | 机器码（小写变体） | 同上 |

---

## 5. 被拦截的 API 路径

```
/user/authorize
/session/validate
/v2/user/subscription/
/v2/product/
```

MIME：`application/json`；上游类型：`application/octet-stream`
认证头：`Bearer <token>`

---

## 6. 域名与解析

| 域名 | 真实 IP（DoH 实测） | 归属 |
|---|---|---|
| `freakluke.me` | `172.67.190.7` / `104.21.73.124` | Cloudflare |
| `scheats.club` | `172.67.220.124` / `104.21.17.33` | Cloudflare |
| （代理环境下） | `198.18.1.130` | **Clash fake-IP，非真实地址** |

> 端口：`freakluke.me:8880`（上游授权）、`127.0.0.1:443`（本地 TLS 监听）

---

## 7. 注入的 hosts 条目（客户端自身会写）

```
127.0.0.1 scheats.club
127.0.0.1 www.scheats.club
127.0.0.1 api.scheats.club
```

随后执行 `ipconfig /flushdns >nul 2>&1`。

---

## 8. 授权文件落盘路径

```
C:\Evo\user.dat          最终授权文件（原子替换写入）
%TEMP%\...\user.dat       临时文件，写完 rename
```

日志（JSON Lines）：`evo_pass.jsonl`（相对路径 -> 落在进程 CWD）

事件名全表：
```
startup / elevation_skipped / hosts_override_failed / upstream_resolved /
certificate_trust_failed / certificate_installed_background / certificate_already_trusted /
tls_listener_ready / evo_started / auth_mode / local_auth_identity_issued /
local_auth_any_accept / heartbeat_session_replayed / subscription_fixture_fallback /
connection_error / resolution_failed
```
