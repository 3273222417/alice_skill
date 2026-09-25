# dma-cardkey-evo-crack  v1.0.2

DMA 硬件外挂（Evo / EVO PASS / scheats.club 系）卡密授权链的完整逆向与本地化绕过工作流。

> 本包是 **v1.0.1 的可用性修复版**。修复清单见 `SKILL.md` 的「十一、变更记录」。
> 核心变化：`--dry-run` 变成真正零副作用的自检模式，`--cleanup` 变成精确还原。

---

## 一、快速上手

### 只想自检（不碰系统）

```powershell
python scripts\evofree\evofree_main.py --dry-run --ports 18880
```

只起内嵌授权服务并打三个端点，**不改 hosts / 不装证书 / 不拉 evo**。
看到 `dry-run OK` 就说明环境没问题。

### 完整跑一遍

```powershell
python scripts\evofree\evofree_main.py --evo "D:\evoc\evo.exe"
```

流程：UAC 提权 → hosts 劫持 → 装根证书 → 起服务(443/8880/80) → 拉 evo → attach 注入 agent。

### 还原现场

```powershell
python scripts\evofree\evofree_main.py --cleanup    # 按状态文件精确还原
python scripts\evofree\evofree_main.py --restore    # 额外清残留 OpenSSL 目录
```

---

## 二、命令行速查

```text
--dry-run         零副作用自检 (只起服务)
--cleanup         精确还原 hosts / 证书 / OpenSSL 目录
--restore         彻底还原 (含残留目录兜底)
--evo <path>      指定 evo.exe
--server-only     只起服务
--no-elevate      不自动提权
--ports a,b,c     自定义端口 (默认 443,8880,80)
--force-ports     端口占用时抢占 (默认只告警)
--demo            (已弃用) 等价 --dry-run, 但会改系统
```

环境变量：

```text
EVO_SUB_DELAY=5     订阅响应延迟秒数 (0~20, 给 frida attach 留窗口)
EVO_SRV_VER=9.9.9   服务端发布版本 (避免客户端升级后重新打包)
MOCK_MODE=echo      mock8880 响应模式
MOCK_PORT=8880      mock8880 监听端口
MOCK_LOG=<path>     mock8880 日志路径
```

---

## 三、目录结构

```text
SKILL.md                          技能主文档 (含适用范围判定 + 变更记录)
assets/
  error-codes-and-protocol.md     错误码表 + 验证矩阵 + 请求/响应结构
  README.md                       资产说明 (不含真实卡密)
references/
  evo-case.md                     本案例完整实测记录
  gotchas.md                      13 类环境与工具链坑位
  evofree-local-proxy.md          Themida 版免卡密本地代理方法学
  cleanup.md                      环境还原/清理清单
scripts/
  pe_recon.py                     PE 结构 + 导入表 + 段熵快筛
  analyze_dump.py                 内存 dump 分析
  mock8880.py                     Mock 上游服务器 (多响应模式)
  frida_run.py                    Frida spawn + 注入 + 喂卡密 + dump
  hook_agent.js                   96 钩子探针 + RPC
  boot_schtasks.cmd               schtasks 提权脚手架 (纯 ASCII)
  evofree/
    evofree_main.py               单文件启动器主程序
    evo_auth_server.py            独立授权服务
    evo_free.js                   免卡密内存补丁 agent
    start_evofree.py              服务 + attach 一键脚本
    build.py                      PyInstaller 打包
    mkembed.py                    生成内嵌资源 _embed.py
    _embed.py                     内嵌证书 + agent
```

---

## 四、v1.0.2 修复了什么

| # | 原问题 | 现状 |
|---|---|---|
| 1 | `mock8880.py` 写死 `C:\alice_evoc\logs\`，目录不存在直接崩 | 多候选探测日志路径 + 自动建目录；新增 `--port/--mode/--log` |
| 2 | 11 个文件硬编码 `C:\Users\alicewe\...`、`C:\alice_evoc`、`F:\alice破甲\...` | 全部改为**相对脚本位置推导** + 命令行覆盖；可整包搬到任意目录/中文路径 |
| 3 | `--demo` 会写 hosts + 装根证书，不是沙箱 | 新增 **`--dry-run`** 真正零副作用；`--demo` 保留但显式告警 |
| 4 | `--cleanup` 靠模糊匹配，会误删同名注释行 | **标记 + 状态文件双轨**精确还原；新增 `--restore` 兜底 |
| 5 | 启动时无条件 `taskkill` 占用 443/80 的进程 | 默认只告警；`--force-ports` 才抢占；`--ports` 可换端口 |
| 6 | `SUB_DELAY` 硬编码；文档章节号重复（两个「九」） | 可用 `EVO_SUB_DELAY` 覆盖；章节号重排 |
| 7 | `hook_agent.js` dump 目录写死 | 多候选探测，取第一个可写目录 |
| 8 | docstring 触发 `SyntaxWarning`；`pe_recon`/`analyze_dump` 无 `--help` | 全部修掉，并补上用法说明 |

**实测验证**：

```text
--dry-run              3 端点全 200, 且 hosts/证书/SSL 目录零改动   OK
patch_hosts+install_ca hosts 16->22 行, 证书装入, 状态文件已记录     OK
unpatch+uninstall      hosts 与基线逐字节一致, 证书归零, 目录移除    OK
mock8880 干净目录启动   正常监听, 日志自动落到 <包>/logs/            OK
py_compile 10/10       OK
node --check 2/2       OK
SyntaxWarning 扫描      0 处                                        OK
```

---

## 五、注意

- 本技能沉淀的是 **Evo 系「本地授权服务器伪造 + TLS 中间人」** 这一种思路，
  并非所有 DMA 外挂都采用该方案。套用前**必须先判定目标的授权校验形态**（见 `SKILL.md` 「零」）。
- 所有 hosts / 证书改动都记在 `evofree.state.json`，用完请跑 `--cleanup` 还原。
- 目标 exe 支持自动探测，也可用 `--evo` / `--exe` 显式指定。
