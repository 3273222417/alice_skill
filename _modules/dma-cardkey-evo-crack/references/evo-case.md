# Evo 卡密逆向 —— 完整实测记录

> 记录时间: 2026-09-18
> 目标目录: `C:\Users\alicewe\Desktop\evoc`
> 结论: **Evo_Crack.exe = 本地 TLS 中间人代理 + 授权服务器伪造器**，不改主程序。

---

## 0. 样本指纹

| 文件 | 大小 | SHA256 | 保护 |
|---|---|---|---|
| `Evo_Crack.exe` | 21,897,728 | `49E19C757B182897599D09934F741F5D33F3FE3A7BB3EE7978FF49434CB509E5` | 自研/VM 虚拟化（15 段随机名） |
| `evo.exe` | 34,249,744 | `5363DAE63DB475AC6739E2CC33C9C97CACD7261AFA497022238BE2E3866146FB` | Themida / WinLicense |

- `Evo_Crack.exe` 编译时间戳 2026-09-13（比 evo.exe 的 2026-09-05 晚 8 天）
- 两者均 **NotSigned**、无版本信息资源

---

## 1. 静态侦察结果

### Evo_Crack.exe

```
PE64 GUI, ImageBase 0x140000000, EP RVA 0xEA3FE1, manifest=requireAdministrator

段: .text .rdata .data .pdata
    .Oh5 .2d8ld .ASLpfR .1wLKw .JMZ7 .LBI .F67vkD   <- 全 RAW=0/RS=0 (运行时填充)
    .5[Q    VA=0x50000   VS=0xE1E07F (14.7MB)  RAW=0   <- 解包目标
    .Plh    VA=0xE6F000  VS=0x198  RAW=0x400 RS=0x200 <- IAT 区
    .3p[    VA=0xE70000  VS=0x14E1894 (21.9MB) RAW=0x600 RS=0x14E1A00 <- 主体
    .rsrc   VA=0x2352000 VS=0x1D6 (仅 RT_MANIFEST)

导入表: 23 个 DLL, 每个只保留 1 个导入
  ADVAPI32.dll -> GetTokenInformation
  CRYPT32.dll  -> CertAddEncodedCertificateToStore
  DNSAPI.dll   -> DnsFree
  KERNEL32.dll -> AreFileApisANSI
  MSVCP140.dll -> ??0?$basic_ios@...
  SHELL32.dll  -> ShellExecuteExW
  Secur32.dll  -> AcceptSecurityContext
  VCRUNTIME140.dll -> _CxxThrowException
  WINHTTP.dll  -> WinHttpCloseHandle
  WS2_32.dll   -> accept
  bcrypt.dll   -> BCryptCloseAlgorithmProvider
```

### 段熵（静态文件）

| 区间 | 熵 | 解读 |
|---|---|---|
| 0x0 - 0x8 万 | 7.99 | VM 字节码 / 加密数据 |
| 0x8 万 - 0x200 万 | **6.0** | **典型 VM 字节码熵区** |
| 0x200 万 - 末尾 | 7.99 | 加密数据 |

### evo.exe

```
段名: 前 8 段名为空(Padding)  .debug .idata .tls .rsrc
      .themida  VA=0x2635000 VS=0x125C000 RAW=0x13BE600 RS=0    <- 运行时展开
      .boot     VA=0x3891000 VS=0xCEB600  RAW=0x13BE600 RS=0xCEB600 ch=0x60000060
      .reloc
EP RVA 0x3891058 (= .boot 段)
全部 8 个主段 entropy 7.9+
明文串: 仅 989 条 ASCII len>=10, 0 条 UTF-16
Themida/VMProtect/freakluke/scheats/C:\Evo/user.dat 关键字全部 0 命中
```

### 依赖栈

```
vmm.dll            2,327,552  PCILeech VMM
leechcore.dll        126,464  导出 19 个: LcAllocScatter1..3/LcClose/LcCommand/LcCreate/
                              LcCreateEx/LcDeviceParameterGet(Numeric)/LcGetOption/LcMemFree/
                              LcMemMap_*/LcRead/LcReadScatter/LcSetOption/LcWrite/LcWriteScatter
leechcore_driver.dll  23,552  内核驱动
FTD3XX.dll           513,928  导出 47 个 FT_* (FTDI FT60x USB3)
tinylz4.dll           19,456  LZ4_compress_default / LZ4_decompress_safe
info.db            5,054,464  SQLite format 3
cloudflared.exe   65,210,696  Cloudflare Quick Tunnel
```

