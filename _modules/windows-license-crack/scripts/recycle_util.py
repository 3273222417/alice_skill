#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回收站删除工具（可恢复清理）
============================
用法:
  python recycle_util.py <路径> [路径2 ...]

注意:
  - 走 SHFileOperationW + FOF_ALLOWUNDO，文件进回收站，可还原
  - ★ 64 位机上返回码可能误报（成功却返回 ERR=2）——
    一律以操作后的 os.path.exists() 为准，本工具已自动附上验证
"""
import ctypes, os, sys
from ctypes import wintypes

FO_DELETE = 3
FOF_SILENT = 0x0004
FOF_NOCONFIRMATION = 0x0010
FOF_ALLOWUNDO = 0x0040
FOF_NOERRORUI = 0x0400

class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND),
                ("wFunc", ctypes.c_uint),
                ("pFrom", ctypes.c_wchar_p),
                ("pTo", ctypes.c_wchar_p),
                ("fFlags", ctypes.c_ushort),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", ctypes.c_wchar_p)]

def recycle(path):
    """返回 (shell返回码, 事后是否仍存在)。仍存在 = 失败。"""
    op = SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = FO_DELETE
    op.pFrom = path + "\0"          # 双 NUL 结尾（c_wchar_p 再补一个）
    op.pTo = None
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    op.fAnyOperationsAborted = False
    op.hNameMappings = None
    op.lpszProgressTitle = None
    r = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return r, os.path.exists(path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    fails = 0
    for p in sys.argv[1:]:
        if not os.path.exists(p):
            print("SKIP(不存在) " + p.encode("unicode_escape").decode()); continue
        code, still = recycle(p)
        if still:
            fails += 1
            print("FAIL(code=%d) %s" % (code, p.encode("unicode_escape").decode()))
        else:
            print("OK(进回收站) " + p.encode("unicode_escape").decode())
    sys.exit(1 if fails else 0)
