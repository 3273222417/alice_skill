# -*- coding: utf-8 -*-
r"""PyInstaller 构建脚本 (避开 cmd 中文路径编码问题)

修复 (v1.0.1):
  * 不再写死 F:\alice破甲\... 与 C:\Program Files\Python310
  * 自动用当前解释器 / 自动探测 frida site-packages
  * PACK 目录默认 = 本脚本所在目录, 可用 --pack 覆盖

用法:
    python build.py
    python build.py --pack "D:\evoc\evofree\pack" --name EvoFree
"""
import argparse
import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_frida_site():
    """返回包含 frida 包的 site-packages 目录"""
    try:
        import frida
        p = os.path.dirname(os.path.dirname(os.path.abspath(frida.__file__)))
        if os.path.isdir(p):
            return p
    except Exception:
        pass
    try:
        import site
        for sp in list(site.getsitepackages()) + [site.getusersitepackages()]:
            if os.path.isdir(os.path.join(sp, "frida")):
                return sp
    except Exception:
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default=HERE, help="打包工作目录 (默认=脚本目录)")
    ap.add_argument("--name", default="EvoFree", help="产物 exe 名字")
    ap.add_argument("--py", default=sys.executable, help="用于打包的 python")
    ap.add_argument("--console", action="store_true", default=True)
    ap.add_argument("--uac-admin", action="store_true", default=True,
                    help="加 requireAdministrator 清单")
    a = ap.parse_args()

    PACK = os.path.abspath(a.pack)
    entry = os.path.join(PACK, "evofree_main.py")
    if not os.path.isfile(entry):
        print("找不到入口: %s" % entry)
        print("用 --pack 指向含 evofree_main.py 的目录")
        return 2

    for d in ("build", "dist"):
        p = os.path.join(PACK, d)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)

    sp = find_frida_site()
    args = [a.py, "-m", "PyInstaller",
            "--onefile", "--name", a.name, "--clean", "--noconfirm",
            "--paths", PACK]
    if a.console:
        args.append("--console")
    if a.uac_admin:
        args.append("--uac-admin")
    if sp:
        args += ["--paths", sp, "--hidden-import", "frida", "--collect-all", "frida"]
    emb = os.path.join(PACK, "_embed.py")
    if os.path.isfile(emb):
        args += ["--add-data", emb + ";."]
    args.append(entry)

    print("pack dir  :", PACK)
    print("python    :", a.py)
    print("frida sp  :", sp or "<not found - exe 需自行装 frida>")
    print("entry     :", entry)
    r = subprocess.run(args, cwd=PACK, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    logp = os.path.join(PACK, "build.log")
    io.open(logp, "w", encoding="utf-8").write(
        (r.stdout or "") + "\n=== STDERR ===\n" + (r.stderr or ""))
    print("EXIT", r.returncode, " log:", logp)
    for l in (r.stdout or "").strip().splitlines()[-8:]:
        print("  " + l)
    if r.returncode != 0:
        print("\n--- stderr tail ---")
        for l in (r.stderr or "").strip().splitlines()[-12:]:
            print("  " + l)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
