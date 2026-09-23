# VMProtect（VMP）加壳程序分析：抓包与脱壳

## 与普通壳的本质区别

VMP 是**虚拟化保护壳**，不是压缩壳：它把 x86/x64 指令编译为自定义字节码，由内置虚拟机解释执行。**虚拟化的函数永远无法还原成原始指令**——"脱壳"的目标是 dump 出非虚拟化的主体（可静态分析），虚拟化的关键函数走动态分析。Ultra 模式 = 虚拟化 + 变异（垃圾指令、等价替换）。

核心思想不变：**验证的输入输出都暴露在系统 API 边界，虚拟化够不到**。

## 专用工具

| 工具 | 用途 | 获取 |
|---|---|---|
| Detect It Easy | 识别 VMP 及版本 | github.com/horsicq/Detect-It-Easy |
| Wireshark | 底层抓包（依赖 Npcap） | wireshark.org |
| Fiddler / mitmproxy / HTTP Toolkit | HTTPS 解密代理 | telerik.com/fiddler、mitmproxy.org、httptoolkit.com |
| Proxifier | 强制不走系统代理的进程走代理 | proxifier.com（商业，有试用） |
| x64dbg | 主力动态调试 | x64dbg.com |
| Scylla | dump + IAT 重建修复 | github.com/NtQuery/Scylla |
| ScyllaHide | 反调试对抗（x64dbg 插件，必备） | github.com/x64dbg/ScyllaHide |
| Ghidra / IDA | dump 后静态分析 | 见 toolbox.md |
| NoVmp（进阶） | x64 VMP 字节码自动还原（基于 Triton，支持版本有限） | github.com/can1357/NoVmp |
| TCPView / Procmon | 连接与行为侦察 | learn.microsoft.com/sysinternals |

## 阶段 0：侦察

1. DIE 查壳：确认 VMP 及版本、保护选项（是否 import 保护、是否 Ultra）。
2. TCPView：程序运行时记录连接的域名 / IP / 端口——判断 HTTP(80) / HTTPS(443) / 自定义端口。
3. Procmon：文件、注册表行为画像（授权信息存哪）。

## 阶段 1：抓包（网络层取证）

1. **明文 HTTP**：Wireshark 捕获，`ip.addr == 目标IP` 过滤，右键 Follow TCP Stream 看完整请求响应。
2. **HTTPS**：Fiddler / mitmproxy 开系统代理 + 导入根证书到受信任存储。.NET / WinINet 程序走系统证书链，可直接解密。
3. **程序直连不走代理**（socket 程序常见）：Proxifier 加规则"目标 exe → 转发 127.0.0.1:8888"。
4. **证书校验（pinning）/ TLS 断连**：Frida hook 校验函数强制通过（.NET：`ServicePointManager.ServerCertificateValidationCallback`；WinHTTP：hook 证书验证回调）。
5. **自定义二进制协议**：Wireshark 只见密文没关系——Frida hook `WSASend`/`WSARecv`/`send`/`recv`，dump 加密前 / 解密后的明文 buffer。
6. VMP 特性：网络验证逻辑通常被虚拟化，静态不可见；hook 点选系统 API 层（WinHTTP / WinINet / socket）。

## 阶段 2：脱壳（dump 出可分析主体）

1. **反调试对抗先行**：x64dbg 附加前装好 ScyllaHide 并全选项开启（隐藏 PEB BeingDebugged、NtGlobalFlag、DR 寄存器、rdtsc 时间差）。VMP 内置多种检测，不隐藏大概率闪退。
2. **找 OEP**（VMP 入口是 VM stub，初始大段是虚拟机初始化，不要单步硬跟）：
   - API 断点法：对 `GetModuleHandleW` / `GetCommandLineW` 下断（程序初始化必调），命中后返回地址附近即真实入口区；
   - 区段执行法：程序跑起来后 RIP 首次落入原始代码节（.text）处。
3. **Dump**：Scylla 附加进程 → Dump 保存内存镜像。
4. **IAT 重建**：Scylla 的 IAT Autosearch + Get Imports。VMP import 保护把调用替换成间接 stub——老版本（2.x 早期）基本可恢复；新版本部分调用走 VM 内部，搜不全属正常，残留手工处理或接受。
5. **Fix Dump**：Scylla 修复 → 得到可打开的 PE。
6. 若 PE 头被抹（EraseHeader）：Scylla 重建 PE 头。

## 阶段 3：虚拟化代码应对（务实路线）

1. dump 文件用 Ghidra / IDA 静态分析非虚拟化部分（界面、存储、注册表、辅助逻辑）。
2. 虚拟化函数表现为跳进 VM handler 的间接块——**不硬啃**。
3. 正解 = 回到主 skill 的运行时绕过路线：
   - 网络验证 → 抓包 + hook 网络响应；
   - 本地比较 → hook 比较所用 API / 内存 patch 结果（反插桩三原则：只挂确认的函数、改返回值不改参数、被检测退回观测模式）。
4. 进阶（成本高）：trace VM handler 执行序列做模式识别；x64 用 NoVmp 自动还原（仅部分版本支持）。

## 问题速查

| 现象 | 原因 | 对策 |
|---|---|---|
| 一调试就闪退 | VMP 反调试（PEB / DR / rdtsc / CheckRemoteDebuggerPresent） | ScyllaHide 全开；内核级用 TitanHide；换 Frida 绕部分检测 |
| dump 文件打不开 | PE 头被抹 / IAT 修复失败 | Scylla 重建 PE 头；提高 IAT 搜索级别 |
| IAT 搜不全 | import 虚拟化，调用走 VM 内 stub | 无法自动恢复，转纯动态 / hook 分析 |
| HTTPS 全密文或断连 | cert pinning | Frida hook 校验回调强制通过 |
| 程序不走代理 | socket 直连 | Proxifier 进程级强制转发 |
| 抓包是乱码 | 自定义加密协议 | API 层 hook send/recv 拿明文 buffer |
| 找不到 OEP | 入口虚拟化 | API 断点法 / 区段执行法；或放弃 OEP，运行期直接分析 |
| 改内存后程序自杀 | CRC 自校验 | 不改代码段，只 hook / 改返回值 |
| 工具不识别新版本 VMP | NoVmp 等仅支持旧版 | 纯动态 + API 边界分析 |

## 推荐执行顺序

DIE 查壳 → TCPView / Procmon 侦察 → Wireshark 抓明文 → Fiddler + 证书解 HTTPS → Proxifier 兜底 → Frida 拿自定义协议明文 → x64dbg + ScyllaHide → API 断点找 OEP → Scylla dump + IAT → Ghidra 分析 → 关键验证走 API 边界 hook
