# -*- coding: utf-8 -*-
r"""
EvoFree 单文件启动器 (self-contained)

作用: 在一台只装了 evo.exe 的 Windows 机器上, 一键完成
  1. UAC 自提权
  2. hosts 劫持 scheats.club / freakluke.me -> 127.0.0.1   (可 --dry-run 跳过)
  3. 内嵌 CA 装入 LocalMachine\Root + 写入 OpenSSL 信任目录 (可 --dry-run 跳过)
  4. 启动内嵌本地授权服务 (HTTPS 443 / 8880 / 80)
  5. 启动 evo.exe
  6. 等待登录成功后 attach 注入免卡密 agent (订阅时间字段 + 版本字段补齐)

用法:
  EvoFree.exe                    # 正常启动 (自动提权)
  EvoFree.exe --dry-run          # 只起服务自检, 不改 hosts / 不装证书 / 不拉 evo
  EvoFree.exe --cleanup          # 精确还原本次改动 (hosts / 证书 / OpenSSL 目录)
  EvoFree.exe --restore          # 同上, 并额外清掉残留的 OpenSSL 信任目录
  EvoFree.exe --evo "D:\path\to\evo.exe"
  EvoFree.exe --server-only      # 只起服务, 方便调试
  EvoFree.exe --no-elevate       # 已提权时跳过
  EvoFree.exe --ports 8443,8880  # 自定义监听端口

修复 (v1.0.2):
  * --demo 更名为 --dry-run, 且真正不再触碰系统 (旧版会写 hosts + 装根证书)
  * hosts 改动带标记注释, 还原时精确删除, 不再误伤同名注释行
  * 证书/OpenSSL 目录改动记入状态文件, 还原时按记录精确删除
  * 端口占用默认只告警不杀进程 (--force-ports 才杀)
  * 启动日志记录本次所有系统改动, 便于事后审计
"""
import argparse
import io
import re
import base64
import datetime
import hashlib
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from _embed import srv_pem, ca_crt, agent_js

APP = "EvoFree"
VERSION = "1.0.2"

HOSTS = ["scheats.club", "www.scheats.club", "api.scheats.club",
         "freakluke.me", "www.freakluke.me"]
REDIRECT = "127.0.0.1"
HOSTS_MARK = "# EvoFree local-auth redirect (auto-added)"

SSL_DIR = r"C:\Program Files\Common Files\SSL"
HOSTS_FILE = r"C:\Windows\System32\drivers\etc\hosts"

# 本次运行所做的系统改动, 落盘以便 --cleanup 精确还原
def _pkg_dir():
    try:
        return os.path.dirname(os.path.abspath(
            sys.executable if getattr(sys, "frozen", False) else __file__))
    except Exception:
        return os.getcwd()


STATE_FILE = os.path.join(_pkg_dir(), "evofree.state.json")
DEFAULT_PORTS = (443, 8880, 80)


def load_state():
    try:
        return json.loads(io.open(STATE_FILE, encoding="utf-8").read())
    except Exception:
        return {}


def save_state(st):
    try:
        io.open(STATE_FILE, "w", encoding="utf-8").write(
            json.dumps(st, indent=1, ensure_ascii=False))
    except Exception as e:
        log("写状态文件失败: %r" % (e,), "warn")


def state_add(key, values):
    """把 values 并入 state[key] (去重), 立即落盘"""
    st = load_state()
    cur = st.get(key) or []
    if not isinstance(cur, list):
        cur = []
    for v in values:
        if v not in cur:
            cur.append(v)
    st[key] = cur
    save_state(st)
    return st

# 服务端发布版本 (必须 >= 客户端版本, 否则 evo 弹 "Version Mismatch")
def _srv_ver():
    """服务端发布版本: 必须 >= 客户端版本, 否则 evo 弹 Version Mismatch.
    环境变量 EVO_SRV_VER=9.9.9 可覆盖 (避免客户端升级后重新打包)."""
    v = (os.environ.get("EVO_SRV_VER") or "").strip()
    if v:
        try:
            parts = [int(x) for x in v.split(".")]
            if len(parts) >= 3 and all(0 <= x < 100000 for x in parts[:3]):
                return tuple(parts[:3])
        except Exception:
            pass
    return (1, 5, 12)


