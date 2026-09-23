# -*- coding: utf-8 -*-
r"""
evo_auth_server.py -- Evo 本地授权服务 (免卡密)

依据已完成的静态/动态逆向结论实现:
  * 客户端 evo.exe = cpp-httplib 0.15.3 + 静态 OpenSSL 3.6.0, 走 HTTPS + Bearer JSON
  * 端点   /user/authorize /session/validate /session/logout
           /user/register /user/email/verify|resend|pending
           /v2/user/subscription/ /v2/product/ /user/subscription/unpause
  * 会话   客户端登录成功后自行写 C:/Evo/user.dat
  * 信任   客户端 OpenSSL 默认 CA 目录 C:/Program Files/Common Files/SSL
           (cert.pem / certs/) 以及 Windows 系统证书库 (org.openssl.winstore)

本服务不校验卡密, 对任何凭证一律返回授权成功。

用法:
    python evo_auth_server.py            # 默认: 443(HTTPS) + 8880(HTTP/HTTPS) + 80
    python evo_auth_server.py --port 443 # 只开一个 HTTPS 端口
"""
import argparse, datetime, hashlib, json, os, ssl, sys, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
CERT = os.path.join(ROOT, "certs", "srv.pem")
LOGDIR = os.path.join(ROOT, "logs")
os.makedirs(LOGDIR, exist_ok=True)

LOCK = threading.Lock()

# 订阅响应固定延迟(秒): 给免卡密加载器留出 attach 窗口 (evo 登录后约 45ms 即请求订阅)
SUB_RESPONSE_DELAY = float(os.environ.get("EVO_SUB_DELAY", "5"))
_log_path = os.path.join(LOGDIR, "requests.log")
_cfg_path = os.path.join(ROOT, "config.json")

DEFAULT_CFG = {
    "username": "evofree",
    "user_id": "00000000-0000-0000-0000-00000000f0ee",
    "product_id": "1",
    "product_name": "Valorant DMA",
    "days": 3650,
    "is_admin": True,
    "auth_level": 3,
    "verbose": True,
}


