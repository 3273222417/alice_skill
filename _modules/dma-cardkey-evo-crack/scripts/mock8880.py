# -*- coding: utf-8 -*-
r"""mock 上游授权服务器 -- 捕获 Evo_Crack.exe 的完整请求并试探响应格式

修复 (v1.0.1):
  * 日志目录不再写死 C:\alice_evoc; 默认落到 <包>/logs/, 自动创建
  * 目录不可写时回退 %TEMP%, 再不行回退 stderr (绝不再因日志崩掉)
  * 端口 / 模式可用命令行或环境变量覆盖

用法:
    python mock8880.py                      # 默认 8880, echo 模式
    python mock8880.py --port 8880 --mode json_true
    python mock8880.py --log D:\cap\mock.log
环境变量:
    MOCK_MODE=echo|empty200|raw64|json_true|zeros
    MOCK_PORT=8880
    MOCK_LOG=<日志文件路径>
"""
import argparse
import io
import json
import os
import socket
import struct
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)          # 包根目录

MODES = ("echo", "empty200", "raw64", "json_true", "zeros")


def pick_log(explicit=None):
    """按优先级选一个可写的日志路径, 全都失败返回 None"""
    cands = []
    if explicit:
        cands.append(explicit)
    env = os.environ.get("MOCK_LOG")
    if env:
        cands.append(env)
    cands.append(os.path.join(PKG, "logs", "mock_server.log"))
    cands.append(os.path.join(HERE, "mock_server.log"))
    try:
        import tempfile
        cands.append(os.path.join(tempfile.gettempdir(), "mock_server.log"))
    except Exception:
        pass
    for c in cands:
        try:
            d = os.path.dirname(os.path.abspath(c))
            if d:
                os.makedirs(d, exist_ok=True)
            with io.open(c, "a", encoding="utf-8"):
                pass
            return c
        except Exception:
            continue
    return None


LOG_PATH = pick_log()
logf = None
if LOG_PATH:
    try:
        logf = io.open(LOG_PATH, "a", encoding="utf-8", buffering=1)
    except Exception:
        logf = None


def log(*a):
    s = " ".join(str(x) for x in a)
    if logf is not None:
        try:
            logf.write(s + "\n")
            logf.flush()
            return
        except Exception:
            pass
    try:
        sys.stderr.write(s + "\n")
        sys.stderr.flush()
    except Exception:
        pass


def build_resp(body, ctype="application/json", status="200 OK"):
    hdr = ("HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
           "Connection: close\r\n\r\n" % (status, ctype, len(body))).encode()
    return hdr + body


def handle(conn, addr, idx, mode):
    try:
        conn.settimeout(15)
        buf = b""
        while b"\r\n\r\n" not in buf:
            c = conn.recv(65536)
            if not c:
                break
            buf += c
            if len(buf) > 4 * 1024 * 1024:
                break
        hdr_end = buf.find(b"\r\n\r\n")
        head = buf[:hdr_end] if hdr_end >= 0 else buf
        body = buf[hdr_end + 4:] if hdr_end >= 0 else b""
        cl = 0
        for line in head.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                try:
                    cl = int(line.split(b":")[1].strip())
                except Exception:
                    pass
        while len(body) < cl:
            c = conn.recv(65536)
            if not c:
                break
            body += c
        log("=" * 80)
        log("[REQ %d] from %s:%d  total=%d head=%d body=%d cl=%d"
            % (idx, addr[0], addr[1], len(buf), len(head), len(body), cl))
        log("--- HEAD ---")
        log(head.decode("latin1", "replace"))
        log("--- BODY (hex) len=%d ---" % len(body))
        hx = body.hex()
        for i in range(0, len(hx), 96):
            log("   " + hx[i:i + 96])
        log("--- BODY (ascii) ---")
        log("   " + "".join(chr(b) if 32 <= b < 127 else "." for b in body[:2000]))

        if mode == "echo":
            r = build_resp(body, "application/octet-stream")
        elif mode == "empty200":
            r = build_resp(b"", "application/octet-stream")
        elif mode == "raw64":
            r = build_resp(b"\x00" * 64, "application/octet-stream")
        elif mode == "json_true":
            r = build_resp(b'{"success":true,"status":"ok","code":0}',
                           "application/json")
        elif mode == "zeros":
            r = build_resp(struct.pack("<II", 8, 0) + b"\x00" * 8,
                           "application/octet-stream")
        else:
            r = build_resp(b"", "application/octet-stream")
        conn.sendall(r)
        log("--- RESP (%s) %d bytes ---" % (mode, len(r)))
        log(r[:600].hex())
    except Exception as e:
        log("[ERR %d] %s" % (idx, e))
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="mock 上游授权服务器")
    ap.add_argument("--port", type=int,
                    default=int(os.environ.get("MOCK_PORT") or 8880))
    ap.add_argument("--mode", default=os.environ.get("MOCK_MODE") or "echo",
                    choices=MODES)
    ap.add_argument("--log", default=None, help="日志文件路径")
    ap.add_argument("--host", default="0.0.0.0")
    a = ap.parse_args()

    global LOG_PATH, logf
    if a.log and a.log != LOG_PATH:
        LOG_PATH = pick_log(a.log)
        try:
            logf = io.open(LOG_PATH, "a", encoding="utf-8", buffering=1) if LOG_PATH else None
        except Exception:
            logf = None

    print("mock server  port=%d  mode=%s" % (a.port, a.mode))
    print("log        : %s" % (LOG_PATH or "<stderr only>"))

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((a.host, a.port))
    except OSError as e:
        log("[FATAL] bind %s:%d failed: %s" % (a.host, a.port, e))
        print("bind 失败: %s  (端口被占用? 换 --port)" % e)
        return 1
    s.listen(16)
    log("### mock server listening %s:%d mode=%s" % (a.host, a.port, a.mode))
    print("listening  : %s:%d" % (a.host, a.port))
    print("Ctrl+C 退出")
    cnt = [0]
    try:
        while True:
            c, addr = s.accept()
            cnt[0] += 1
            threading.Thread(target=handle, args=(c, addr, cnt[0], a.mode),
                             daemon=True).start()
    except KeyboardInterrupt:
        print("\nbye")
        return 0
    except Exception as e:
        log("[ACCEPT ERR] %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