SRV_VER = _srv_ver()
# 订阅响应延迟: 客户端在登录后 ~45ms 就发订阅请求, 必须靠服务端延迟
# 制造 attach 窗口。实测 5~8s 有效; >20s 会触发客户端超时
# (错误串变 "Failed to get subscription data")。可用环境变量覆盖。
def _sub_delay():
    v = (os.environ.get("EVO_SUB_DELAY") or "").strip()
    if v:
        try:
            f = float(v)
            if 0.0 <= f <= 20.0:
                return f
        except Exception:
            pass
    return 5.0


SUB_DELAY = _sub_delay()


# --------------------------------------------------------------------------
# logging
# --------------------------------------------------------------------------
def _log_path():
    """日志文件: 优先 exe 同目录, 失败回退 %TEMP% (别的机器上方便排查)"""
    try:
        base = os.path.dirname(os.path.abspath(
            sys.executable if getattr(sys, "frozen", False) else __file__))
    except Exception:
        base = os.getcwd()
    for cand in (os.path.join(base, "EvoFree.log"),
                 os.path.join(tempfile.gettempdir(), "EvoFree.log")):
        try:
            with open(cand, "a", encoding="utf-8"):
                pass
            return cand
        except Exception:
            pass
    return None


LOG_FILE = _log_path()


def log(msg, level="info"):
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = "[%s] [%s] %s" % (ts, level, msg)
    try:
        print(line, flush=True)
    except Exception:
        pass
    if LOG_FILE:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def die(msg, code=1):
    log(msg, "error")
    try:
        input("\n按回车退出...")
    except Exception:
        pass
    sys.exit(code)


def is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate():
    """用 UAC 重启自己 (带所有参数)"""
    if is_admin():
        return False
    params = " ".join('"%s"' % a for a in sys.argv[1:])
    log("请求管理员权限...")
    try:
        import ctypes
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable,
                                                params, None, 1)
        return rc > 32
    except Exception as e:
        die("提权失败: %r" % (e,))
        return False


# --------------------------------------------------------------------------
# hosts
# --------------------------------------------------------------------------
def patch_hosts():
    """写入带标记的 hosts 重定向; 已存在则跳过"""
    try:
        raw = io.open(HOSTS_FILE, "rb").read().decode("utf-8", "replace")
    except Exception as e:
        log("读取 hosts 失败: %r" % (e,), "error")
        return False
    lines = raw.splitlines()
    have = set()
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) >= 2 and REDIRECT in parts[0]:
            have.add(parts[1].lower())
    need = [h for h in HOSTS if h.lower() not in have]
    if not need:
        log("hosts 已就绪 (无需改动)")
        return True
    try:
        shutil.copy2(HOSTS_FILE, HOSTS_FILE + ".evofree.bak")
    except Exception:
        pass
    if not any(HOSTS_MARK in ln for ln in lines):
        lines.append(HOSTS_MARK)
    for h in need:
        lines.append("%s %s" % (REDIRECT, h))
    try:
        io.open(HOSTS_FILE, "w", encoding="utf-8", newline="").write(
            "\r\n".join(lines) + "\r\n")
    except Exception as e:
        log("写 hosts 失败: %r" % (e,), "error")
        return False
    subprocess.run("ipconfig /flushdns", shell=True, capture_output=True)
    state_add("hosts_added", need)
    log("hosts 已劫持 -> %s (新增 %d 条, 已记入状态文件)" % (REDIRECT, len(need)))
    return True


def unpatch_hosts(quiet=False):
    """只删我们自己加的: 状态文件里记录的行 + 带标记的行块"""
    st = load_state()
    tracked = set((st.get("hosts_added") or []))
    try:
        raw = io.open(HOSTS_FILE, "rb").read().decode("utf-8", "replace")
    except Exception as e:
        log("读取 hosts 失败: %r" % (e,), "error")
        return
    kept, dropped = [], []
    for ln in raw.splitlines():
        s = ln.strip()
        if s == HOSTS_MARK:
            dropped.append(ln)
            continue
        parts = s.split()
        if (len(parts) >= 2 and not s.startswith("#") and REDIRECT in parts[0]
                and parts[1].lower() in HOSTS):
            dropped.append(ln)
            continue
        kept.append(ln)
    while kept and not kept[-1].strip():
        kept.pop()
    try:
        io.open(HOSTS_FILE, "w", encoding="utf-8", newline="").write(
            "\r\n".join(kept) + "\r\n")
    except Exception as e:
        log("写 hosts 失败: %r" % (e,), "error")
        return
    subprocess.run("ipconfig /flushdns", shell=True, capture_output=True)
    if not quiet:
        log("hosts 已还原 (移除 %d 行)" % len(dropped))
        for d in dropped:
            log("   - " + d)
    st = load_state()
    st.pop("hosts_added", None)
    save_state(st)


