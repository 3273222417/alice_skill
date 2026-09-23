# 隔离环境操作手册

> 全部命令在**虚拟机内的管理员 PowerShell** 中执行。宿主机侧只用 VM 管理器的快照功能（GUI 或 `vmrun` / `VBoxManage`）。

## 一、宿主机侧：快照（VMware / VirtualBox）

```powershell
# VMware Workstation（vmrun 位于安装目录）
& "C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe" -T ws snapshot "D:\VMs\re-lab\re-lab.vmx" "00-clean"
& "C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe" -T ws listSnapshots "D:\VMs\re-lab\re-lab.vmx"
& "C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe" -T ws revertToSnapshot "D:\VMs\re-lab\re-lab.vmx" "00-clean"

# VirtualBox
& "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" snapshot "re-lab" take "00-clean"
& "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" snapshot "re-lab" list
& "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" snapshot "re-lab" restore "00-clean"
```

**规则**：`revertToSnapshot` / `restore` 是不可逆的，回滚前确认当前分支没有需要保留的进度；需要保留就先打新快照。

## 二、虚拟机内：基线检查与固化

```powershell
# 1. 记录基线（写入 env.md）
[System.Environment]::OSVersion.VersionString
(Get-CimInstance Win32_OperatingSystem).Caption
$env:PROCESSOR_ARCHITECTURE

# 2. 关自动更新（避免快照内状态漂移）
Set-Service -Name wuauserv  -StartupType Disabled
Set-Service -Name bits      -StartupType Disabled

# 3. 关休眠与页面文件压缩（可选，加快快照）
powercfg -h off

# 4. 关闭共享与剪贴板（VMware 用 .vmx 手工改，VirtualBox 用下面的命令）
& "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" modifyvm "re-lab" --clipboard disabled --draganddrop disabled
```

VMware 的 `.vmx` 里加/改：

```
isolation.tools.copy.disable    = "TRUE"
isolation.tools.paste.disable   = "TRUE"
isolation.tools.dnd.disable     = "TRUE"
sharedFolder.maxNum             = "0"
```

## 三、网络策略

```powershell
# 查当前网卡与网关（确认是否真的隔离）
Get-NetIPConfiguration | Select-Object InterfaceAlias, IPv4Address, IPv4DefaultGateway

# 断网最快做法：禁用网卡（用完再启用）
Get-NetAdapter | Disable-NetAdapter -Confirm:$false
Get-NetAdapter | Enable-NetAdapter  -Confirm:$false

# 抓包阶段：启用网卡 + 系统代理指向宿主机 Fiddler/mitmproxy
netsh winhttp set proxy 127.0.0.1:8888        # 或宿主机 IP
netsh winhttp reset proxy                     # 用完还原
```

网络模式选择：

| 模式 | 用途 | 风险 |
|---|---|---|
| 无网络 / host-only | 默认分析态 | 无 |
| NAT | 需要出网抓包 | 样本可外传 |
| 桥接 | 需要同网段设备 | 暴露到真实内网，慎用 |

## 四、时间控制

```powershell
# 关 VM tools 时间同步（VMware）
& "C:\Program Files\VMware\VMware Tools\VMwareToolboxCmd.exe" timesync disable

# VirtualBox
& "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" setextradata "re-lab" "VBoxInternal/Devices/VMMDev/0/Config/GetHostTimeDisabled" 1

# 关 Windows 时间服务（双保险，改完日期再启用）
Stop-Service w32time; Set-Service w32time -StartupType Disabled
Set-Date -Date "2027-01-15 10:00:00"     # 改到未来测时间锁
Get-Date                                  # 确认未被同步回去
```

**顺序**：先断网 → 再关时间同步 → 最后改日期。三者缺一，日期会被改回。

## 五、驱动签名与 Secure Boot

