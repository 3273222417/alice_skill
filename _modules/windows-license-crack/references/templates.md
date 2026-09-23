# 代码模板（按目标程序改常量后使用）

> 以下模板来自一次完整实战（MPRESS 壳 + .NET 单文件 NativeAOT + ECDSA 验签的工具箱）。
> 使用时替换：目标进程名、指纹模板、提示语、授权码结构常量。

## 1. 静态侦察：壳 / overlay / 单文件识别（pefile）

```python
import pefile
pe = pefile.PE(exe_path)
print("Machine:", hex(pe.FILE_HEADER.Machine))          # 0x8664 = x64
for s in pe.sections:
    print(s.Name.decode(errors="replace").rstrip("\x00"),
          hex(s.VirtualAddress), "entropy=%.2f" % s.get_entropy())
    # .MPRESS1/.MPRESS2 => MPRESS 壳；UPX0 => UPX；
    # .CLR_UEF => .NET 单文件 bundle；高熵(>7.5)节 = 压缩/加密
overlay_off = pe.get_overlay_data_start_offset()
# overlay 高熵 => 附加数据（可能是释放载荷/资源包）
```

## 2. 进程内存字符串提取（UTF-16 + UTF-8 + BSJB）

```python
import ctypes, ctypes.wintypes as w, re, sys

pid = int(sys.argv[1])
k32 = ctypes.windll.kernel32
PROCESS_VM_READ, PROCESS_QS = 0x0010, 0x0400
h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QS, False, pid)

class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD), ("RegionSize", ctypes.c_size_t),
                ("State", wintypes.DWORD), ("Protect", wintypes.DWORD), ("Type", wintypes.DWORD)]

addr, results = 0, {}
MEM_COMMIT = 0x1000
BAD_PROTECT = {0x01, 0x02, 0x04, 0x08}   # NOACCESS/READONLY-例外/GUARD 系列：跳过
while addr < 0x7FFFFFFFFFFF:
    mbi = MBI()
    if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        break
    size = mbi.RegionSize
    # 只读已提交、可读的内存
    if mbi.State == MEM_COMMIT and mbi.Protect not in BAD_PROTECT and size:
        buf = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(got)):
            d = buf.raw[:got.value]
            # UTF-16LE：ASCII 段 + 中文段（CJK 高字节 0x4E-0x9F）
            pat = re.compile(rb"(?:[\x20-\x7e]\x00|[\x00-\xff][\x4e-\x9f]){4,}")
            for m in pat.finditer(d):
                try: s = d[m.start():m.end()].decode("utf-16-le")
                except Exception: continue
                if len(s) >= 6: results[s] = addr + m.start()
            # .NET 元数据
            idx = d.find(b"BSJB")
            if idx >= 0: print("BSJB metadata @", hex(addr + idx))
    addr += size
for s, a in sorted(results.items(), key=lambda kv: kv[1]):
    print(hex(a), repr(s))
```

要点：
- 文件里搜不到明文 = 字符串运行时解密，**这是主战场**；
- 找到指纹模板（如 `App|CPU:{x};DISK:{y};BOARD:{z}`）→ 第 4 步算法输入原文；
- 找到 `SOFTWARE\xxx` → 授权存储位置（可读注册表确认 ConfigToken 等）；
- 中文/关键串可能"按需解密、用完即销"，扫不到就转观测器。

## 3. 加密调用只读观测器（先观测后挂钩的铁律）

骨架（Frida JS，通过 python 的 `dev.spawn([exe])` + `script.post`/message 回传）：

```js
function hexof(p, n) { /* 读 p 起始 n 字节转 hex，截断 256 */ }
function hook(dll, fn) {
  var mod; try { mod = Module.load(dll); } catch (e) { return; }
  var a;    try { a = mod.getExportByName(fn); } catch (e) { return; }
  Interceptor.attach(a, {
    onEnter: function(args) {
      var rec = { t: "CALL", mod: dll, fn: fn, bt: this.returnAddress.toString() };
      // 按函数语义记录参数：Hash/Verify 记 hash+sig 的 hex；Import 记 blob
      if (/Verify/.test(fn)) { rec.hash = hexof(args[2], args[3].toInt32());
                               rec.sig  = hexof(args[4], args[5].toInt32()); }
      send(rec);
    }
  });
}
["bcrypt.dll","bcryptPrimitives.dll","ncrypt.dll"].forEach(function(d) {
  try { Module.load(d).enumerateExports().forEach(function(e) {
    if (/Verify|Sign|Decrypt|Encrypt|Hash|Import|Secret|Derive/.test(e.name)) hook(d, e.name);
  }); } catch (err) {}
});
```

判读：
- 看到 `NCryptImportKey` + blob `"ECCPUBLICBLOB"` → ECDSA 走 CNG；
- `BCryptHashData/FinishHash` 的输入 = 授权码 payload 原文（先 `SHA256` 一下比对确认哈希算法）；
- `NCryptVerifySignature` 的 sig 参数与已知授权码签名段比对（`MINE=true`）。

**绝不在此阶段改返回值**——观测器只读，不会触发反插桩。

## 4. 过滤式强制验签（最终绕过 JS）

