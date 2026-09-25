# 环境与工具链坑位详解（gotchas）

> 来源：2026-09-18 `Evo_Crack.exe` 实战中**真实踩过**的坑，全部有现场证据。
> 每条格式：【症状】【根因】【解法】【验证方法】。

---

## 1. Frida 17 移除了 `Module.getExportByName()`

**症状**：Frida 脚本 `load()` 成功、无任何报错，但 **0 个钩子事件**。
只打印出模块列表，看起来"程序什么都没做"。

**根因**：Frida 17 起 `Module` 变成实例级 API：

| 旧（16 及以前） | 新（17+） |
|---|---|
| `Module.getExportByName(null, "f")` | `Module.getGlobalExportByName("f")` |
| `Module.getExportByName("k32", "f")` | `Process.getModuleByName("k32").getExportByName("f")` |
| `Module.findExportByName(null, "f")` | `Module.findGlobalExportByName("f")` |

旧写法在 17 里要么抛异常（被 `try{}catch{}` 吞掉），要么返回 `null`，
于是 `Interceptor.attach(null, ...)` 静默跳过 ——
**这是本案例首两轮"零行为事件"的唯一根因。**

**解法**：统一走自愈式解析器，失败返回 `null` 并打日志：

```js
function resolveExport(modName, expName) {
  if (modName) {
    try {
      const m = Process.getModuleByName(modName);
      const p = m.getExportByName(expName);
      if (p && !p.isNull()) return p;
    } catch (e) { log("miss " + modName + "!" + expName + ": " + e.message); }
  }
  try {
    const p2 = Module.getGlobalExportByName(expName);
    if (p2 && !p2.isNull()) return p2;
  } catch (e) { log("miss *!" + expName + ": " + e.message); }
  return null;
}
```

**验证方法**：脚本启动时先 `resolveExport("kernel32.dll", "CreateFileW")`，
拿不到就立刻 `throw` 而不是静默继续。宁可炸，不要哑。

---

## 2. `dev.spawn()` 缺 `stdio="pipe"` 导致喂不进 stdin

**症状**：进程正常起来，钩子也装上了，但**永远停在「请输入卡密: 」**。
`dev.input(pid, b"...")` 调用不报错却毫无效果。

**根因**：Frida 默认 spawn 走进程自己的控制台，stdin 是**真实控制台句柄**，
不是 Frida 的管道。`dev.input()` 只能写进 Frida 托管的标准流。

**解法**：

```python
pid = dev.spawn([EXE], cwd=CWD, stdio="pipe", env={...})   # stdio="pipe" 不能省
session = dev.attach(pid)
script.load()
dev.resume(pid)
time.sleep(4.0)                       # 等它打印提示、进入 getchar/ReadConsoleW
dev.input(pid, b"EVO-TESTKEY-0001-AAAA-BBBB\r\n")
```

**注意**：`\r\n` 两个都要（`ReadConsoleW` 等回车）；纯 `\n` 有时不触发。
`time.sleep` 也不能省 —— 抢在提示输出前喂输入会丢。

---
## 3. 中文路径 + Windows PowerShell 5.1 = 乱码

**症状**：

```
F:\alice破甲\resources\...   ->  实际收到 F:\alice鐮寸敳\resources\...
```

**根因**：powershell.exe 5.1 在非 UTF-8 活动代码页下按 ACP(936) 解读脚本内的中文。

**解法**：

1. 提权/调度脚本放纯 ASCII 路径。
2. .cmd 用 GBK(936) 保存，.ps1 用 UTF-8 BOM 保存。
3. 脚本内不要内联中文。
1. **所有提权/调度脚本放纯 ASCII 路径**（本案例专用 C:\alice_evoc\）。
2. **.cmd / .bat 用 GBK(936) 保存**，.ps1 用 **UTF-8 with BOM** 保存。
3. 脚本内**不要内联中文**；需要中文就 chcp 65001，或干脆全英文。

