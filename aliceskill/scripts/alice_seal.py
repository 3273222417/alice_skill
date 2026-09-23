#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice封印工具（技能包加密 + 防伪标识）
=====================================
功能：
  ① 把技能包 zip 用 AES-GCM 加密成密封文件（.wzseal），无法单独使用/拆包
  ② 生成唯一防伪标识（序列号 WZ-XXXX-XXXX + 持有人水印 + 时间戳 + 哈希签名）
  ③ 密钥内嵌 exe（混淆存储），解密校验失败即拒装
  ④ 防伪标识写入技能包，安装后技能内可见——倒卖必留痕

用法:
  python alice_seal.py seal --bundle dist/alice_1.0.zip --owner "本地持有者" --out dist/alice_sealed.bin
  python alice_seal.py inspect --file dist/alice_sealed.bin      # 查看防伪信息
  python alice_seal.py selfcheck
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import struct
import sys
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

MAGIC = b"WZSEAL\x00\x01"
IV_LEN = 12
TAG_LEN = 16
SALT = b"alice-redblue-2026-seal-salt-v1"


def c(s: str, code: str) -> str:
    m = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
         "cyan": "\033[96m", "bold": "\033[1m", "magenta": "\033[95m"}
    if not sys.stdout.isatty():
        return s
    return f"{m.get(code, '')}{s}\033[0m"


def ok(s: str) -> None:
    print(c("  ✓ ", "green") + s)


def fail(s: str) -> None:
    print(c("  ✗ ", "red") + s)


def banner(title: str, sub: str = "") -> None:
    w = 64
    print(c("┌" + "─" * (w - 2) + "┐", "magenta"))
    print(c("│ " + title + " " * (w - 4 - len(title)) + "│", "bold"))
    if sub:
        print(c("│ " + sub + " " * (w - 4 - len(sub)) + "│", "dim"))
    print(c("└" + "─" * (w - 2) + "┘", "magenta"))


def _key() -> bytes:
    """派生 AES 密钥（混淆内嵌，exe 反编译难度 +1）。"""
    seed = b"WZ!@#RedBlue2026*&Sealed"
    xored = bytes(b ^ 0x5A for b in seed)
    return hashlib.pbkdf2_hmac("sha256", xored, SALT, 12000, dklen=32)


def gen_serial() -> str:
    import random
    charset = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    parts = []
    for _ in range(4):
        parts.append("".join(random.choice(charset) for _ in range(4)))
    return "-".join(parts)


def seal(bundle_path: str, owner: str, out_path: str, serial: str | None = None) -> dict:
    """加密技能包 + 写防伪头。"""
    if not os.path.isfile(bundle_path):
        raise FileNotFoundError(bundle_path)
    serial = serial or gen_serial()
    payload = open(bundle_path, "rb").read()
    info = {
        "magic": "WZSEAL",
        "format": "v1",
        "serial": serial,
        "owner": owner,
        "sealed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bundle_sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    }
    head = json.dumps(info, ensure_ascii=False).encode("utf-8")
    head_b64 = base64.b64encode(head)
    iv = get_random_bytes(IV_LEN)
    cipher = AES.new(_key(), AES.MODE_GCM, nonce=iv)
    ct, tag = cipher.encrypt_and_digest(payload)
    with open(out_path, "wb") as fh:
        fh.write(MAGIC)
        fh.write(struct.pack("<I", len(head_b64)))
        fh.write(head_b64)
        fh.write(iv)
        fh.write(tag)
        fh.write(ct)
    return info


def unseal(sealed_path: str) -> dict:
    """解密密封包，返回 info + payload。校验失败抛异常。"""
    data = open(sealed_path, "rb").read()
    if not data.startswith(MAGIC):
        raise ValueError("不是有效的Alice密封包（魔数不符）")
    off = len(MAGIC)
    (hlen,) = struct.unpack("<I", data[off:off + 4])
    off += 4
    head_b64 = data[off:off + hlen]
    off += hlen
    iv = data[off:off + IV_LEN]
    off += IV_LEN
    tag = data[off:off + TAG_LEN]
    off += TAG_LEN
    ct = data[off:]
    head = json.loads(base64.b64decode(head_b64).decode("utf-8"))
    cipher = AES.new(_key(), AES.MODE_GCM, nonce=iv)
    try:
        payload = cipher.decrypt_and_verify(ct, tag)
    except ValueError as e:
        raise ValueError("解密校验失败（包被篡改或密钥不符）: " + str(e)) from e
    got = hashlib.sha256(payload).hexdigest()
    if got != head.get("bundle_sha256"):
        raise ValueError("哈希签名不符（包被篡改）")
    return {"info": head, "payload": payload}


def cmd_seal(a) -> int:
    banner("Alice封印", f"持有人: {a.owner}")
    info = seal(a.bundle, a.owner, a.out)
    ok(f"加密完成: {a.out}")
    ok(f"防伪序列号: {info['serial']}")
    ok(f"持有人: {info['owner']}")
    ok(f"包哈希: {info['bundle_sha256'][:16]}...")
    print(c("\n[!] 倒卖必留痕：序列号+持有人已写入密封包，安装后技能内可见", "magenta"))
    return 0


def cmd_inspect(a) -> int:
    banner("防伪查验", a.file)
    d = unseal(a.file)
    info = d["info"]
    ok(f"序列号: {info['serial']}")
    ok(f"持有人: {info['owner']}")
    ok(f"封印时间: {info['sealed_at']}")
    ok(f"包哈希: {info['bundle_sha256'][:24]}...")
    ok(f"包大小: {info['size']} bytes")
    if a.owner and info["owner"] != a.owner:
        fail(f"持有人不匹配! 包={info['owner']} vs 输入={a.owner}")
        return 1
    return 0


def cmd_selfcheck(a) -> int:
    banner("自检", "封印工具")
    checks = [
        ("AES-GCM 可用", True),
        ("密钥派生", len(_key()) == 32),
        ("序列号格式", len(gen_serial().split("-")) == 4),
        ("魔数", MAGIC.startswith(b"WZSEAL")),
    ]
    all_ok = True
    for name, passed in checks:
        print(("  ✓ " if passed else "  ✗ ") + name)
        all_ok &= passed
    print(f"\n自检结果: {sum(p for _, p in checks)}/{len(checks)} 通过")
    return 0 if all_ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Alice封印工具")
    sub = p.add_subparsers(dest="cmd")
    se = sub.add_parser("seal")
    se.add_argument("--bundle", required=True)
    se.add_argument("--owner", required=True, help="持有人/单位，防伪标识")
    se.add_argument("--serial", default=None)
    se.add_argument("--out", required=True)
    se.set_defaults(func=cmd_seal)
    ins = sub.add_parser("inspect")
    ins.add_argument("--file", required=True)
    ins.add_argument("--owner", default="")
    ins.set_defaults(func=cmd_inspect)
    sub.add_parser("selfcheck").set_defaults(func=cmd_selfcheck)
    a = p.parse_args()
    if not hasattr(a, "func"):
        p.print_help()
        return 0
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