**判定: DMA 硬件外挂（Valorant 用），Evo_Crack.exe 是卡密绕过工具。**

---

## 2. 动态侦察 —— 突破过程

### 2.1 提权问题

| 尝试 | 结果 |
|---|---|
| `Start-Process` 直接跑 | 「请求的操作需要提升」 |
| `frida.spawn` | `NotSupportedError 0x2e4` |
| `Start-Process -Verb RunAs` | ✅ 成功（PID 23116），但生命周期绑定调用者 |
| **schtasks /rl HIGHEST** | ✅✅ 最可靠，完全脱离会话 |

环境：`EnableLUA=1` / `ConsentPromptBehaviorAdmin=0` / `PromptOnSecureDesktop=0`
→ 管理员组用户可**静默提权**（无 UAC 弹窗）。

### 2.2 首次裸跑

```
C:\Users\alicewe\Desktop\evoc>echo EVO-TESTKEY-0001-AAAA-BBBB| Evo_Crack.exe
请输入卡密: 卡密验证失败：接收失败（错误码 4）
EXITCODE=3
```

**副作用检查（282 个文件 hash 全对比）**：
- 文件系统：**零写入**
- 注册表：Run 键无变化、无新服务/驱动
- `C:\Evo`：未创建
- hosts：未修改

结论：**卡密 = 纯网络验证，本地无持久化**。

### 2.3 Frida 探针的两轮失败

**第 1-2 轮**：日志只有模块列表，**零行为事件**。

根因（后来定位）：
```js
Module.getExportByName('KERNEL32.dll','CreateFileW')   // Frida 17 已移除!
// -> TypeError: not a function，被 try/catch 静默吞掉
```

**修正**：
```js
Process.getModuleByName('KERNEL32.dll').getExportByName('CreateFileW')   // 0x7fffbcee70b0
Module.getGlobalExportByName('CreateFileW')                              // 备选
```

**第 3 轮**：还是没喂进卡密。根因：`dev.spawn()` 缺 `stdio="pipe"`。

**第 4 轮**：96 钩子成功装载（8 个失败），完整行为链捕获。

---

## 3. 捕获到的完整行为链

### 3.1 启动自解密（T+1.0 ~ 1.3s）

```
[T+0.996] NtQueryInformationProcess(class=0)          <- 反调试探测
[T+1.160] NtQueryInformationProcess(class=37)
[T+1.166] WriteProcessMemory(proc=0xffffffffffffffff, addr=0x7fffbe610008, size=5)
          e9 ab 17 ef ff                               <- jmp rel32
[T+1.166] WriteProcessMemory(proc=0xffffffffffffffff, addr=0x7fffbe610015, size=6)
          ff 25 00 00 00 00                            <- jmp [rip+0]
[T+1.167] VirtualProtect(addr=0x7fffbe610000, size=0x1000, prot=0x20)  <- PAGE_EXECUTE_READ
... (共 18 组, 覆盖 9 个不同 DLL 区域)
[T+1.288] OpenProcessToken(access=0x8)
[T+1.288] GetTokenInformation(class=20)                <- 检查自身提权状态
[T+1.315] STDOUT> 请输入卡密:
```

**解读**：VM 壳把已加载 DLL 的 IAT 槽改写成跳到 VM 桩的 jmp —— **IAT 混淆**。

### 3.2 卡密输入后（T+4.0s）

```
[T+4.017] GetComputerNameW -> "ALICE"                  <- 机器码采集
[T+4.143] getaddrinfo("freakluke.me", "8880")          <- ★ 授权服务器
[T+4.143] LoadLibraryExW("C:/Windows/System32/mswsock.dll")
[T+4.144] RegCreateKeyExW(..., "System/CurrentControlSet/Services/Tcpip/Parameters")
[T+4.144] RegOpenKeyExW(..., "Software/Policies/Microsoft/Windows NT/DnsClient")
... (DNS/Winsock 标准初始化, 非恶意)
[T+4.148] connect -> 198.18.1.130:8880                 <- Clash fake-IP
[T+4.154] SEND 463 bytes:
          POST /1 HTTP/1.1
          connection: close
          content-length: 378
          host: freakluke.me:8880
```

### 3.3 请求体（378 字节，3 次采样）

