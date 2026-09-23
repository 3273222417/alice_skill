# Evo 免卡密本地代理（evo.exe Themida 版）

沉淀自 2026-09-18 实测案例：`evo.exe`（34.2 MB，Themida 加壳 + WinLicense）
配合本地授权服务 + frida agent，绕过订阅校验进入功能界面。

---

## 一、结论先行：真正的门槛是「订阅响应结构体」

登录（`/user/authorize`）是**扁平 JSON**，很容易伪造。
真正卡住的是 `/v2/user/subscription/{product_id}`：客户端把响应解析进一个
**0x100 字节的结构体**，再做数值判定。**这个结构体的字段无法用扁平 JSON 键填充**——
实测 34 组 schema（含 69 键"厨房水槽"）全部失败。

### 判定链（运行时镜像 RVA）

| RVA | 作用 |
|---|---|
| `0x1469B0` | fetch（Themida VM 保护，静态不可读） |
| `0x144DA0` | 把响应结构体拷贝到 `Authorization+0xC0` |
| `0x1480A0` | 订阅有效性判定 |
| `0x144FC0` | 校验 + 日志（`Subscription Error [{status}]: {msg}`） |
| `0x177EDC` | UI 状态机（每帧调用，~300 次/秒） |

### 三个时间字段（关键）

订阅结构体 `sub`（即 `Authorization+0xC0`）：

| 偏移 | 含义 |
|---|---|
| `sub+0x40` | 激活时间 |
| `sub+0x48` | 过期时间 |
| `sub+0xe8` | 服务器当前时间 |

`0x1480A0` 反汇编（`0xE1F818` 是 integer 相减助手，返回 double）：

```
mov rdx,[rbx+0xe8]      ; server time
mov rcx,[rbx+0x48]      ; expiration
call 0xE1F818           ; d = exp - srv
comisd xmm0, 0
jbe  -> return 0        ; 必须 exp > srv
mov rdx,[rbx+0x40]      ; activation
mov rcx,[rbx+0xe8]
call 0xE1F818           ; d = srv - act
comisd xmm0, 0
jbe  -> return 0        ; 必须 srv > act
mov al,1
```

> **必须严格 激活 < 服务器时间 < 过期**，三者相等会因 `jbe` 失败。

`Authorization` 自身（`0x177EDC`）：

```
cmp  qword [rsi+0x180], 0xC8     ; HTTP 200
jne  fail
cmp  byte  [rsi+0x1b0], 0        ; has response
je   fail
mov  rcx, [rsi+0x108]            ; expiration
test rcx,rcx
jle  fail                        ; > 0
mov  rdx, [rsi+0x1a8]            ; server time
call 0xE1F818                    ; d = exp - srv
comisd xmm0, 0
jbe  fail                        ; 服务器时间 < 过期
```

| 偏移 | 含义 |
|---|---|
| `auth+0x100` | 激活时间 |
| `auth+0x108` | 过期时间 |
| `auth+0x180` | HTTP 状态码 |
| `auth+0x188` | 消息串（纯文本，与 `Bad Session` 等 memcmp 比对） |
| `auth+0x1a8` | 服务器时间 |
| `auth+0x1b0` | 是否有响应体（byte） |

---

## 二、方法学（本轮最大教训）

### 2.1 Trigger frida spawn 会被 Themida 察觉

`frida.spawn()` + resume：进程能起、script 能 load、hook 显示 installed，
**但客户端完全不发 HTTP 请求**（服务端日志 0 请求），UI 停在启动阶段。

**正确做法：attach 已运行进程。**

```python
ep = subprocess.Popen([EVO], cwd=WD, ...)     # 正常启动
# 等 "Logged In" 出现在 stdout
session = frida.attach(ep.pid)                 # 不是 spawn
session.create_script(src).load()
```

实测 Themida **对 attach 无感知**，hook 全部命中。

### 2.2 竞态：订阅请求在登录后 ~45ms 就发出

```
[19:03:45.348] Trying to log-in automatically
[19:03:45.388] Logged In, Welcome [admin]      <- +40ms
[19:03:45.42x] POST /v2/user/subscription/...  <- +45ms
```

手工 attach 永远慢一步（实测循环里 EVO 走 300+ 次 UI 判定时 hook 才装上，
但 `0x144DA0` 已经跑完了）。

**解法：在服务端给订阅响应加固定延迟，制造 attach 窗口。**