```powershell
$gbk = [System.Text.Encoding]::GetEncoding(936)
[System.IO.File]::WriteAllText($path, $text, $gbk)
[System.IO.File]::WriteAllText($path, $text, (New-Object System.Text.UTF8Encoding $true))
```

**验证方法**：Get-Content C:\alice_evoc\scripts\boot.cmd 看中文是否正常。

> 顺带：PATH 里可能没有 powershell，用绝对路径
> `$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe`。

---
## 4. 提权：schtasks 路线最可靠

**症状**：

- 非提权 Start-Process 报「请求的操作需要提升」
- frida.spawn 非提权报 NotSupportedError: 0x2e4
- 直接 schtasks /create（非提权）报「错误: 拒绝访问。」
- Start-Process -Verb RunAs 跑长任务：调用者会话一断，子进程跟着死

**根因**：目标 manifest 是 requireAdministrator；且 RunAs 出来的进程生命周期
绑定在调用链上，长跑任务会被连带杀掉。

**解法（三段式）**：

boot.cmd 只做两件事：用 /rl HIGHEST 创建一次性计划任务，然后 /run 触发它。
任务体是一个普通 .cmd（本案例 run.cmd），里面 set 好环境变量再拉起要分析的程序。

**关键点**：任务体跑在 HIGHEST 上下文，且**完全脱离调用者会话** ——
PowerShell 被中断、Codex 轮次被截断，任务照样跑完。

**清理**（务必做）：

```bat
schtasks /delete /tn ALICE_Run /f
```

**环境旁证**：本案例机器 EnableLUA=1 + ConsentPromptBehaviorAdmin=0 +
PromptOnSecureDesktop=0，管理员组用户**静默提权**，无 UAC 弹窗。

---

## 5. Frida RPC 导出名不要带下划线

**症状**：报 `Error: unable to find method 'dumpRange'`，
但 JS 侧明明写的是 rpc.exports = { dumpRange: ... }。

**根因**：script.exports_sync 会把 RPC 名做 snake_case 与 camelCase 自动转换。
写 dump_range 就必须调 dumpRange；两边风格不一致时互相找不到。

**解法**：RPC 名**全用无下划线的小写单词**，两边写法完全一致：

```js
rpc.exports = { dumprange, saverange, findkey, ctxdump, modules, ranges, gatedump, release };
```

```python
script.exports_sync.dumprange(addr, size)
```

---
## 6. exit gate 冻结进程后脚本被销毁，dump 不能走 RPC

**症状**：用 ExitProcess 钩子做"出口闸门"，`while (!released) Thread.sleep(0.1);`
冻结进程后，Python 侧任何 script.exports_sync.* 都报 `script has been destroyed`。

**根因**：目标进程被卡死时，Frida RPC 通道心跳超时，agent 被回收。

**解法**：**dump 必须在 JS 侧完成落盘**，不要回 Python 取数据：

```js
function gatedump() {
  const out = [];
  Process.enumerateModules().forEach(m => {
    out.push({ name: m.name, base: m.base.toString(), size: m.size });
    try {
      // v1.0.2: hook_agent.js 已内置多候选探测, 直接调用 saveRange 即可
const r = saveRange("mod_" + m.name + ".bin", m.base, m.size);
// 若自己写脚本, 把目录换成本机可写路径 (别再写死 C:\alice_evoc)
const DUMPDIR = "<可写目录>\\dumps\\";
const f = new File(DUMPDIR + "mod_" + m.name + ".bin", "wb");
      f.write(m.base.readByteArray(Math.min(m.size, 0x6000000)));
      f.flush(); f.close();
    } catch (e) { log("dump fail " + m.name + ": " + e.message); }
  });
  new File(GATE_JSON, "w").write(JSON.stringify(out, null, 2));
  while (!released) Thread.sleep(0.1);   // 落盘完成后再冻结
}
```

