# 环境清理与还原（分析完成后必做）

> 本案例（2026-09-18）分析结束时已执行的还原动作。**下次分析完请照此逐项检查。**

---

## 1. 计划任务（提权脚手架遗留）

分析期间用 `schtasks` 建的一次性任务，**必须删**：

```bat
schtasks /delete /tn WZ_Run /f
schtasks /delete /tn WZ_E5 /f
schtasks /delete /tn WZ_E6 /f
schtasks /delete /tn WZ_E7 /f
schtasks /delete /tn WZ_CB /f
schtasks /delete /tn WZ_M2 /f
```

核对：

```powershell
schtasks /query /fo LIST | Select-String "WZ_"
```

**本案例状态**：全部已删除（2026-09-18 实测）。

> 实测遗留任务名：`WZ_CB` `WZ_E5` `WZ_E6` `WZ_E7` `WZ_EvocRun` `WZ_EvocRun4` `WZ_M2`
> 非提权 `schtasks /delete` 会报 `Access is denied`，**必须提权删**（RunAs 一个纯 ASCII 路径的 .cmd）。

---

## 2. hosts 还原

`Evo_Crack.exe` 自身会改写 hosts。分析时若手工劫持，**务必还原**：

```powershell
Select-String -Path "$env:WINDIR\System32\drivers\etc\hosts" -Pattern "scheats|freakluke"
ipconfig /flushdns
```

**本案例状态**：脚本自动还原，确认无残留。

---

## 3. 根证书（若被植入）

`Evo_Crack.exe` 会把自己内嵌的 CER 装进 **local-machine ROOT store**。
分析中若真的跑到了这一步，检查并清理：

```powershell
Get-ChildItem Cert:\LocalMachine\Root | Where-Object { $_.Subject -notmatch "Microsoft|VeriSign|DigiCert|GlobalSign|Sectigo|Baltimore|COMODO|USERTrust|Entrust|Go Daddy|Starfield|thawte|SecureTrust|AddTrust|Certum|QuoVadis|SwissSign|T-TeleSec|XRamp|AffirmTrust|Network Solutions|Symantec|GeoTrust|Equifax|VISA|AC Camerfirma|Buypass|D-TRUST|Disig|Firmaprofesional|Hongkong Post|Izenpe|Microsec|OISTE|PSCProcert|SECOM|Sonera|Staat der|TeliaSonera|TUBITAK|Unizeto|WISeKey|ANF|China|CFCA|GDCA|WoSign" } |
  Select-Object Subject, Thumbprint, NotAfter
```

删除可疑项：

```powershell
Remove-Item -LiteralPath "Cert:\LocalMachine\Root\<Thumbprint>"
```

**本案例状态**：证书**未植入**（进程在证书步骤前就退出了），无需清理。

---

## 4. 授权文件

```powershell
Test-Path C:\Evo\user.dat
Get-ChildItem C:\Evo -ErrorAction SilentlyContinue
```

**本案例状态**：`C:\Evo` **从未创建**，`evo_pass.jsonl` **未生成**。

---

## 5. 提权脚本区

```
C:\wz_evoc\           本次分析的提权脚本 + 日志 + dump 存放处
                      (v1.0.2 起脚本改为相对自身定位, 这个目录只在本案例里出现)
```

分析结束后可整目录删除（**先确认 dump 已备份**）：

```powershell
# 确认路径后执行
Remove-Item -LiteralPath "C:\wz_evoc" -Recurse -Force

# ---- v1.0.2: 启动器自带的精确还原 (推荐, 不会误删) ----
#   EvoFree.exe --cleanup    按 evofree.state.json 精确删除本次改动
#   EvoFree.exe --restore    额外清掉残留的 OpenSSL 信任目录
# 状态文件 evofree.state.json 记录: hosts_added / certs_added / ssl_files
```

**本案例状态**：**保留**（dump 与日志作为证据留档），用户可自行删除。

---

## 6. 环境基线比对（推荐流程）

分析**开始前**做基线快照，结束后逐项 diff：

| 项 | 采集命令 |
|---|---|
| hosts | `copy hosts hosts.bak` |
| 服务 | `Get-Service \| Export-Csv services.csv` |
| 驱动 | `driverquery /v /fo csv > drivers.csv` |
| 计划任务 | `schtasks /query /fo csv /v > schedtasks.csv` |
| Run 键 | `reg query HKLM\...\Run` |
| 文件 hash | `Get-FileHash * -Algorithm SHA256` |
| 进程 | `Get-Process \| Export-Csv procs.csv` |
| 网络 | `netstat -anob > netstat.txt` |

本案例基线：`work/evoc-crack2/env/baseline_20260918_160739/`（282 项文件 hash + 8 类系统状态）。

---

## 7. 分析完的检查清单

- [ ] `schtasks` 无 `WZ_*` 残留
- [ ] hosts 无 `scheats` / `freakluke` 条目
- [ ] 根证书无异常自签项
- [ ] `C:\Evo` 不存在（或已清理）
- [ ] 无 `EVO_PASS_*` 环境变量残留（`Get-ChildItem Env:EVO*`）
- [ ] `evo.exe` / `Evo_Crack.exe` 进程已退出
- [ ] mock 服务器进程已关闭
- [ ] 基线 diff 无意外差异