# --------------------------------------------------------------------------
# certificate
# --------------------------------------------------------------------------
def _ca_sha1(ca):
    """返回 DER 形式的 SHA1 指纹 (大写十六进制)"""
    try:
        der = ssl.PEM_cert_to_DER_cert(ca.decode("utf-8", "replace"))
        return hashlib.sha1(der).hexdigest().upper()
    except Exception:
        return ""


def install_ca():
    """装根证书 + 写 OpenSSL 信任目录; 全部记入状态文件以便精确还原"""
    ca = ca_crt()
    sha1 = _ca_sha1(ca)
    tmp = os.path.join(tempfile.gettempdir(), "evofree_ca.crt")
    with io.open(tmp, "wb") as f:
        f.write(ca)

    # --- 系统证书库 ---
    r = subprocess.run(["certutil", "-store", "Root"], capture_output=True,
                       text=True, errors="replace")
    if sha1 and sha1.replace(" ", "") in (r.stdout or "").replace(" ", "").upper():
        log("根证书已在 LocalMachine\\Root")
    elif "Evo Local Authority" in (r.stdout or ""):
        log("根证书已在 LocalMachine\\Root (按 CN 匹配)")
    else:
        r = subprocess.run(["certutil", "-addstore", "-f", "Root", tmp],
                           capture_output=True, text=True, errors="replace")
        if r.returncode != 0:
            log("装根证书失败: %s" % (r.stdout or r.stderr), "error")
            return False
        log("根证书已装入 LocalMachine\\Root")
        state_add("certs_added", [sha1 or "Evo Local Authority"])

    # --- OpenSSL 信任目录 (evo 用 OpenSSL 3.x 默认路径) ---
    created = []
    try:
        cd = os.path.join(SSL_DIR, "certs")
        if not os.path.isdir(cd):
            os.makedirs(cd, exist_ok=True)
            created.append(cd)
        try:
            from cryptography import x509
            c = x509.load_pem_x509_certificate(ca)
            h = hashlib.sha1(c.subject.public_bytes()).hexdigest()[:8]
        except Exception:
            h = "88908d26"
        for path in (os.path.join(SSL_DIR, "cert.pem"),
                     os.path.join(cd, h + ".0")):
            io.open(path, "wb").write(ca)
            created.append(path)
        log("OpenSSL 信任目录已写入 (%s.0)" % h)
        state_add("ssl_files", created)
    except Exception as e:
        log("写 OpenSSL 信任目录失败: %r" % (e,), "warn")
    return True


def uninstall_ca(quiet=False):
    """精确还原: 按状态文件删证书, 按记录删 OpenSSL 文件/目录"""
    st = load_state()
    targets = list(st.get("certs_added") or [])
    if not targets:
        targets = ["Evo Local Authority"]
    for t in targets:
        r = subprocess.run(["certutil", "-delstore", "Root", t],
                           capture_output=True, text=True, errors="replace")
        if not quiet:
            log("卸载根证书 %s rc=%s" % (t[:20], r.returncode))
    st = load_state()
    st.pop("certs_added", None)
    save_state(st)

    files = list(st.get("ssl_files") or [])
    removed = 0
    for f in files:
        try:
            if os.path.isfile(f):
                os.remove(f)
                removed += 1
                if not quiet:
                    log("已删除 " + f)
        except Exception as e:
            if not quiet:
                log("删 %s 失败: %r" % (f, e), "warn")
    # 目录若空则一并移除
    for d in (os.path.join(SSL_DIR, "certs"), SSL_DIR):
        try:
            if os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)
                if not quiet:
                    log("已删除空目录 " + d)
        except Exception:
            pass
    st = load_state()
    st.pop("ssl_files", None)
    save_state(st)
    if not quiet:
        log("证书/信任目录清理完成 (删 %d 个文件)" % removed)


# --------------------------------------------------------------------------
# embedded auth server
# --------------------------------------------------------------------------
LOCK = threading.Lock()