```
样本1: 7a 01 00 00 | 29 74 06 00 | <372B 密文>
样本2: 7a 01 00 00 | e3 a4 06 00 | <372B 密文>
样本3: 7a 01 00 00 | a0 92 08 00 | <372B 密文>
       ^^^^^^^^^^^   ^^^^^^^^^^^
       = 378 (LE)    nonce/tick 变化
       自描述长度
末尾: 8 字节 0 对齐 + 24~32 字节尾块
```

**加密证据**（hook 到的 BCrypt 调用）：
```
BCryptOpenAlgorithmProvider("AES")
BCryptSetProperty(ChainingModeCBC)
BCryptGenerateSymmetricKey
BCryptEncrypt / BCryptDecrypt
BCryptGenRandom
```

### 3.4 失败路径

```
[T+15.800] STDOUT> 卡密验证失败：接收失败（错误码 4）
[T+15.801] CRT exit(3) — freezing
```

---

## 4. 内存 dump

### 4.1 产物

```
C:\wz_evoc\dumps\
  mod_Evo_Crack.exe.bin       37,040,128   <- 主模块完整镜像, 熵 7.7875
  mod_ntdll.dll.bin            2,519,040
  mod_KERNEL32.DLL.bin           831,488
  mod_KERNELBASE.dll.bin       4,202,496
  mod_SHELL32.dll.bin          7,962,624
  mod_combase.dll.bin          3,690,496
  mod_USER32.dll.bin           1,896,448
  mod_ole32.dll.bin            1,679,360
  mod_CRYPT32.dll.bin          1,564,672
  mod_DNSAPI.dll.bin           1,409,024
  mod_ucrtbase.dll.bin         1,359,872
  mod_WINHTTP.dll.bin          1,220,608
  ... (共 38 个模块)
  live_rwx_00_7fffb34d7000.bin    36,864  <- VM 解包残留
  live_rwx_05_7fffbe397000.bin    36,864
  live_rwx_01..09_*.bin            4,096  <- 9 个 RWX 页 (VM 桩)
```

### 4.2 解包后的段熵对比

| 段 | 静态熵 | **live 熵** | 变化 |
|---|---|---|---|
| `.text` | 0.000 (RAW=0) | **6.517** | 已解密 |
| `.rdata` | 0.000 | **6.356** | 已解密 |
| `.data` | 0.000 | 3.910 | 已解密 |
| `.ASLpfR` | 0.000 | 7.957 | 仍加密 |
| `.3p[` | 7.864 | 7.864 | 仍加密 |

### 4.3 卡密在内存中的 3 处副本

```
[0] base=0x550000 addr=0x5764e0  (UTF-16, 环境块中)
[1] base=0x550000 addr=0x576540  (ASCII, 输入缓冲)
[2] base=0x550000 addr=0x5767b0  (UTF-16, 请求组装区)
```

周围可见：`ALLUSERSPROFILE=C:\ProgramData` / `ALICE` / `BlueTooth Namespace` /
`f.r.e.a.k.l.u.k.e...m.e` / `EVO-TESTKEY-0001-AAAA-BBBB` / `L.S.A.R.P.C._.E.N.D.P.O.I.N.T` /
`N.T. .A.U.T.H.O.R.I.T.Y.\.S.Y.S`

---

## 5. ★ 破解原理（从 dump 还原）★

### 5.1 内部字符串全表（UTF-16LE @ dump 0x28190-0x29000）

```
0x28190  请输入卡密: 
0x28250  未配置服务器信息
0x28268  连接服务器失败
0x28278  发送失败
0x28288  接收失败
0x28298  无效数据包
0x282A8  无效数据
0x282B8  数据损坏
0x282C8  客户端版本停止服务
0x282E0  客户端版本已过期
0x282F8  未知错误
0x28308  失败：
0x28312  错误码 
0x28328  初始化
0x28330  卡密不能为空。
0x28348  卡密长度超过 511 字节。
0x28368  卡密必须以 EVO 开头。
0x28388  卡密验证
0x28398  登录完整性校验
0x283A8  登录成功
```

### 5.2 加密 / TLS 相关

