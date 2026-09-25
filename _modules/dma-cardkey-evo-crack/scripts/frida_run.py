# -*- coding: utf-8 -*-
r"""frida_run.py -- spawn 目标 + 注入 hook_agent.js + 喂卡密 + 自动 dump

修复 (v1.0.1):
  * 全部路径改为相对脚本位置, 不再写死 C:\alice_evoc / C:\Users\alicewe\...
  * 目标 exe / 工作目录 / 卡密 都可用命令行指定
  * frida 缺失时给出可操作的安装提示, 不再抛裸 ImportError

用法:
    python frida_run.py --exe "D:\evoc\Evo_Crack.exe"
    python frida_run.py --exe ... --cwd ... --key EVO-TESTKEY-0001-AAAA-BBBB
    python frida_run.py --list          # 只列出探测到的候选目标
"""
import argparse
import io
import json
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
AGENT = os.path.join(HERE, "hook_agent.js")
LOGDIR = os.path.join(PKG, "logs")
DUMPS = os.path.join(PKG, "dumps")

DEFAULT_KEYS = ["EVO-TESTKEY-0001-AAAA-BBBB"]


def find_targets():
    """在常见位置找 Evo_Crack.exe / evo.exe"""
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    roots = [os.getcwd(), PKG,
             os.path.join(home, "Desktop"),
             os.path.join(home, "Downloads"),
             os.path.join(home, "Documents")]
    names = ("Evo_Crack.exe", "evo.exe", "EC1.1.exe")
    hits = []
    for r in roots:
        for sub in ("", "evoc", "Evo", "evo", "EvoFree"):
            d = os.path.join(r, sub) if sub else r
            for n in names:
                p = os.path.join(d, n)
                if os.path.isfile(p):
                    hits.append(os.path.abspath(p))
    for drv in ("C:", "D:", "E:", "F:", "G:"):
        for sub in (r"\Evo", r"\evoc", r"\evo"):
            for n in names:
                p = drv + sub + "\\" + n
                if os.path.isfile(p):
                    hits.append(os.path.abspath(p))
    seen, out = set(), []
    for h in hits:
        if h.lower() not in seen:
            seen.add(h.lower())
            out.append(h)
    return out