**注意**：Process.getModuleByName 只用来取 base/size，
`base.readByteArray(size)` 才拿到运行时（已解包）内容 ——
**静态文件读不到的东西全在这里**。

---

## 7. dump 之后：GBK 与 UTF-16LE 都要搜

**症状**：静态文件搜「卡密」0 命中、搜 EVO 0 命中，
误判"这程序没有中文 / 没有明文字符串"。

**根因**：

- 加壳程序明文只在**运行时内存**里，静态文件全被加密；
- 中文 Windows 程序有两种常见编码：**GBK(936)** 和 **UTF-16LE**；
- 本案例 Evo_Crack.exe 静态文件 **0 条 UTF-16 串**，
  但内存 dump 出来的是 **UTF-16LE**（`请输入卡密: `）。

**解法**：三种编码全试，注意 **UTF-16LE 需 2 字节对齐**：

```python
d = open(dump, "rb").read()
for enc, name in (("gbk", "GBK"), ("utf-16le", "UTF-16LE"), ("utf-8", "UTF-8")):
    print(name, d.count("卡密".encode(enc)))
```

**关键判据**：UTF-16LE 里 卡 = U+5361 -> 字节 61 53；密 = U+5BC6 -> C6 5B。
看到 61 53 C6 5B 就是「卡密」。

**教训**：搜不到不等于没有，只代表**编码没试全**或**没 dump**。

---
## 8. Clash / 代理的 fake-IP 段会骗你

**症状**：DNS 解析 scheats.club 得到 198.18.1.130，
抓包显示 TCP 能连但**永远没有 HTTP 响应**，看起来"服务器挂了"。

**根因**：198.18.0.0/15 是 **Clash fake-IP 默认段**。
代理接管 DNS 后返回假 IP，由 Clash 内核按域名转发；
绕过代理直连这个 IP 当然不通。同理 hosts 劫持 + 代理同时存在时，
**代理可能抢先接管**，mock 服务器收不到包。

**解法**：

1. 用 **DoH** 绕过本地 DNS 拿真实 IP：
   https://1.1.1.1/dns-query?name=freakluke.me&type=A
   本案例真值：freakluke.me -> 172.67.190.7 / 104.21.73.124（Cloudflare）
   scheats.club -> 172.67.220.124 / 104.21.17.33
2. 做本地化绕过实验时**先关代理**，或确认代理进程未运行。
3. IP 落在 198.18.0.0/15 或 198.19.0.0/15 就直接判定"被代理接管"。

---

## 9. hosts 劫持必须还原

**症状**：分析做完忘了还原，之后该机器访问 scheats.club 一直失败或被本地劫持。

**解法**：**先备份再改，用 try/finally 包住**：

```python
import shutil, os, subprocess
HOSTS = os.path.join(os.environ["WINDIR"], "System32", "drivers", "etc", "hosts")
bak = HOSTS + ".bak_wz"
shutil.copy2(HOSTS, bak)
try:
    with open(HOSTS, "a", encoding="utf-8") as f:
        f.write("\n127.0.0.1 scheats.club\n")
    subprocess.run("ipconfig /flushdns", shell=True, capture_output=True)
    # ... 跑分析 ...
finally:
    shutil.copy2(bak, HOSTS)
    subprocess.run("ipconfig /flushdns", shell=True, capture_output=True)
```

**验证**：Select-String -Path hosts -Pattern "scheats|freakluke" 应无输出。
**本案例状态**：脚本已自动还原，确认无残留（见 evo-case.md 第 8 节）。

---

## 10. 不要直接 patch 主程序 exe

**症状**：在 evo.exe 上找 jz/jnz 想改跳转，改完启动直接崩或无反应。

**根因**：evo.exe 是 **Themida / WinLicense**：

- .themida 段 RAW=0（运行时才展开）；
- .boot 段熵 7.949（虚拟机字节码）；
- 有 CRC 自校验 + 反调试。