def cfg():
    if os.path.exists(_cfg_path):
        try:
            with open(_cfg_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            c = dict(DEFAULT_CFG)
            c.update(d)
            return c
        except Exception:
            pass
    return dict(DEFAULT_CFG)


def log(*a):
    line = "[%s] " % datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3] + " ".join(str(x) for x in a)
    with LOCK:
        with open(_log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    if cfg().get("verbose", True):
        try:
            print(line, flush=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# VARIANT OVERRIDE (探测订阅响应 schema 用)
# 服务端每次请求时读取 ROOT/variant.json:
#   {"scope":"sub"|"all", "status":200, "mode":"json"|"raw", "raw":"...", "body":{...}}
# 文件不存在或 scope 不匹配时使用默认行为。
# ---------------------------------------------------------------------------
def sub_delay_for(path):
    if "subscription" in (path or "").lower() and SUB_RESPONSE_DELAY > 0:
        return SUB_RESPONSE_DELAY
    return 0.0


def variant_for(path):
    p = os.path.join(ROOT, "variant.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8-sig") as f:
            v = json.load(f)
    except Exception:
        return None
    scope = (v.get("scope") or "sub").lower()
    lp = path.lower()
    if scope == "sub" and "subscription" not in lp:
        return None
    if scope == "authorize" and "authorize" not in lp:
        return None
    if scope == "validate" and "validate" not in lp:
        return None
    return v


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def mk_token():
    return hashlib.sha256((uuid.uuid4().hex + str(time.time())).encode()).hexdigest()


def sub_obj(c):
    start = datetime.datetime.now(datetime.timezone.utc)
    exp = start + datetime.timedelta(days=int(c.get("days", 3650)))
    a = start.strftime("%Y-%m-%d %H:%M:%S UTC")
    e = exp.strftime("%Y-%m-%d %H:%M:%S UTC")
    return {
        "product_id": c["product_id"],
        "product_key": "EVO-FREE-0000-0000-0000",
        "product_name": c["product_name"],
        "ActivationDate": a,
        "activation_date": a,
        "expiration": e,
        "expiration_date": e,
        "expire": e,
        "valid": True,
        "active": True,
        "authorized": True,
        "status": "active",
        "plan": "lifetime",
        "tier": "premium",
        "subscription": {
            "product_id": c["product_id"],
            "valid": True,
            "active": True,
            "activation_date": a,
            "expiration": e,
        },
    }


def identity(c, req=None):
    user = c["username"]
    if isinstance(req, dict):
        for k in ("username", "email", "user", "login", "name"):
            v = req.get(k)
            if isinstance(v, str) and v.strip():
                user = v.strip()
                break
    return {
        "token": mk_token(),
        "authorized": True,
        "success": True,
        "status": "ok",
        "code": 0,
        "is_admin": bool(c.get("is_admin", True)),
        "auth_level": c.get("auth_level", 3),
        "user_id": c["user_id"],
        "UserId": c["user_id"],
        "username": user,
        "user": user,
        "email": user,
        "hwid": "EVOFREE-HWID-0000000000",
        "Hwid": "EVOFREE-HWID-0000000000",
        "server_time": now_iso(),
        "created_at": now_iso(),
        "verified": True,
        "verification_required": False,
        "registration_pending": False,
        "auth_mode": "local-any-accept",
    }


def make_body(path, req):
    c = cfg()
    p = path.lower()
    ident = identity(c, req)
    if "/logout" in p:
        return {"success": True, "status": "ok", "code": 0, "logged_out": True}
    if "/register" in p:
        b = dict(ident)
        b.update({"verification_required": False, "registration_pending": False,
                  "verified": True, "authorized": True,
                  "verification_email_sent": False, "resend_after_seconds": 0})
        return b
    if "/email/verify" in p or "/email/resend" in p or "/email/pending" in p:
        b = dict(ident)
        b.update({"verified": True, "verification_required": False, "code": "000000"})
        return b
    b = dict(ident)
    b.update(sub_obj(c))
    b["authorized"] = True
    return b


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "nginx"

    def _read_body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except Exception:
            n = 0
        if n <= 0:
            return b""
        return self.rfile.read(n)

    def _handle(self, verb):
        raw = self._read_body()
        u = urlparse(self.path)
        req = None
        if raw:
            try:
                req = json.loads(raw.decode("utf-8", "replace"))
            except Exception:
                req = None
        v = variant_for(u.path)
        status = 200
        ctype = "application/json"
        _sd = sub_delay_for(u.path)
        if _sd > 0:
            log("   .. delaying subscription response %.1fs (attach window)" % _sd)
            time.sleep(_sd)
        if v is not None and v.get("delay"):
            d = float(v.get("delay"))
            log("   .. delaying response %.1fs (variant scope=%s)" % (d, v.get("scope")))
            time.sleep(d)
        if v is not None and v.get("status") is not None:
            status = int(v.get("status", 200))
            if (v.get("mode") or "json").lower() == "raw":
                raw_out = v.get("raw", "")
                out = raw_out.encode("utf-8") if isinstance(raw_out, str) else bytes(raw_out)
                ctype = v.get("ctype", "application/text")
            else:
                out = json.dumps(v.get("body", {}), ensure_ascii=False).encode("utf-8")
            body = v.get("body", {})
            if v.get("body") is None and v.get("mode") is None:
                body = make_body(u.path, req)
                out = json.dumps(body, ensure_ascii=False).encode("utf-8")
        else:
            body = make_body(u.path, req)
            out = json.dumps(body, ensure_ascii=False).encode("utf-8")
        log("=" * 78)
        log("%s %s  from %s:%s" % (verb, self.path, self.client_address[0], self.client_address[1]))
        for k, v in self.headers.items():
            log("   H  %s: %s" % (k, v))
        if raw:
            log("   BODY %d bytes  %s" % (len(raw), raw[:600].decode("utf-8", "replace")))
        try:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(out)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(out)
            self.close_connection = True
            log("   -> %d %s %d bytes" % (status, ctype, len(out)))
            log("   OUT %s" % out[:1200].decode("utf-8", "replace"))
        except Exception as e:
            log("   !! send failed: %r" % (e,))

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_PATCH(self):
        self._handle("PATCH")

    def do_DELETE(self):
        self._handle("DELETE")

    def log_message(self, fmt, *args):
        pass


def serve(port, tls):
    srv = ThreadingHTTPServer(("0.0.0.0", port), H)
    srv.daemon_threads = True
    if tls:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(CERT)
        try:
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        except Exception:
            pass
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    log("### listening 0.0.0.0:%d (%s)" % (port, "HTTPS" if tls else "HTTP"))
    srv.serve_forever()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--no-8880", action="store_true")
    ap.add_argument("--no-80", action="store_true")
    a = ap.parse_args()
    log("#" * 78)
    log("### evo local auth server starting. cert=%s" % CERT)
    if not os.path.exists(CERT):
        log("!! cert missing: %s" % CERT)
        sys.exit(2)
    ts = []
    if a.port:
        ts.append(threading.Thread(target=serve, args=(a.port, True), daemon=True))
    else:
        ts.append(threading.Thread(target=serve, args=(443, True), daemon=True))
        if not a.no_8880:
            ts.append(threading.Thread(target=serve, args=(8880, False), daemon=True))
            ts.append(threading.Thread(target=serve, args=(8880, True), daemon=True))
        if not a.no_80:
            ts.append(threading.Thread(target=serve, args=(80, False), daemon=True))
    for t in ts:
        t.start()
    log("### %d listener(s) up" % len(ts))
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        log("### ctrl-c, exiting")


if __name__ == "__main__":
    main()
