# -*- coding: utf-8 -*-
r"""生成 _embed.py: 把证书与 agent 内嵌为 base64/python 字面量

修复 (v1.0.1): 路径改为相对本脚本推导, 不再写死 C:\Users\alicewe\...

用法:
    python mkembed.py
    python mkembed.py --root "D:\evoc\evofree"
"""
import argparse
import base64
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(HERE)   # evofree/ 的上级 = scripts/


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT,
                    help="evofree 工作目录 (含 certs/ 与 loader/)")
    ap.add_argument("--out", default=None, help="输出 _embed.py 路径")
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    srv_p = os.path.join(root, "certs", "srv.pem")
    ca_p = os.path.join(root, "certs", "ca.crt")
    js_p = os.path.join(root, "loader", "evo_free.js")
    out_p = a.out or os.path.join(root, "pack", "_embed.py")

    missing = [p for p in (srv_p, ca_p, js_p) if not os.path.isfile(p)]
    if missing:
        print("缺少输入文件:")
        for m in missing:
            print("  " + m)
        print("\n提示: 若使用本包自带的 evo_free.js, 可用 --root 指向 scripts/ 并把")
        print("      certs/ 与 loader/ 摆好; 或直接使用已有的 _embed.py。")
        return 2

    srv = io.open(srv_p, "rb").read()
    ca = io.open(ca_p, "rb").read()
    js = io.open(js_p, "rb").read()
    out = ["# -*- coding: utf-8 -*-",
           "# auto-generated: embedded certs + frida agent",
           "import base64",
           "SRV_PEM_B64 = %r" % base64.b64encode(srv).decode(),
           "CA_CRT_B64  = %r" % base64.b64encode(ca).decode(),
           "AGENT_JS_B64 = %r" % base64.b64encode(js).decode(),
           "def srv_pem(): return base64.b64decode(SRV_PEM_B64)",
           "def ca_crt():  return base64.b64decode(CA_CRT_B64)",
           "def agent_js(): return base64.b64decode(AGENT_JS_B64).decode('utf-8')",
           ""]
    os.makedirs(os.path.dirname(out_p), exist_ok=True)
    io.open(out_p, "w", encoding="utf-8").write("\n".join(out))
    print("embed ok -> %s (%d bytes)" % (out_p, len("\n".join(out))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