```
0x284D8  HTTP/1.1 
0x284EA  Connection
0x28500  Content
0x28508  Length
0x2851C  fixture
0x28528  IV siz
0x28530  invalidAES
0x28568  ChainingModeCBC
0x28588  ChainingMode
0x285C8  ObjectLength
0x28688  BCryptGenRandom
0x288F4  client close
0x28902  during handshake
0x28918  CompleteAuthToken
0x2893C  handshake
0x28946  send failed
0x28958  AcceptSecurityContext
0x28986  truncatedQueryContextAttributes(STREAM_SIZES)
0x289D2  is not supported b...
0x28A70  Microsoft Unified Security Protocol Provider
0x28AD0  AcquireCredentialsHandle
0x28B30  runas
0x28B40  --elevated
0x28B58  EVO_PASS_ACCEPT_ANY_AUTH
0x28B78  --accept-any-auth
0x28BC8  EVO_PASS_PRESERVE_INVALID_AUTH
0x28BE8  --preserve-invalid-auth
0x28C50  EVO_PASS/1.0                          <- User-Agent
0x28CC0  Host: scheats.club                    <- 上游请求头
0x28DE8  C:\Evo\user.dat
0x28DF4  tempdata.evo.tmp
0x28E28  create temporary user
0x28E60  user.dat failed: 
0x28E78  replace C:\Evo\user.dat failed: 
0x28EA0  evo_pass.jsonl
0x28EBE  override and certificate trust may fail
0x28EE8  elevation_skipped
0x28F00  startup
0x28F38  hosts_override_failed
0x28F50  upstream_resolved
0x28F68  embedded CER win32=
0x28F80  certificate_trust_failed
0x28FA6  machine
0x28FAE  ROOT store
0x28FC0  certificate_installed_background
0x28FE8  certificate_already_trusted
0x29010  1443: (行号)
```

### 5.3 事件日志事件名

```
startup                      elevation_skipped
hosts_override_failed        upstream_resolved
certificate_trust_failed     certificate_installed_background
certificate_already_trusted  tls_listener_ready
evo_started                  auth_mode
local_auth_identity_issued   local_auth_any_accept
heartbeat_session_replayed   subscription_fixture_fallback
connection_error             resolution_failed
```

### 5.4 API 路径

```
/user/authorize            登录授权
/session/validate          会话校验（心跳）
/v2/user/subscription/     订阅状态
/v2/product/               产品信息
```

---

## 6. 动态验证矩阵

| # | 配置 | 结果 | 错误码 |
|---|---|---|---|
| 1 | 无网络 | 接收失败 | **4** |
| 2 | Mock 返回非法响应 | 未知错误 | **8** |
| 3 | 真实服务器（Clash 代理） | 未知错误 | **1201** |
| 4 | `EVO_PASS_ACCEPT_ANY_AUTH=1` + 真实服务器 | 未知错误 | **1201** |
| 5 | `--accept-any-auth` | 未知错误 | **1201** |
| 6 | `--accept-any-auth --elevated` | 未知错误 | **1201** |
| 7 | `EVO_PASS_PRESERVE_INVALID_AUTH=1` | 未知错误 | **1201** |
| 8 | Mock(`scheats.club`→127.0.0.1) | 未知错误 | **8** |

**结论**：
- 错误码 `4 → 8 → 1201` 反映链路推进（DNS → TCP → 业务）
- `EVO_PASS_ACCEPT_ANY_AUTH` 只影响**本地 fixture 行为**，真实卡密校验链仍需上游 200 + 合法响应体
- 无有效卡密时，纯开关无法通过校验

---

## 7. 网络证据

### 7.1 授权服务器

```
freakluke.me  -> 172.67.190.7 / 104.21.73.124 (Cloudflare, DoH 实测)
scheats.club  -> 172.67.220.124 / 104.21.17.33 (Cloudflare)

本地代理环境下的解析: 198.18.1.130  <- Clash fake-IP 段 198.18.0.0/15
```

### 7.2 Mock 服务器捕获（原始）

```
[REQ 1] from 127.0.0.1:63592  total=463 head=81 body=378 cl=378
--- HEAD ---
POST /1 HTTP/1.1
connection: close
content-length: 378
host: freakluke.me:8880
--- BODY (hex) len=378 ---
7a010000 a0920800 17115c7a89250000 09cd9bd474d1756d...
```

---

## 8. 环境清理记录

**本次分析全程未产生持久化副作用**：

| 项目 | 状态 |
|---|---|
| `C:\Evo` | 未创建 |
| `C:\Evo\user.dat` | 未写入 |
| hosts | 分析期间临时添加过，**已还原** |
| 根证书 | 未植入（因上游校验失败提前退出） |
| `evo_pass.jsonl` | 未生成 |
| 文件签名/哈希 | 未修改（未 patch 任何二进制） |

分析用的提权脚本集中在 `C:\wz_evoc\`，产物在 `C:\wz_evoc\dumps\`、
日志在 `C:\wz_evoc\logs\`。
