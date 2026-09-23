# 定位与追踪操作细节

## 一、六条定位路径的具体做法

### 路径 1：提示语 / 字符串检索

- 原生：IDA/Ghidra 打开 Strings 窗口，搜 `激活`、`授权`、`licen`、`trial`、`expire`、`invalid`、`signature`
- .NET：dnSpy 右键程序集 → 搜索 → 字符串常量，直接双击跳到引用方法
- 交叉引用（XREF）：对命中的字符串按 X，看哪个函数引用它 → 该函数的上层就是判断分支
- **坑**：全局字符串搜索无结果 ≠ 没有校验。可能是运行时解密或按需解密（windows-license-crack 第 3 步）。此时转路径 4/5

### 路径 2：导入表 / API 筛选

按授权模型的"功能面"倒推该调哪些 API：

| 授权特征 | 必查 API | 说明 |
|---|---|---|
| 卡密验签 | `BCryptVerifySignature` / `NCryptVerifySignature` / `CryptVerifySignature` | 两条 CNG 路径并存，必须都挂 |
| 授权存注册表 | `RegSetValueEx` / `RegQueryValueEx` | 授权文件路径与键名是重要线索 |
| 机器码/指纹 | `GetVolumeInformation` / `GetAdaptersInfo` / WMI `Win32_*` | 决定卡密是否绑机器 |
| 试用期 | `GetLocalTime` / `GetSystemTime` / `GetFileTime` | 时间锁的入口 |
| 授权文件 | `CreateFile` / `ReadFile` 到 `.lic`/`.dat`/`.key` | 直接看文件内容即可判断结构 |

### 路径 3：GUI 事件回溯

- WinForms/WPF：dnSpy 找窗体的 `InitializeComponent`，定位按钮的 `Click` 事件委托 → 跟进 handler
- Delphi：IDR/DeDe 加载 exe → Forms 页看事件表 → 定位 OnClick 地址
- 原生 MFC/Win32：x64dbg 对 `user32!DispatchMessageW` 下断 → 断下后回溯栈到窗口过程（`WndProc`）→ 在窗口过程里找 `WM_COMMAND` 分支
- **坑**：有些程序把激活逻辑放在后台线程，事件 handler 只是 `PostMessage`，此时要跟消息队列

### 路径 4：内存搜输入串（对抗加密字符串最有效）

1. 准备一段高辨识度输入（如 `AAAAA-BBBBB-CCCCC-DDDDD-EEEEE`），不要用真实卡密
2. 在输入框粘贴但**先不点确定**
3. 用 x64dbg 的 Memory Map → 搜字符串（同时勾 UTF-16 与 UTF-8，多数 Windows 程序是 UTF-16）
4. 对命中地址下**内存访问断点**（读/写），然后点确定
5. 命中指令即比较点（通常是 `repe cmpsb` / `memcmp` / 逐字节 `cmp`）

**为什么有效**：无论文件层面怎么加密，用户输入最终一定会以明文存在于内存缓冲区里。

### 路径 5：内存字符串扫描

用 windows-license-crack 的 `scripts/mem_strings.py` 全量扫进程内存，拿解密后的提示语、指纹模板、注册表路径。注：按需解密、用完即销的提示语扫不到，只能用观测器抓。

### 路径 6：跨语言分支速查

| 语言 / 打包 | 首选工具 | 关键特征 | 常见误区 |
|---|---|---|---|
| .NET Framework | dnSpy / ILSpy | 有 BSJB 元数据 | 混淆后需 de4dot 先反混淆 |
| .NET 单文件 bundle | 提取后回 dnSpy | 单 exe、内嵌 coreclr | 有 coreclr = 可提 IL |
| .NET NativeAOT | IDA / Ghidra | bundle 但无 coreclr | **无 IL 可看，只能运行时分析** |
| 原生 C/C++ | IDA / Ghidra | 无 BSJB | 静态量大，优先 API 断点缩小范围 |
| Delphi | IDR / DeDe | VCL 类名、`TForm` | 字符串在 DFM 资源里 |
| Go | IDA + go_parser | 函数名含包名、大字符串表 | 符号被 strip 时需先恢复 |
| Electron | asar 解包 | `resources/app.asar` | 直接看 JS，几乎无保护 |
| PyInstaller | pyi-archive_viewer | `PYZ`、`.pyc` | 提 pyc 后反编译即可 |

## 二、断点与追踪的常见误判与排除

| 现象 | 真实原因 | 处置 |
|---|---|---|
| 挂了 `BCryptVerifySignature` 却什么都没断下 | 实际走 `NCryptVerifySignature` | 先用观测器全量只读确认路径 |
| 断点命中但参数看起来是乱码 | 参数是句柄或结构体指针，需进一步解引用 | 读第二层指针；或用 Frida 打印完整结构 |
| 强制返回成功后仍报"签名失败" | 存在第二道校验（启动期/后台定时） | 双 API 同时挂；检查是否有线程定时重验 |
| 修改后立即崩溃 | 删了被后续逻辑依赖的校验代码 | 改为最小改动：只翻转判断结果，保留原函数体 |
| 内存访问断点不命中 | 输入被复制到另一缓冲区 | 对复制后的新地址再下断；或用 `memcmp`/`lstrcmp` API 断点 |
| 断点导致程序退出 | 触发了反调试（软件断点检测） | 改用硬件断点；确认 ScyllaHide 插件已启用 |
| 改返回值后报"模块异常" | 触发反插桩 | 减少挂钩面，只挂验签函数，其余原样放行 |

## 三、追踪完成的三条自检

1. **可复现**：同样的输入，每次都能在同一条指令命中 —— 排除偶然路径
2. **可解释**：能说清输入经过哪几个函数变成最终比较值 —— 排除"只看到表面"
3. **可干预**：改这一处，结果确实翻转，且不引入崩溃 —— 排除"改了个无关紧要的地方"

三条中少一条，都不要进入阶段四（打补丁），否则验证阶段必然返工。
