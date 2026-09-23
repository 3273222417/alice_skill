#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cursor 授权注入 + 机器指纹复位（跨 Win/mac/Linux）。

授权注入移植自 ddCat-main/cursor-auto-register cursor_auth_manager.py；
机器指纹复位来自 reset_machine.py（四项 telemetry 标识）。

用法:
  # 查询当前内置账号
  python cursor_auth_inject.py show
  # 注入 token
  python cursor_auth_inject.py inject --email a@b.com --access <token> --refresh <token>
  # 只复位机器指纹
  python cursor_auth_inject.py reset-id
  # 注入 + 复位 + 备份
  python cursor_auth_inject.py apply --email a@b.com --access <token>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
import uuid

APP_NAME = "Cursor"


def state_vscdb_path() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        if not base:
            raise EnvironmentError("APPDATA 未设置")
        return os.path.join(base, APP_NAME, "User", "globalStorage", "state.vscdb")
    if sys.platform == "darwin":
        return os.path.expanduser(
            f"~/Library/Application Support/{APP_NAME}/User/globalStorage/state.vscdb")
    return os.path.expanduser(
        f"~/.config/{APP_NAME}/User/globalStorage/state.vscdb")


def storage_json_path() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        if not base:
            raise EnvironmentError("APPDATA 未设置")
        return os.path.join(base, APP_NAME, "User", "globalStorage", "storage.json")
    if sys.platform == "darwin":
        return os.path.expanduser(
            f"~/Library/Application Support/{APP_NAME}/User/globalStorage/storage.json")
    return os.path.expanduser(
        f"~/.config/{APP_NAME}/User/globalStorage/storage.json")


def backup(path: str) -> str:
    """改动前必备份，带时间戳，可回滚。"""
    if not os.path.exists(path):
        return ""
    dst = f"{path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(path, dst)
    return dst


def ensure_cursor_closed() -> None:
    """Cursor 运行中会覆写 state.vscdb，必须先退出。"""
    if sys.platform == "win32":
        import subprocess
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Cursor.exe"],
                             capture_output=True, text=True).stdout
        if "Cursor.exe" in out:
            raise RuntimeError("检测到 Cursor.exe 正在运行，请先退出 Cursor 再注入")
    else:
        if os.popen("pgrep -f 'Cursor'").read().strip():
            raise RuntimeError("检测到 Cursor 进程，请先退出再注入")


# ---------- 授权注入 ----------

def read_auth() -> dict:
    path = state_vscdb_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到 Cursor 状态库（可能未安装 Cursor）: {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM itemTable WHERE key LIKE 'cursorAuth/%'")
        return {k: (v.decode() if isinstance(v, bytes) else v) for k, v in cur.fetchall()}
    finally:
        conn.close()


def update_auth(email: str | None = None, access_token: str | None = None,
                refresh_token: str | None = None, skip_check: bool = False) -> bool:
    if not skip_check:
        ensure_cursor_closed()
    path = state_vscdb_path()
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    bk = backup(path)

    # cachedSignUpType=Auth_0 是绕过「新设备试用判定」的关键字段
    updates = [("cursorAuth/cachedSignUpType", "Auth_0")]
    if email:
        updates.append(("cursorAuth/cachedEmail", email))
    if access_token:
        updates.append(("cursorAuth/accessToken", access_token))
    if refresh_token:
        updates.append(("cursorAuth/refreshToken", refresh_token))

    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        for key, value in updates:
            cur.execute("SELECT COUNT(*) FROM itemTable WHERE key = ?", (key,))
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO itemTable (key, value) VALUES (?, ?)", (key, value))
            else:
                cur.execute("UPDATE itemTable SET value = ? WHERE key = ?", (value, key))
        conn.commit()
    finally:
        conn.close()
    print(f"授权已写入（备份: {bk}）")
    return True


# ---------- 机器指纹复位 ----------

def generate_new_ids() -> dict:
    return {
        "telemetry.devDeviceId": str(uuid.uuid4()),
        "telemetry.macMachineId": hashlib.sha512(os.urandom(64)).hexdigest(),
        "telemetry.machineId": hashlib.sha256(os.urandom(32)).hexdigest(),
        "telemetry.sqmId": "{" + str(uuid.uuid4()).upper() + "}",
    }


def reset_machine_ids() -> bool:
    path = storage_json_path()
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    bk = backup(path)
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    new_ids = generate_new_ids()
    cfg.update(new_ids)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=4)
    print(f"机器标识已复位（备份: {bk}）")
    for k, v in new_ids.items():
        print(f"  {k} = {v}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Cursor 授权注入 / 机器指纹复位")
    ap.add_argument("action", choices=["show", "inject", "reset-id", "apply"])
    ap.add_argument("--email", default=None)
    ap.add_argument("--access", default=None)
    ap.add_argument("--refresh", default=None)
    ap.add_argument("--force", action="store_true", help="跳过 Cursor 进程检查")
    a = ap.parse_args()

    if a.action == "show":
        print(json.dumps(read_auth(), indent=2, ensure_ascii=False))
        return 0
    if a.action == "reset-id":
        return 0 if reset_machine_ids() else 1
    if a.action in ("inject", "apply"):
        update_auth(a.email, a.access, a.refresh, skip_check=a.force)
        if a.action == "apply":
            reset_machine_ids()
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())