def main():
    ap = argparse.ArgumentParser(description="Frida 探针运行器")
    ap.add_argument("--exe", default=None, help="目标 exe 完整路径")
    ap.add_argument("--cwd", default=None, help="目标工作目录 (默认=exe 所在目录)")
    ap.add_argument("--key", action="append", default=None,
                    help="要喂入的卡密, 可重复")
    ap.add_argument("--out", default=None, help="日志文件 (默认 <包>/logs/run.log)")
    ap.add_argument("--wait", type=float, default=3.0, help="每次喂 key 后等待秒数")
    ap.add_argument("--list", action="store_true", help="只列出候选目标")
    a = ap.parse_args()

    if a.list:
        hits = find_targets()
        print("候选目标 (%d):" % len(hits))
        for h in hits:
            print("  " + h)
        if not hits:
            print("  <没找到, 请用 --exe 指定>")
        return 0

    exe = a.exe
    if not exe:
        hits = find_targets()
        if not hits:
            print("没找到目标 exe, 请用 --exe \"路径\" 指定")
            return 2
        exe = hits[0]
        print("自动选中: %s" % exe)
    exe = os.path.abspath(exe)
    if not os.path.isfile(exe):
        print("目标不存在: %s" % exe)
        return 2
    cwd = a.cwd or os.path.dirname(exe)

    try:
        import frida
    except ImportError:
        print("缺少 frida 模块。安装:")
        print("  pip install frida frida-tools")
        print("或使用王炸 MCP venv:")
        print("  $CODEX_HOME\\mcp\\venv\\Scripts\\python.exe -m pip install frida")
        return 3

    os.makedirs(LOGDIR, exist_ok=True)
    os.makedirs(DUMPS, exist_ok=True)
    out = a.out or os.path.join(LOGDIR, "run.log")
    keys = a.key if a.key else list(DEFAULT_KEYS)

    logf = io.open(out, "w", encoding="utf-8", buffering=1)

    def log(*x):
        try:
            logf.write(" ".join(str(i) for i in x) + "\n")
            logf.flush()
        except Exception:
            pass
        try:
            print(" ".join(str(i) for i in x), flush=True)
        except Exception:
            pass

    if not os.path.isfile(AGENT):
        log("找不到 agent: %s" % AGENT)
        return 2
    src = io.open(AGENT, "r", encoding="utf-8").read()

    STATE = {"exit": False}
    SCRIPT = {"s": None}

    def on_message(msg, data):
        try:
            if msg.get("type") == "send":
                p = msg.get("payload", {})
                tag = p.get("tag")
                d = p.get("data") or {}
                if tag == "line":
                    log("[%s] %s" % (p.get("t"), d.get("msg")))
                elif tag == "EXITGATE":
                    STATE["exit"] = True
                    log("### EXITGATE %s" % json.dumps(d, ensure_ascii=False))
                else:
                    extra = {k: v for k, v in d.items() if k not in ("hex", "ascii")}
                    log("[%s] %s %s" % (p.get("t"), tag,
                                        json.dumps(extra, ensure_ascii=False)))
                    body = d.get("hex") or ""
                    asc = d.get("ascii") or ""
                    if body:
                        for i in range(0, len(body), 96):
                            log("        " + body[i:i + 96].rstrip())
                    if asc:
                        for i in range(0, len(asc), 96):
                            log("        |" + asc[i:i + 96] + "|")
            elif msg.get("type") == "error":
                log("!! ERROR " + str(msg.get("description")))
                log(str(msg.get("stack"))[:1200])
        except Exception as e:
            log("!! onmsg fail " + str(e))

    log("=== start " + time.strftime("%H:%M:%S"))
    log("=== exe " + exe)
    log("=== cwd " + cwd)
    log("=== log " + out)

    dev = frida.get_local_device()
    pid = dev.spawn([exe], cwd=cwd, stdio="pipe")
    log("=== PID %d" % pid)
    session = dev.attach(pid)
    script = session.create_script(src)
    script.on("message", on_message)
    SCRIPT["s"] = script
    script.load()
    log("=== script loaded")
    dev.resume(pid)
    log("=== resumed")
    time.sleep(4.0)

    for k in keys:
        try:
            dev.input(pid, (k + "\r\n").encode("utf-8"))
            log("=== fed key %r" % k)
        except Exception as e:
            log("=== feed fail " + str(e))
        time.sleep(a.wait)

    time.sleep(3.0)

    # dump 关键模块 + RWX
    try:
        res = script.exports_sync.gatedump()
        for row in res:
            log("    [MOD] %s base=%s size=0x%X -> %s" % tuple(row))
        log("=== [LIVE] modules dumped: %d" % len(res))
    except Exception as e:
        log("gatedump fail %s" % e)

    try:
        rng = script.exports_sync.ranges("rwx")
        rep = os.path.join(LOGDIR, "rwx_live.json")
        io.open(rep, "w", encoding="utf-8").write(json.dumps(rng, indent=1))
        log("=== [LIVE] rwx %d -> %s" % (len(rng), rep))
        big = [x for x in rng if x["size"] >= 0x1000][:30]
        for i, r in enumerate(big):
            nm = "live_rwx_%02d_%s.bin" % (i, r["base"].replace("0x", ""))
            try:
                rr = script.exports_sync.saverange(
                    r["base"], min(r["size"], 32 * 1024 * 1024),
                    os.path.join(DUMPS, nm))
                log("    [RWX] %s size=0x%X -> %s" % (r["base"], r["size"], rr))
            except Exception as e:
                log("    rwx dump fail %s" % e)
    except Exception as e:
        log("rwx fail %s" % e)

    try:
        script.exports_sync.release()
    except Exception as e:
        log("release fail %s" % e)
    time.sleep(8.0)
    try:
        session.detach()
    except Exception:
        pass
    try:
        dev.kill(pid)
    except Exception:
        pass
    log("=== DONE")
    logf.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("FATAL " + str(e))
        traceback.print_exc()
        sys.exit(1)