```python
SUB_RESPONSE_DELAY = float(os.environ.get("EVO_SUB_DELAY", "5"))
def sub_delay_for(path):
    if "subscription" in (path or "").lower() and SUB_RESPONSE_DELAY > 0:
        return SUB_RESPONSE_DELAY
    return 0.0
```

> ⚠️ **延迟上限 20 秒**：超过会触发客户端超时，错误串变成
> `Subscription Error [0]: Failed to get subscription data`（而非 `Invalid response from server`）。
> 这两档错误信号是很好的诊断依据：
> - `[0] Failed to get subscription data` → 请求超时 / 未收到响应
> - `[200] Invalid response from server` → 收到响应但结构不被接受

### 2.3 内存镜像必须用运行时 dump

Themida 在运行时解密字符串，**静态文件里这些串是加密的**。
必须用管理员权限 dump 运行时镜像，且 **RVA == 文件偏移**（ImageBase `0x140000000`）。

静态 vs live 差分出的 5 个运行时解密串：

| 地址 | 串 |
|---|---|
| `0x14267B750` | `Invalid response from server` |
| `0x142685390` | `/v2/user/subscription/` |
| `0x14268B740` | `Login Successful` |
| `0x14268DA80` | `/user/authorize` |
| `0x1426710B0` | `Welcome, ` |

字符串描述符布局（Themida）：`[4B flags][8B ptr][4B len]`，
描述符在 **ptr - 0x20** 处，且 `[desc] == ptr` 可用于确认。

### 2.4 好消息：Themida VM 保护会泄漏真实返回地址

`0x1469B0` 入口第 10 条指令是 `jmp 0x1435CED0F`（VM stub）。
**stub 尾部会 push 一个 imm32 = 真实返回点**：

```
0x1435CEE2B  mov qword ptr [rsp], 0x1469e8
0x1435CEE33  jmp 0x1428b7d6d
```

→ `0x1469E8` 就是 fetch 的真实主体地址（虽在 VM 保护区内不可读，但能精确定位边界）。

---

## 三、成品

| 文件 | 作用 |
|---|---|
| `loader/evo_free.js` | frida agent：补齐三时间字段 + 强制 `isValid` 放行 |
| `start_evofree.py` | 一键启动器（起服务 → 起 evo → 等登录 → attach 注入） |
| `server/evo_auth_server.py` | 本地授权服务（含 `SUB_RESPONSE_DELAY`） |

### 运行

```powershell
Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-Command',
  '& "C:\Program Files\Python310\python.exe" C:\...\evofree\start_evofree.py'
```

frida 需要手动加 sys.path（Python 3.10 下 `import frida` 会因 `typing.NotRequired` 失败）：

```python
# 用当前解释器即可 (v1.0.2 起不再写死 site-packages 路径)
import sys
sys.path.insert(0, "")   # 若 frida 装在别处, 这里换成对应的 site-packages
import frida
```

### 成功判据

evo stdout 出现：

```
[info] Current Version : 1.5.12
[info] Got valid subscription until 2036-09-15 19:04:03
```

且**窗口标题变成 `Evo Overlay`**（透明覆盖层 = 已进入功能界面）。

---

## 四、frida 写内存注意事项（踩坑）

frida 16.x 的 `writeU64` 要求 `uint64` 对象，传 JS number 会报
`TypeError: UInt64 object expected`。用：

```js
p.add(0x40).writePointer(ptr(t));           // 推荐
// 或
p.add(0x40).writeU64(uint64("1234567890"));
```

`Interceptor.attach` 的 `onEnter(args)` 里 **`args[0]` 不一定是 `this`**——
`0x177EDC` 的 `args[0]` 是垃圾，真正的对象在 `this.context.rsi`。
判定方法：看函数入口反汇编的第一条 `mov`，确认哪个寄存器承载 `this`。

---

## 五、边界（未达成）

- **纯服务端"零注入"方案未达成**：订阅结构体的三个时间字段本机不可解，
  fetch 内部只有 HTTP 头解析，`0x14CCA0`(JSON getkey) 在订阅路径 0 次调用。
  上游真实响应是 Themida 加密的嵌套/序列化结构。
- 当前成品**依赖 frida agent 常驻**（attach 在订阅请求返回前完成）。
- 若要彻底免注入，需要抓到一次**真实有效订阅**的原始响应体，逐字节复现。
