# 卡密破解工具箱（按路线分组）

配合"方法路线总览"使用：先定路线，再取工具。所有工具均为绿色/免费优先，商业工具仅在免费替代不足时列出。

## 环境底座（所有路线共用，第 0 步必装）

| 工具 | 用途 | 获取/安装 |
|---|---|---|
| Python 3 | 脚本平台：内存扫描、机器码复现、keygen、打包分发 | python.org |
| pefile | PE 文件头/节区/overlay 解析 | `pip install pefile` |
| capstone | 反汇编引擎（脚本化静态分析） | `pip install capstone` |
| frida + frida-tools | 动态插桩（路线四核心） | `pip install frida-tools`（下载慢，最先启动后台安装） |

一键安装：`pip install pefile capstone frida-tools`

## 路线一：静态逆向

| 工具 | 用途 | 费用/获取 |
|---|---|---|
| Ghidra | 原生程序反编译（IDA 的免费替代） | 免费开源，github.com/NationalSecurityAgency/ghidra |
| IDA Pro | 商业反编译标准（有免费 IDA Free） | 商业，hex-rays.com |
| dnSpy / ILSpy | .NET 反编译看源码，可改 IL 存回 | 免费开源，github.com/dnSpyEx/dnSpy、github.com/icsharpcode/ILSpy |
| Detect It Easy (DIE) | 查壳判架构（MPRESS/UPX 一眼识别） | 免费开源，github.com/horsicq/Detect-It-Easy |
| HxD | 十六进制编辑与比对 | 免费，mh-nexus.de/hxd |

## 路线二：脱壳与解包

| 工具 | 用途 | 费用/获取 |
|---|---|---|
| UPX | `upx -d` 一键脱 UPX 壳 | 免费开源，upx.github.io |
| x64dbg | 动态调试脱壳主力 | 免费开源，x64dbg.com |
| CFF Explorer | PE 节区/overlay 深入解析 | 免费，ntcore.com |

## 路线三：算法推导

| 工具 | 用途 | 费用/获取 |
|---|---|---|
| CyberChef | 编码解码/哈希/格式转换瑞士军刀 | 免费网页版，gchq.github.io/CyberChef |
| WMI | 取 CPU/磁盘/MAC 序列号复现机器码 | 系统自带 |
| Python hashlib/hmac | HMAC 暴力排除、算法验证 | Python 标准库 |

## 路线四：运行时绕过

| 工具 | 用途 | 费用/获取 |
|---|---|---|
| Frida | spawn 注入 + 过滤式验签 hook | 免费开源，frida.re |
| Process Hacker | 进程内存查看/字符串搜索/转储 | 免费开源，github.com/winsiderss/systeminformer |
| API Monitor | 只读观测 bcrypt/ncrypt 加密调用 | 免费，rohitab.com/apimonitor |

## 可选补充（联网验证 / 内存搜索场景）

| 工具 | 用途 | 费用/获取 |
|---|---|---|
| Cheat Engine | 内存搜索计数器/标志位 | 免费，cheatengine.org |
| Wireshark | 联网激活时抓包分析协议 | 免费开源，wireshark.org |
| Fiddler / mitmproxy | HTTPS 抓包 | 免费，telerik.com/fiddler、mitmproxy.org |

## 最小启动集

够跑通 90% 流程的 7 件套：**Python（+pefile、capstone、frida-tools）、Ghidra、dnSpy、x64dbg、Detect It Easy**。其余按实际阻力再补。

## 本机环境检查（每次开工前）

1. Python 库：`python -c "import pefile, capstone, frida"` 报 ModuleNotFoundError 即缺
2. 外部工具不在 PATH 属正常（绿色解压即用）：用 PowerShell `Get-ChildItem "C:\Program Files","C:\Program Files (x86)"` 扫一遍确认
3. 本机 bash 环境的 coreutils 可能损坏（dirname/head/ls 找不到）——列目录、检查文件一律走 PowerShell，不要依赖 bash
4. 绿色免安装目录建议：`C:\tools\<工具名>`，统一管理不污染系统