```js
var MY_SIG = "<已知授权码的签名段 hex 大写>";   // 只对这条签名放行
function hexof(p, n) { /* 同上 */ }

function hookVerify(dllName, fnName) {
  var mod; try { mod = Module.load(dllName); } catch (e) { return; }
  var addr; try { addr = mod.getExportByName(fnName); } catch (e) { return; }
  Interceptor.attach(addr, {
    onEnter: function(a) {
      this.sig  = hexof(a[4], a[5].toInt32());   // NCryptVerifySignature(hKey,pbHash,cbHash,pbSig,cbSig,flags)
      this.mine = (this.sig === MY_SIG);
    },
    onLeave: function(r) {
      var st = r.toInt32();
      if (this.mine) { if (st !== 0) { r.replace(0); send({t:'FORCED', fn:fnName}); } }
      // 其它验签一律原样放行 —— 保护程序自检，避免"授权模块异常"
    }
  });
}
hookVerify('ncrypt.dll', 'NCryptVerifySignature');
hookVerify('bcrypt.dll', 'BCryptVerifySignature');   // 双路径都挂（启动期/后台可能走另一条）
// bcryptPrimitives.dll 的 BCryptVerifySignature 真实实现也挂（同参数位）
```

## 5. 启动器工程要点（python 侧）

```python
import frida, glob, os, time, subprocess

dev = frida.get_local_device()

def find_inner():
    # 自解压程序会自我清理/改写 exe：按 mtime 选"最新"可能选中坏文件，必须校验大小
    c = glob.glob(os.path.join(os.environ.get("TEMP",""), "~*", "Target.exe"))
    v = [p for p in c if _size_ok(p)]            # getsize > 50MB，OSError 跳过
    return max(v, key=os.path.getmtime) if v else None

def find_outer():                                 # 原版安装包候选位置
    for p in [r"C:\安装包.exe", PKG_ROOT_安装包, 桌面, 下载目录]:
        if os.path.exists(p): return p
    return None

exe = find_inner()
if not exe:                                       # 别的电脑首次使用
    outer = find_outer()
    if outer:
        subprocess.Popen([outer]);                # 让它自解压（钩子挂壳无效！）
        for i in range(90):
            time.sleep(1)
            exe = find_inner()
            if exe: break

for l in subprocess.run(["tasklist","/fo","csv","/nh"], ...).stdout.splitlines():
    if "Target" in l: subprocess.run(["taskkill","/F","/PID", ...])

pid = dev.spawn([exe], cwd=os.path.dirname(exe))  # spawn 从第一条指令就挂钩
script = dev.attach(pid).create_script(JS); script.load(); dev.resume(pid)

gone = 0
while True:
    time.sleep(2)
    alive = any(p.pid == pid for p in dev.enumerate_processes())
    gone = gone + 1 if not alive else 0
    if gone >= 2: break            # ★ 进程枚举判活，连续 2 次才认死；
                                   #   用"有无窗口"判断会在初始化慢时误判 →
                                   #   钩子卸载 → 程序验签失败自杀
```

## 6. 跨机器授权码生成器

```python
import base64, hashlib, json, subprocess

SIG_B64 = "<已知真实授权码的签名段>"       # hook 只认签名段，不看哈希 → 全机器通用
def machine_code():
    ps = ("$cpu=(Get-CimInstance Win32_Processor|Select -First 1).ProcessorId;"
          "$disk=(Get-CimInstance Win32_DiskDrive|?{$_.Index -eq 0}|Select -First 1).SerialNumber;"
          "$board=(Get-CimInstance Win32_BaseBoard|Select -First 1).SerialNumber;"
          "[pscustomobject]@{cpu=$cpu;disk=$disk;board=$board}|ConvertTo-Json -Compress")
    d = json.loads(subprocess.run(["powershell","-NoProfile","-Command",ps],
                   capture_output=True, text=True, encoding="utf-8").stdout or "{}")
    raw = 'App|CPU:%s;DISK:%s;BOARD:%s' % (d.get("cpu") or "", d.get("disk") or "",
                                           d.get("board") or "UNKNOWN")
    h = hashlib.md5(raw.encode()).hexdigest().upper()
    return "%s-%s-%s-%s" % (h[:4], h[4:8], h[8:12], h[12:16])

def make_license(code, expiry="209912312359"):     # yyyyMMddHHmm
    return base64.b64encode(f"{code}|{expiry}".encode()).decode() + "." + SIG_B64
```

**必带自检**：用已知机器码生成，与已知可用授权码逐字符比对，一致才输出（算法漂移检测）。

## 7. 回收站删除（可恢复清理）

```python
import ctypes
FO_DELETE, FOF_ALLOWUNDO, FOF_NOCONFIRMATION, FOF_SILENT, FOF_NOERRORUI = 3, 0x40, 0x10, 0x4, 0x400
# SHFILEOPSTRUCTW 结构 + SHFileOperationW(byref(op))
# op.pFrom = path + "\0"  （ctypes c_wchar_p 自动补第二个 \0）
# 返回码在 64 位上可能误报 ERR=2 —— 一律以操作后的 os.path.exists() 为准
```

## 8. 分发 zip 打包与校验

```python
import os, zipfile
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for root, dirs, files in os.walk(pkg):
        for f in sorted(files):
            if f.endswith(".log"): continue          # 日志不进包
            full = os.path.join(root, f)
            z.write(full, os.path.join("包名", os.path.relpath(full, pkg)))
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    names = z.namelist()
    # ★ zip 内部路径分隔符是 "/" 不是 os.sep，endswith 校验时用 "tools/x.py"
    assert all(any(n.endswith(k) for n in names) for k in KEY_FILES)
```
