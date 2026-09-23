#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进程内存字符串/证据提取器（加壳程序运行时分析主工具）
====================================================
用法:
  python mem_strings.py <pid> [输出文件] [--min N]

功能:
  - 全量读取目标进程已提交可读内存
  - 提取 UTF-16LE 字符串（ASCII + CJK），带虚拟地址
  - 检测 .NET 元数据块（BSJB）位置
  - 结果打印并可写文件（UTF-8）

为什么存在: 加壳+字符串加密的程序，文件里搜不到明文，
运行时字符串已解密在内存中 —— 指纹模板/注册表路径/提示语全在这里。
"""
import ctypes, ctypes.wintypes as w, re, sys, io

def main():
    if len(sys.argv) < 2:
        print(__doc__); return 1
    pid = int(sys.argv[1])
    out_path = None
    min_len = 6
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--min" and i + 1 < len(args):
            min_len = int(args[i + 1]); args = args[:i] + args[i + 2:]; break
    if args:
        out_path = args[0]

    k32 = ctypes.windll.kernel32
    k32.OpenProcess.restype = w.HANDLE
    h = k32.OpenProcess(0x0010 | 0x0400, False, pid)   # VM_READ | QUERY_INFORMATION
    if not h:
        print("!! OpenProcess(%d) 失败，需要同权限级别运行" % pid); return 1

    class MBI(ctypes.Structure):
        _fields_ = [("BaseAddress", ctypes.c_void_p),
                    ("AllocationBase", ctypes.c_void_p),
                    ("AllocationProtect", w.DWORD),
                    ("RegionSize", ctypes.c_size_t),
                    ("State", w.DWORD),
                    ("Protect", w.DWORD),
                    ("Type", w.DWORD)]

    MEM_COMMIT = 0x1000
    BAD_PROTECT = {0x01}   # 仅 PAGE_NOACCESS 拒读；0x02/0x04/0x08 是可读页（READONLY/READWRITE/WRITECOPY），过滤会丢掉 .NET 字符串堆
    pat = re.compile(rb"(?:[\x20-\x7e]\x00|[\x00-\xff][\x4e-\x9f]){4,}")

    addr, total, strings = 0, 0, {}
    bsjb = []
    while addr < 0x7FFFFFFFFFFF:
        mbi = MBI()
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        size = mbi.RegionSize
        if mbi.State == MEM_COMMIT and mbi.Protect not in BAD_PROTECT and size:
            buf = ctypes.create_string_buffer(size)
            got = ctypes.c_size_t()
            if k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(got)) and got.value:
                d = buf.raw[:got.value]
                total += got.value
                for m in pat.finditer(d):
                    try:
                        s = d[m.start():m.end()].decode("utf-16-le")
                    except Exception:
                        continue
                    s = s.strip("\x00")
                    if len(s) >= min_len:
                        strings.setdefault(s, addr + m.start())
                idx = 0
                while True:
                    idx = d.find(b"BSJB", idx)
                    if idx < 0:
                        break
                    bsjb.append(addr + idx)
                    idx += 4
        addr += size

    lines = ["# total_read=%dMB strings=%d bsjb=%d" % (total // 1048576, len(strings), len(bsjb))]
    lines += ["BSJB @ 0x%x" % a for a in bsjb[:80]]
    lines += ["0x%012x\t%s" % (a, s) for s, a in sorted(strings.items(), key=lambda kv: kv[1])]
    text = "\n".join(lines)
    if out_path:
        io.open(out_path, "w", encoding="utf-8").write(text)
        print("written:", out_path.encode("unicode_escape").decode())
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        print(text)
    k32.CloseHandle(h)
    return 0

if __name__ == "__main__":
    sys.exit(main())
