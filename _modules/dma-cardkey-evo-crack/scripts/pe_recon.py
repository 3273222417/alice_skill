# -*- coding: utf-8 -*-
"""pe_recon.py - PE 结构 / 段熵 / 导入表 快筛 (DMA 外挂识别)"""
import sys, math, collections, struct

def ent(b):
    if not b: return 0.0
    c = collections.Counter(b); n = len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

def recon(path):
    d = open(path, "rb").read()
    lf = struct.unpack_from("<I", d, 0x3C)[0]
    assert d[lf:lf+4] == b"PE\x00\x00", "not PE"
    mach = struct.unpack_from("<H", d, lf+4)[0]
    nsec = struct.unpack_from("<H", d, lf+6)[0]
    ts   = struct.unpack_from("<I", d, lf+8)[0]
    optsz= struct.unpack_from("<H", d, lf+20)[0]
    magic= struct.unpack_from("<H", d, lf+24)[0]
    ep   = struct.unpack_from("<I", d, lf+24+16)[0]
    print("="*72)
    print("FILE %s  size=%d" % (path, len(d)))
    print("  machine=0x%04X nsec=%d ts=%d(0x%X) optmagic=0x%X EP=0x%X" % (mach, nsec, ts, ts, magic, ep))
    secoff = lf + 24 + optsz
    print("  --- sections (entropy) ---")
    for i in range(nsec):
        o = secoff + i*40
        nm = d[o:o+8].rstrip(b"\x00").decode("latin1")
        vs, va, rs, raw = struct.unpack_from("<IIII", d, o+8)
        ch = struct.unpack_from("<I", d, o+36)[0]
        body = d[raw:raw+min(rs, vs)] if rs else b""
        flag = ""
        if rs == 0 and vs > 0: flag = "  <-- RAW=0 (runtime-filled / VM target)"
        print("    %-10s VA=0x%08X VS=0x%08X RAW=0x%08X RS=0x%08X ch=0x%08X ent=%.3f%s"
              % (nm, va, vs, raw, rs, ch, ent(body), flag))
    # data dirs
    ddbase = lf + 24 + (0x70 if magic == 0x20b else 0x60)
    names = ["export","import","resource","exception","security","basereloc","debug","arch",
             "globalptr","tls","loadcfg","boundimp","iat","delayimp","comdesc","res"]
    print("  --- data directories ---")
    for i in range(16):
        rva, sz = struct.unpack_from("<II", d, ddbase + i*8)
        if rva or sz: print("    [%2d] %-10s rva=0x%08X size=0x%X" % (i, names[i], rva, sz))
    print("  --- 提示 ---")
    print("    themida/.boot 段 -> Themida/WinLicense;  随机段名+RAW=0 -> VMProtect/自研 VM")
    print("    每个 DLL 只 1 个导入 -> 导入表被抹, 需内存 dump")

USAGE = """pe_recon.py -- PE 结构 / 导入表 / 段熵 快筛

用法:
    python pe_recon.py <target.exe> [more.exe ...]

输出:
    machine / 节区数 / 入口点
    每个节的 熵值  (>=7.9 说明加壳)
    数据目录 (import / resource / iat / delayimp ...)
    加壳类型提示 (Themida / VMProtect / 自研 VM)

提示:
    见到 vmm.dll + leechcore.dll + FTD3XX.dll 三件套 = DMA 卡外挂
    每个 DLL 只 1 个导入 = 导入表被抹, 需内存 dump 后再分析
"""

if not sys.argv[1:] or sys.argv[1] in ("-h", "--help", "/?"):
    print(USAGE)
    sys.exit(0)

for p in sys.argv[1:]:
    try: recon(p)
    except Exception as e: print("ERR", p, e)