改静态文件 -> CRC 失败 -> 进程自杀。就算过了 CRC，逻辑也全在 VM 里，
改 native 跳转没用。

**正确路线**：**不碰二进制，改环境** ——
Evo_Crack.exe 的思路就是把授权服务端搬到本地：
hosts 劫持 + 根证书植入 + 本地 TLS 443 + 伪造授权响应 + 写 C:\Evo\user.dat。
**改数据流，不改代码流。**

---
## 11. 其它零碎但致命的点

| # | 坑 | 症状 | 解法 |
|---|---|---|---|
| 11.1 | 段名含方括号 | pefile 正常但自写解析器截断 | 段名 8 字节补零，rstrip 后 decode latin1 |
| 11.2 | 静态段熵 = 0.000 | 误以为"空段" | RAW=0 / RS=0 是**运行时填充**，不是空；dump 后才有内容 |
| 11.3 | 导入表每 DLL 只 1 个 | 误以为"程序很简单" | 壳抹掉了 IAT，运行时 LoadLibrary + GetProcAddress 重建 |
| 11.4 | bind 443 失败 | bind/listen 127.0.0.1:443 failed | 端口被占或未提权；先 netstat -ano 查 :443 |
| 11.5 | mock 服务器非提权起不来 | PermissionError | 8880 需提权绑定；或用 hosts + 用户态端口映射 |
| 11.6 | 提权上下文里环境变量丢失 | 开关不生效 | schtasks 的 /tr 里不能直接带 env；改在 run.cmd 内 set VAR=1 |
| 11.7 | evo_pass.jsonl 找不到 | 不知道程序写哪了 | 相对路径落在**进程 CWD**；先 hook CreateFileW 看绝对路径 |
| 11.8 | 错误码卡在 1201 | 以为绕过失败 | 1201 = "服务器响应但业务拒绝"，说明链路已通到业务层，是**进展**不是失败 |
| 11.9 | UTF-16 扫描错位 | 一片乱码 | 从**偶地址**对齐开始扫，或两个偏移都试 |
| 11.10 | 混用 cmd 与 PowerShell 删文件 | 删错或删不掉 | 统一一个 shell；PowerShell 用 Remove-Item -LiteralPath |

---

## 12. 快速自检清单（每次开工前跑一遍）

```powershell
# 1. 提权上下文是否可用（找到 High Mandatory Level 即已提权）
whoami /groups | findstr /i "S-1-16-12288"

# 2. 目标 manifest：pe_recon.py 输出里找 requireAdministrator

# 3. 端口占用
netstat -ano | findstr ":443 :8880"

# 4. 代理是否在跑（会干扰 DNS / hosts）
Get-Process | Where-Object { $_.ProcessName -match "clash|verge|v2ray|sing-box" }

# 5. hosts 是否干净
Select-String -Path "$env:WINDIR\System32\drivers\etc\hosts" -Pattern "scheats|freakluke"
```

**另**：分析前先做环境基线快照（hosts / Run 键 / 服务 / 驱动 / 计划任务 / 文件 hash），
分析后逐项比对，确认无残留改动。本案例脚本见 `evo-case.md` 第 8 节。

---

## 13. 工具版本记录（本案例实测可用）

| 工具 | 版本 | 备注 |
|---|---|---|
| Python | 3.13.15 | AppData\Local\Programs\Python\Python313\python.exe |
| frida | 17.18.0 | **API 与 16 及以前不兼容，见第 1 条** |
| pefile | 2024.8.26 | 段解析正常 |
| capstone | 5.0.9 | 反汇编 |
| pywin32 | 312 | 提权 / token 检查 |
| psutil | 7.2.2 | 进程枚举 |
| pycryptodome | - | AES 复现 |
| keystone | - | 汇编 |
| Windows PowerShell | 5.1 | **中文路径坑，见第 3 条** |
| Git | C:\Program Files\Git\cmd\git.exe | 不在 PATH 里，用绝对路径 |