```powershell
# 查 Secure Boot 状态
Confirm-SecureBootUEFI

# 开启测试签名（需重启）
bcdedit /set testsigning on
bcdedit /set nointegritychecks on     # 老版本系统可能需要
shutdown /r /t 0

# 验证测试签名已生效（桌面右下角出现"测试模式"水印）
bcdedit /enum "{current}" | Select-String "testsigning"

# 关闭（分析完成后）
bcdedit /set testsigning off
```

**驱动加载验证**（每次换 OS 版本都做一次）：

```powershell
sc create TitanHide binPath= "C:\tools\TitanHide\TitanHide.sys" type= kernel start= demand
sc start TitanHide
# 失败先看错误码：
#   577 = 未签名 / 测试签名未开
#   31  = 驱动与系统不兼容（版本偏移不对）
sc query TitanHide
sc stop TitanHide; sc delete TitanHide
```

优先级：**ScyllaHide 用户模式 → 不够再上内核驱动**。内核驱动一崩就是 BSOD，且可能与目标程序的反调试正面冲突。

## 六、符号环境

```powershell
# 当前会话
$env:_NT_SYMBOL_PATH = "srv*C:\Symbols*https://msdl.microsoft.com/download/symbols"

# 永久生效
[Environment]::SetEnvironmentVariable("_NT_SYMBOL_PATH",
  "srv*C:\Symbols*https://msdl.microsoft.com/download/symbols", "Machine")

# 验证（x64dbg / WinDbg 里应能看到系统模块符号已加载）
Test-Path C:\Symbols
```

## 七、反虚拟机 / 反沙箱检测排查清单

跑样本前逐项确认（有任意一项被检测 → 后续结论可能失真）：

| 检测面 | 检查方法 | 伪装手段 |
|---|---|---|
| 设备名 / 磁盘名 | 设备管理器看磁盘与 CD-ROM 型号 | `.vmx` 改 `disk.EnableUUID`、改产品名 |
| MAC 前缀 | `Get-NetAdapter \| Select MacAddress` | 手工改 MAC 为非 VM OUI |
| CPUID hypervisor 位 | 跑 CPUID 检测工具 | `.vmx` 加 `hypervisor.cpuid.v0 = "FALSE"` |
| BIOS / 主板串 | `Get-CimInstance Win32_BIOS` | `.vmx` 改 `bios440.filename` 或填 SMBIOS 串 |
| 进程 / 服务名 | 任务管理器看 `vmtoolsd`/`VBoxTray` | 无法完全隐藏 → 考虑真机隔离分区 |
| 鼠标 / 用户活动 | 长时间无输入判定为沙箱 | 手工移动鼠标 |

VMware `.vmx` 常用加硬项：

```
hypervisor.cpuid.v0 = "FALSE"
board-id.reflectHost = "TRUE"
isolation.tools.getPtrLocation.disable = "TRUE"
isolation.tools.setPtrLocation.disable = "TRUE"
isolation.tools.getVersion.disable     = "TRUE"
monitor_control.disable_directexec     = "TRUE"
monitor_control.disable_chksimd        = "TRUE"
monitor_control.disable_ntreloc        = "TRUE"
monitor_control.disable_selfmod        = "TRUE"
monitor_control.disable_reloc          = "TRUE"
monitor_control.disable_btinout        = "TRUE"
monitor_control.disable_btmemspace     = "TRUE"
monitor_control.disable_btpriv         = "TRUE"
monitor_control.disable_btseg          = "TRUE"
```

## 八、开工前检查清单

- [ ] `00-clean` / `01-tools` 快照已存在且可回滚
- [ ] 网络处于 host-only 或无网络
- [ ] 共享文件夹与剪贴板已关闭
- [ ] 时间同步已关闭（若需改日期）
- [ ] 测试签名状态与内核驱动需求匹配（若需内核驱动）
- [ ] `_NT_SYMBOL_PATH` 已设置且 `C:\Symbols` 可写
- [ ] `env.md` 已记录以上全部信息
