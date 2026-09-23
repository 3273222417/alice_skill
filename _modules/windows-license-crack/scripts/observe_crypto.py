#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密 API 只读观测器 —— 先观测，后挂钩
======================================
用法:
  python observe_crypto.py <目标exe路径>        # spawn 模式（推荐，从第一条指令挂钩）

功能:
  - 一次性挂上 bcrypt.dll / bcryptPrimitives.dll / ncrypt.dll 全部
    Verify|Sign|Decrypt|Encrypt|Hash|Import|Secret|Derive 导出函数
  - 只记录，不修改任何返回值（不会触发反插桩）
  - 记录: 函数、hash 参数 hex、签名参数 hex、调用点地址、进程模块归属
  - 日志写脚本目录 observe_crypto.log

为什么存在: 想当然挂 BCryptVerifySignature 而程序实际走 NCryptVerifySignature
是最常见的失败原因。观测一轮就知道真实验签路径，再去做过滤式强制。
"""
import sys, os, io, time, ctypes

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
LOGF = io.open(os.path.join(HERE, "observe_crypto.log"), "w", encoding="utf-8", buffering=1)
def log(s):
    LOGF.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), str(s)))
    print("[%s] %s" % (time.strftime("%H:%M:%S"), s), flush=True)

try:
    import frida
except ImportError:
    log("!! 缺少 frida: pip install frida"); raise SystemExit(1)

def main():
    if len(sys.argv) < 2:
        print(__doc__); return 1
    exe = sys.argv[1]
    if not os.path.exists(exe):
        log("!! exe 不存在: " + exe); return 1

    dev = frida.get_local_device()
    pid = dev.spawn([exe], cwd=os.path.dirname(exe))
    session = dev.attach(pid)

    JS = r"""
var SEEN = {};
function ev(o){ try{ send(o); }catch(e){} }
function hexof(p, n){
  try{ return Array.from(new Uint8Array(p.readByteArray(Math.min(n, 512))))
    .map(function(b){ return ('0'+b.toString(16)).slice(-2); }).join('').toUpperCase(); }
  catch(e){ return 'ERR'; }
}
function modof(addr){
  try { var m = Process.findModuleByAddress(addr); return m ? (m.name + '+0x' + addr.sub(m.base).toString(16)) : 'private:'+addr.toString(); }
  catch(e){ return '?'; }
}
function hookMod(dll){
  var mod; try { mod = Module.load(dll); } catch(e){ return; }
  mod.enumerateExports().forEach(function(e){
    if (!/Verify|Sign|Decrypt|Encrypt|Hash|Import|Secret|Derive/.test(e.name)) return;
    if (SEEN[dll + '!' + e.name]) return;
    SEEN[dll + '!' + e.name] = true;
    try {
      Interceptor.attach(e.address, {
        onEnter: function(a){
          this.rec = { t:'CALL', fn: dll + '!' + e.name, bt: modof(this.returnAddress) };
          try {
            if (/Verify|Sign/.test(e.name)) { this.rec.hash = hexof(a[2], a[3].toInt32()); this.rec.sig = hexof(a[4], a[5].toInt32()); }
            else if (/Import/.test(e.name)) { this.rec.blob = hexof(a[3], a[4].toInt32()); }
            else if (/Hash|Encrypt|Decrypt/.test(e.name)) { this.rec.data = hexof(a[1], Math.min(a[2].toInt32(), 128)); }
          } catch(err){}
        },
        onLeave: function(r){
          if (this.rec) { this.rec.ret = '0x' + (r.toInt32() >>> 0).toString(16); ev(this.rec); }
        }
      });
    } catch(err){}
  });
  ev({ t:'ok', what: dll });
}
["bcrypt.dll","bcryptPrimitives.dll","ncrypt.dll"].forEach(hookMod);
ev({ t:'ready' });
"""

    def on_message(msg, data):
        if msg.get("type") == "send":
            p = msg["payload"]; t = p.get("t")
            if t == "ok": log("[hook] " + p["what"])
            elif t == "ready": log("[观测就绪] 现在去程序界面手动触发一次激活/登录")
            elif t == "CALL":
                s = "CALL %s  ret=%s  bt=%s" % (p.get("fn"), p.get("ret"), p.get("bt"))
                if p.get("hash"): s += "\n      hash=" + p["hash"][:160]
                if p.get("sig"):  s += "\n      sig =" + p["sig"][:160]
                if p.get("blob"): s += "\n      blob=" + p["blob"][:160]
                if p.get("data"): s += "\n      data=" + p["data"][:160]
                log(s)
        elif msg.get("type") == "error":
            log("[JS错误] " + str(msg.get("description"))[:200])

    script = session.create_script(JS)
    script.on("message", on_message)
    script.load()
    dev.resume(pid)
    log("已启动 pid=%s，观测中……（Ctrl+C 退出）" % pid)
    try:
        sys.stdin.read()
    except KeyboardInterrupt:
        pass
    try: session.detach()
    except Exception: pass
    LOGF.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
