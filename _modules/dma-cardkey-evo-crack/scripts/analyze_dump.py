# -*- coding: utf-8 -*-
"""analyze_dump.py - 内存 dump 分析 (DMA 卡密破解专用)
用法: python analyze_dump.py <dump.bin>
输出: ASCII / UTF-16LE / GBK 字符串, EVO_* 常量, /api 路径, 事件名, 段熵
"""
import sys, re, math, collections, struct

def ent(b):
    if not b: return 0.0
    c = collections.Counter(b); n = len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

def s_ascii(d, mn=6):
    return sorted({s.decode("latin1") for s in re.findall(rb"[\x20-\x7E]{%d,}" % mn, d)})

def s_utf16(d, mn=4):
    out = []
    i, n = 0, len(d)
    while i < n-1:
        if 0x4e <= d[i+1] <= 0x9f:
            j, raw = i, b""
            while j < n-1:
                b0, b1 = d[j], d[j+1]
                if (0x4e <= b1 <= 0x9f) or (0x20 <= b0 <= 0x7e and b1 == 0):
                    raw += d[j:j+2]; j += 2
                else: break
            if len(raw) >= mn*2:
                try:
                    t = raw.decode("utf-16le")
                    if re.search(r"[\u4e00-\u9fff]{%d,}" % (mn//2), t): out.append(t)
                except Exception: pass
            i = j
        else: i += 1
    return sorted(set(out))

def main(path):
    d = open(path, "rb").read()
    print("dump %s size=%d entropy=%.4f" % (path, len(d), ent(d)))

    print("\n=== EVO_* 常量 ===")
    for m in sorted(set(re.findall(rb"EVO_[A-Z0-9_]+", d))): print("  ", m.decode())

    print("\n=== 事件名 / 模式标识 ===")
    pat = rb"[a-z][a-z0-9_]{4,40}(?:_mode|_fixture|_fallback|_accept|_replayed|_issued|_skipped|_failed|_ready|_started|_resolved|_trusted|_installed)"
    for m in sorted(set(re.findall(pat, d))): print("  ", m.decode())

    print("\n=== API 路径 ===")
    for m in sorted(set(re.findall(rb"/[a-z][a-z0-9_./-]{3,50}", d))):
        t = m.decode()
        if re.match(r"^/(user|session|v2|api|auth|product|login)", t): print("  ", t)

    print("\n=== 中文提示串 (UTF-16LE) ===")
    for s in s_utf16(d, 4)[:400]: print("  ", s)

    print("\n=== 关键 ASCII ===")
    kw = ("http", "host:", "user-agent", "content-length", "bearer", "token",
          "hwid", "user_id", "server_time", "hosts", "certificate", "root store",
          "elevat", "accept-any", "preserve", "user.dat", "jsonl", "creatorprocess")
    for s in s_ascii(d, 6):
        if any(k in s.lower() for k in kw): print("  ", s[:200])

    print("\n=== CLI / 环境变量 ===")
    for m in sorted(set(re.findall(rb"--[a-z][a-z0-9-]{2,40}", d))): print("  ", m.decode())

    print("\n=== 证书候选 (DER 30 82, 含 X509 OID) ===")
    cnt = 0
    for i in range(0, len(d)-4):
        if d[i] == 0x30 and d[i+1] == 0x82:
            ln = struct.unpack_from(">H", d, i+2)[0]
            if 800 < ln < 4000 and i+4+ln <= len(d):
                blob = d[i+4:i+4+ln]
                if b"\x06\x03\x55\x04" in blob:
                    print("   0x%08X len=%d" % (i, ln)); cnt += 1
                    if cnt > 10: break
    if not cnt: print("   none")

    # 段熵 (若 dump 是模块镜像)
    try:
        lf = struct.unpack_from("<I", d, 0x3C)[0]
        if d[lf:lf+4] == b"PE\x00\x00":
            nsec = struct.unpack_from("<H", d, lf+6)[0]
            optsz = struct.unpack_from("<H", d, lf+20)[0]
            secoff = lf + 24 + optsz
            print("\n=== live 段熵 (解包后) ===")
            for i in range(nsec):
                o = secoff + i*40
                nm = d[o:o+8].rstrip(b"\x00").decode("latin1")
                vs, va, rs, raw = struct.unpack_from("<IIII", d, o+8)
                print("   %-10s VA=0x%08X VS=0x%08X ent=%.3f" % (nm, va, vs, ent(d[va:va+min(vs, len(d)-va)])))
    except Exception: pass

USAGE = """analyze_dump.py -- 内存 dump 分析

用法:
    python analyze_dump.py <dump.bin> [more.bin ...]

分析内容:
    整体熵 / 节区熵      (判断是否仍被压缩/加密)
    EVO_* 常量           (定位关键开关名)
    事件名 / 模式标识
    API 路径             (/user/authorize 等端点)
    中文提示串 (UTF-16LE) (壳惰性解密后的提示语)
    关键 ASCII / CLI 参数 / 环境变量
    证书候选项 (DER 30 82 / X509 OID)

提示:
    壳会惰性解密字符串 -> 不同运行阶段多 dump 几次
    只搜 ASCII/GBK 容易漏, UTF-16LE 一定要搜
"""

if not sys.argv[1:] or sys.argv[1] in ("-h", "--help", "/?"):
    print(USAGE)
    sys.exit(0)

for p in sys.argv[1:]: main(p)