class Cfg(object):
    username = "admin"
    user_id = "00000000-0000-0000-0000-00000000f0ee"
    product_id = "a527f66b-e671-4cb1-838f-09157f6236fe"
    product_name = "Valorant DMA"
    days = 3650
    is_admin = True
    auth_level = 3


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def mk_token():
    return hashlib.sha256((uuid.uuid4().hex + str(time.time())).encode()).hexdigest()


def identity(req=None):
    user = Cfg.username
    if isinstance(req, dict):
        for k in ("username", "email", "user", "login", "name"):
            v = req.get(k)
            if isinstance(v, str) and v.strip():
                user = v.strip()
                break
    return {
        "token": mk_token(), "authorized": True, "success": True,
        "status": "active", "code": 0,
        "is_admin": Cfg.is_admin, "auth_level": Cfg.auth_level,
        "user_id": Cfg.user_id, "UserId": Cfg.user_id,
        "username": user, "user": user, "email": user,
        "hwid": "EVOFREE-HWID-0000000000", "Hwid": "EVOFREE-HWID-0000000000",
        "server_time": now_iso(), "created_at": now_iso(),
        "verified": True, "verification_required": False,
        "registration_pending": False, "auth_mode": "evofree-local",
    }


def sub_obj():
    start = datetime.datetime.now(datetime.timezone.utc)
    exp = start + datetime.timedelta(days=Cfg.days)
    a = start.strftime("%Y-%m-%d %H:%M:%S UTC")
    e = exp.strftime("%Y-%m-%d %H:%M:%S UTC")
    return {
        "product_id": Cfg.product_id, "product_key": "EVO-FREE-0000-0000-0000",
        "product_name": Cfg.product_name,
        "ActivationDate": a, "activation_date": a,
        "expiration": e, "expiration_date": e, "expire": e,
        "ExpirationDate": e, "valid": True, "active": True,
        "VersionMajor": SRV_VER[0], "VersionMinor": SRV_VER[1],
        "VersionPatch": SRV_VER[2],
        "IsPaused": False, "Hwid": ["EVOFREE-HWID-0000000000"],
    }


def make_body(path, req):
    p = (path or "").lower()
    ident = identity(req)
    if "/logout" in p:
        return {"success": True, "status": "ok", "code": 0, "logged_out": True}
    b = dict(ident)
    b.update(sub_obj())
    b["authorized"] = True
    return b


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "nginx"

    def _read_body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except Exception:
            n = 0
        return self.rfile.read(n) if n > 0 else b""

    def _handle(self, verb):
        raw = self._read_body()
        req = None
        if raw:
            try:
                req = json.loads(raw.decode("utf-8", "replace"))
            except Exception:
                pass
        path = urlparse(self.path).path
        if "subscription" in path.lower() and SUB_DELAY > 0:
            time.sleep(SUB_DELAY)
        body = make_body(path, req)
        out = json.dumps(body, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(out)
            self.close_connection = True
        except Exception:
            pass

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_DELETE(self):
        self._handle("DELETE")

    def log_message(self, fmt, *args):
        pass


def serve(port, tls, pem_path):
    try:
        srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    except OSError as e:
        log("端口 %d 占用: %r" % (port, e), "warn")
        return
    srv.daemon_threads = True
    if tls:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(pem_path)
        try:
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        except Exception:
            pass
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    log("监听 0.0.0.0:%d (%s)" % (port, "HTTPS" if tls else "HTTP"))
    srv.serve_forever()


def free_port(port):
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-NetTCPConnection -State Listen -LocalPort %d -ErrorAction SilentlyContinue).OwningProcess" % port],
            capture_output=True, text=True).stdout
        for tok in (out or "").split():
            if tok.isdigit() and int(tok) != os.getpid():
                subprocess.run(["taskkill", "/F", "/PID", tok], capture_output=True)
    except Exception:
        pass


def start_server(pem_path, ports=None, force_ports=False):
    """按端口列表起服务; force_ports=False 时只告警不杀占用进程"""
    ports = tuple(ports) if ports else DEFAULT_PORTS
    if force_ports:
        for p in ports:
            free_port(p)
        time.sleep(0.5)
    else:
        for p in ports:
            if port_in_use(p):
                log("端口 %d 已被占用, 跳过 (需要抢占请加 --force-ports)" % p, "warn")
    started = []
    for p in ports:
        if not force_ports and port_in_use(p):
            continue
        # 443 用 TLS, 其余按 HTTP (与原行为一致)
        use_tls = (p == 443)
        t = threading.Thread(target=serve, args=(p, use_tls, pem_path), daemon=True)
        t.start()
        started.append(p)
    time.sleep(1.0)
    return started


