# -*- coding: utf-8 -*-
r"""start_evofree.py -- 起本地授权服务 + 拉起 evo.exe + attach 注入 evo_free.js

修复 (v1.0.1):
  * 不再写死 C:\Users\alicewe\Desktop\evoc 与 F:\alice破甲\...site-packages
  * 目标 exe 自动探测, 可用 --evo 覆盖
  * frida 缺失时给出安装提示而不是崩掉

用法:
    python start_evofree.py                       # 自动找 evo.exe
    python start_evofree.py --evo "D:\evoc\evo.exe"
    python start_evofree.py --no-server --wait 20
"""
import argparse
import datetime
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
PY = sys.executable
SRV = os.path.join(HERE, "evo_auth_server.py")
JSP = os.path.join(HERE, "evo_free.js")
LOGS = os.path.join(PKG, "logs")
os.makedirs(LOGS, exist_ok=True)
EOUT = os.path.join(LOGS, "evo.out.log")
LOG = os.path.join(LOGS, "evofree.log")


def log(m):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), m)
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def find_evo(explicit=None):
    if explicit:
        return os.path.abspath(explicit) if os.path.isfile(explicit) else None
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    roots = [os.getcwd(), PKG,
             os.path.join(home, "Desktop"),
             os.path.join(home, "Downloads")]
    for r in roots:
        for sub in ("", "evoc", "Evo", "evo"):
            p = os.path.join(r, sub, "evo.exe") if sub else os.path.join(r, "evo.exe")
            if os.path.isfile(p):
                return os.path.abspath(p)
    for drv in ("C:", "D:", "E:", "F:", "G:"):
        for sub in (r"\Evo", r"\evoc", r"\evo"):
            p = drv + sub + r"\evo.exe"
            if os.path.isfile(p):
                return os.path.abspath(p)
    return None


def kill(name):
    subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True)


def kill_port(port):
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-NetTCPConnection -State Listen -LocalPort %d "
             "-ErrorAction SilentlyContinue).OwningProcess" % port],
            capture_output=True, text=True).stdout
    except Exception:
        return
    for tok in (out or "").split():
        if tok.isdigit() and int(tok) != os.getpid():
            subprocess.run(["taskkill", "/F", "/PID", tok], capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", type=float, default=15.0,
                    help="登录后等待秒数再 attach")
    ap.add_argument("--no-server", action="store_true")
    ap.add_argument("--evo", default=None, help="evo.exe 完整路径")
    a = ap.parse_args()

    try:
        import frida
    except ImportError:
        log("缺少 frida 模块。安装: pip install frida frida-tools")
        log("或: %s -m pip install frida" % PY)
        return 3

    evo = find_evo(a.evo)
    if not evo:
        log("没找到 evo.exe, 请用 --evo \"路径\" 指定")
        return 2
    wd = os.path.dirname(evo)
    log("目标 evo: %s" % evo)

    kill("evo.exe")
    for p in (443, 80, 8880):
        kill_port(p)
    time.sleep(1.2)

    sp = None
    if not a.no_server:
        if not os.path.isfile(SRV):
            log("找不到授权服务: %s" % SRV)
            return 2
        sp = subprocess.Popen([PY, SRV],
                              stdout=open(os.path.join(LOGS, "server.out.log"), "wb"),
                              stderr=open(os.path.join(LOGS, "server.err.log"), "wb"))
        log("auth server pid %d" % sp.pid)
        time.sleep(2.5)
        if sp.poll() is not None:
            log("!! server exited rc=%s" % sp.returncode)
            try:
                log(io.open(os.path.join(LOGS, "server.err.log"),
                            encoding="utf-8", errors="replace").read()[-1500:])
            except Exception:
                pass
            return 1

    try:
        os.remove(EOUT)
    except OSError:
        pass
    ep = subprocess.Popen([evo], cwd=wd, stdout=open(EOUT, "wb"),
                          stderr=subprocess.DEVNULL)
    log("evo pid %d" % ep.pid)

    deadline = time.time() + 20
    logged = False
    while time.time() < deadline:
        time.sleep(0.3)
        try:
            txt = io.open(EOUT, encoding="utf-8", errors="replace").read()
        except OSError:
            txt = ""
        if "Logged In" in txt:
            logged = True
            break
    log("logged=%s" % logged)
    time.sleep(max(0.0, a.wait))

    def on_message(msg, data):
        if msg.get("type") == "send":
            log("AGENT " + str(msg.get("payload"))[:600])
        elif msg.get("type") == "error":
            log("AGENTERR " + str(msg.get("description"))[:300])

    session = None
    try:
        session = frida.attach(ep.pid)
        script = session.create_script(io.open(JSP, encoding="utf-8").read())
        script.on("message", on_message)
        script.load()
        log("agent injected into pid %d" % ep.pid)
    except Exception as e:
        log("!! attach/inject failed: %r" % (e,))
        return 3

    try:
        while ep.poll() is None:
            time.sleep(1.0)
        log("evo exited rc=%s" % ep.returncode)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            session.detach()
        except Exception:
            pass
        if sp is not None:
            try:
                sp.kill()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