def port_in_use(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.4)
        r = s.connect_ex(("127.0.0.1", port))
        s.close()
        return r == 0
    except Exception:
        return False


# --------------------------------------------------------------------------
# evo discovery / launch
# --------------------------------------------------------------------------
KNOWN_EVO_SIZE = 34249744   # 已知适配版本 evo.exe 大小 (Themida 保护)


def fingerprint(path):
    """打印 evo.exe 指纹; 与已知版本不一致时警告 (RVA 可能不匹配)"""
    try:
        sz = os.path.getsize(path)
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        dig = h.hexdigest()
        log("evo.exe 大小=%d sha256=%s" % (sz, dig[:32]))
        if sz != KNOWN_EVO_SIZE:
            log("!! 该 evo.exe 与已验证版本不同(期望 %d 字节), 注入点可能失效"
                % KNOWN_EVO_SIZE, "warn")
            log("!! 若登录后卡在订阅校验, 请把本机 evo.exe 换成已验证版本再试", "warn")
        return dig
    except Exception as e:
        log("读取 evo.exe 指纹失败: %r" % (e,), "warn")
        return None


def _ok_exe(p):
    try:
        return bool(p) and os.path.isfile(p) and os.path.getsize(p) > 1_000_000
    except Exception:
        return False


def _scan_dir(root, depth=3):
    """在 root 下有限深度找 evo.exe (不全盘扫描)"""
    out = []
    try:
        root = os.path.abspath(root)
        if not os.path.isdir(root):
            return out
        base_depth = root.rstrip("\\").count("\\")
        for cur, dirs, files in os.walk(root):
            if cur.count("\\") - base_depth >= depth:
                dirs[:] = []
            dirs[:] = [d for d in dirs if not d.startswith("$") and d.lower() != "windows"]
            for f in files:
                if f.lower() == "evo.exe":
                    out.append(os.path.join(cur, f))
    except Exception:
        pass
    return out


def find_evo(explicit=None):
    if _ok_exe(explicit):
        return os.path.abspath(explicit)
    try:
        base = os.path.dirname(os.path.abspath(
            sys.executable if getattr(sys, "frozen", False) else __file__))
    except Exception:
        base = os.getcwd()
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    roots = []
    for r in (base, os.getcwd(), os.path.join(home, "Desktop"),
              os.path.join(home, "Downloads"), os.path.join(home, "Documents")):
        if r and r not in roots:
            roots.append(r)
    cands = []
    for r in roots:
        for sub in ("", "evo", "evoc", "Evo", "EvoFree"):
            cands.append(os.path.join(r, sub, "evo.exe"))
    for drive in ("C:", "D:", "E:", "F:", "G:"):
        for sub in (r"\Evo", r"\evoc", r"\evo", r"\Desktop\evoc", r"\Desktop\Evo"):
            cands.append(drive + sub + r"\evo.exe")
    for c in cands:
        if _ok_exe(c):
            return os.path.abspath(c)
    for r in roots[:4]:
        for hit in _scan_dir(r, 3):
            if _ok_exe(hit):
                return os.path.abspath(hit)
    return None


def prompt_evo():
    """找不到 evo.exe 时交互询问路径 (别的机器上的兜底)"""
    log("没有自动找到 evo.exe。", "warn")
    log("建议: 把 EvoFree.exe 放到 evo.exe 同目录再运行, 或用 --evo 指定路径。", "warn")
    for _ in range(5):
        try:
            s = input("请输入 evo.exe 完整路径 (直接回车退出): ").strip().strip(chr(34)).strip(chr(39))
        except Exception:
            return None
        if not s:
            return None
        if _ok_exe(s):
            return os.path.abspath(s)
        log("不是有效的 evo.exe: %s" % s, "warn")
    return None


def launch_evo(evo_path, log_path):
    wd = os.path.dirname(evo_path)
    log("启动 evo: %s" % evo_path)
    try:
        f = open(log_path, "wb")
    except Exception:
        f = subprocess.DEVNULL
    p = subprocess.Popen([evo_path], cwd=wd, stdout=f, stderr=subprocess.STDOUT)
    return p


def wait_login(log_path, timeout=40.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(0.25)
        try:
            txt = open(log_path, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if "Logged In" in txt:
            return True, txt
    try:
        txt = open(log_path, encoding="utf-8", errors="replace").read()
    except Exception:
        txt = ""
    return False, txt


# --------------------------------------------------------------------------
# frida injection
# --------------------------------------------------------------------------
def inject(pid):
    try:
        import frida
    except Exception as e:
        log("frida 不可用: %r" % (e,), "error")
        return None
    js = agent_js()
    want = "[%d, %d, %d]" % SRV_VER
    js2 = re.sub(r"var\s+SRV_VER\s*=\s*\[[^\]]*\]", "var SRV_VER = " + want, js, count=1)
    if js2 != js:
        log("agent 版本号 -> %s" % ".".join(str(x) for x in SRV_VER))
    try:
        session = frida.attach(pid)
        script = session.create_script(js2)
        script.on("message", lambda m, d: log("agent: %s" % str(m.get("payload", m))[:300])
                  if m.get("type") == "send" else None)
        script.load()
        log("agent 已注入 pid=%d" % pid)
        return session
    except Exception as e:
        log("注入失败: %r" % (e,), "error")
        return None


def _demo_server(ports=None):
    """--dry-run: 只跑内嵌服务自检, **不碰 hosts / 不装证书 / 不拉 evo**"""
    import urllib.request, ssl as _ssl
    tmpdir = os.path.join(tempfile.gettempdir(), "evofree")
    os.makedirs(tmpdir, exist_ok=True)
    pem = os.path.join(tmpdir, "srv.pem")
    io.open(pem, "wb").write(srv_pem())
    started = start_server(pem, ports, force_ports=False)
    log("dry-run 监听端口: %s" % (started or "无 (全被占用)"))
    if not started:
        print("dry-run: 没有可用端口, 无法自检 (换 --ports)")
        return
    ctx = _ssl._create_unverified_context()
    # 用真实起来的端口 + 正确协议构造 URL (443 是 HTTPS, 其余 HTTP)
    for ep in ("/user/authorize", "/v2/user/subscription/TEST", "/session/validate"):
        last_err = None
        for port in started:
            scheme = "https" if port == 443 else "http"
            url = "%s://127.0.0.1:%d%s" % (scheme, port, ep)
            try:
                req = urllib.request.Request(
                    url,
                    data=b'{"username":"admin","password":"admin"}',
                    headers={"Content-Type": "application/json",
                             "Host": "scheats.club",
                             "User-Agent": "EVOVALORANT"})
                if scheme == "https":
                    r = urllib.request.urlopen(req, context=ctx, timeout=25)
                else:
                    r = urllib.request.urlopen(req, timeout=25)
                body = r.read().decode("utf-8", "replace")
                print("  %-44s -> %d  %s" % (url.replace("://127.0.0.1", ""), r.status, body[:100]))
                last_err = None
                break
            except Exception as e:
                last_err = e
        if last_err is not None:
            print("  %-44s -> ERR %r" % (ep, last_err))
    print("dry-run OK  (未改动 hosts / 未安装证书)")

# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--evo", default=None, help="evo.exe 完整路径")
    ap.add_argument("--cleanup", action="store_true",
                    help="精确还原 hosts / 证书 / OpenSSL 目录")
    ap.add_argument("--restore", action="store_true",
                    help="同 --cleanup, 并额外清掉残留 OpenSSL 信任目录")
    ap.add_argument("--server-only", action="store_true", help="只起服务")
    ap.add_argument("--no-elevate", action="store_true", help="不自动提权")
    ap.add_argument("--dry-run", action="store_true",
                    help="只起服务自检, 不改 hosts / 不装证书 / 不拉 evo")
    ap.add_argument("--demo", action="store_true",
                    help="(已弃用) 等价于 --dry-run, 但会改动系统")
    ap.add_argument("--ports", default=None,
                    help="逗号分隔的监听端口, 默认 443,8880,80")
    ap.add_argument("--force-ports", action="store_true",
                    help="端口被占用时强杀占用进程 (默认只告警)")
    a = ap.parse_args()

    ports = None
    if a.ports:
        try:
            ports = tuple(int(x) for x in a.ports.split(",") if x.strip())
        except Exception:
            die("--ports 格式错误, 例: --ports 443,8880")

    # --demo 保留但明确警告 (旧行为会改系统)
    if a.demo and not a.dry_run:
        print("!" * 70)
        print(" 警告: --demo 会改动 hosts 与根证书 (旧行为).")
        print("       只做自检请改用 --dry-run (不触碰系统).")
        print("!" * 70)

    print("=" * 70)
    print(" %s v%s  --  Evo 本地免卡密启动器" % (APP, VERSION))
    print("=" * 70)
    if LOG_FILE:
        print(" log: %s" % LOG_FILE)

    if a.dry_run:
        _demo_server(ports)
        return

    if a.demo:
        if not is_admin() and not a.no_elevate:
            if elevate():
                return
        patch_hosts(); install_ca(); _demo_server(ports)
        return

    if a.cleanup or a.restore:
        if not is_admin() and not a.no_elevate:
            if elevate():
                return
        log("开始还原...")
        unpatch_hosts()
        uninstall_ca()
        if a.restore:
            # 兜底: 状态文件缺失时, 按已知路径清掉残留
            try:
                if os.path.isdir(SSL_DIR):
                    shutil.rmtree(SSL_DIR, ignore_errors=True)
                    log("已移除残留目录 " + SSL_DIR)
            except Exception as e:
                log("移除 %s 失败: %r" % (SSL_DIR, e), "warn")
            st = load_state()
            for k in ("hosts_added", "certs_added", "ssl_files"):
                st.pop(k, None)
            save_state(st)
        try:
            if os.path.isfile(STATE_FILE):
                os.remove(STATE_FILE)
        except Exception:
            pass
        log("清理完成")
        return

    if not is_admin():
        if a.no_elevate:
            log("未提权, 部分步骤可能失败", "warn")
        elif elevate():
            return
        else:
            die("需要管理员权限")

    started = time.time()

    # 1) hosts
    if not patch_hosts():
        die("hosts 劫持失败 (需要管理员)")

    # 2) cert
    if not install_ca():
        die("证书安装失败")

    # 3) cert files for server
    tmpdir = os.path.join(tempfile.gettempdir(), "evofree")
    os.makedirs(tmpdir, exist_ok=True)
    pem_path = os.path.join(tmpdir, "srv.pem")
    with open(pem_path, "wb") as f:
        f.write(srv_pem())

    # 4) server
    started_ports = start_server(pem_path, ports, a.force_ports)
    log("本地授权服务就绪 (%.1fs) 端口=%s" % (time.time() - started, started_ports))
    if not started_ports:
        die("没有可用端口 (443/8880/80 全被占用). 用 --ports 换端口或 --force-ports 抢占")

    if a.server_only:
        log("--server-only, 保持运行. Ctrl+C 退出")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return

    # 5) evo
    for name in ("evo.exe",):
        subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True)
    time.sleep(0.5)

    evo = find_evo(a.evo)
    if not evo:
        evo = prompt_evo()
    if not evo:
        die("找不到 evo.exe, 请用 --evo \"路径\" 指定")
    log("找到 evo.exe: %s" % evo)
    fingerprint(evo)

    log_path = os.path.join(tmpdir, "evo.out.log")
    try:
        os.remove(log_path)
    except OSError:
        pass
    ep = launch_evo(evo, log_path)
    log("evo pid=%d" % ep.pid)

    ok, txt = wait_login(log_path)
    if not ok:
        log("未检测到登录成功, 尾部日志:", "warn")
        for ln in txt.strip().splitlines()[-8:]:
            log("   " + ln, "warn")
    else:
        log("登录成功")

    # 6) inject
    log("注入免卡密 agent...")
    session = inject(ep.pid)
    if session is None:
        log("agent 注入失败 -- evo 会卡在订阅校验", "error")

    # 7) report
    time.sleep(8)
    try:
        final = open(log_path, encoding="utf-8", errors="replace").read()
    except Exception:
        final = ""
    good = "Got valid subscription" in final
    print("-" * 70)
    if good:
        log("订阅校验通过 -- 已进入功能界面", "ok")
    else:
        log("订阅未通过, 最后几行:", "warn")
        for ln in final.strip().splitlines()[-6:]:
            log("   " + ln, "warn")
    for ln in final.strip().splitlines()[-4:]:
        log("evo: " + ln)
    print("-" * 70)
    log("保持运行中. 关闭本窗口即可结束")
    try:
        while True:
            time.sleep(2)
            if ep.poll() is not None:
                log("evo 已退出 rc=%s" % ep.returncode)
                break
    except KeyboardInterrupt:
        pass
    finally:
        try:
            session.detach()
        except Exception:
            pass


if __name__ == "__main__":
    main()

