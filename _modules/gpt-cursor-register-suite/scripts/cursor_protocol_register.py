#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cursor 五步协议注册（Next.js Server Action 链路）。

移植自 lxf746/any-auto-register platforms/cursor/core.py。
ACTION_* 三个 Server Action ID 会随 Cursor 前端版本更新，跑挂先重新提取。
依赖: pip install curl_cffi
"""
from __future__ import annotations

import json
import random
import re
import string
import urllib.parse
import uuid

AUTH = "https://authenticator.cursor.sh"
CURSOR = "https://cursor.com"

ACTION_SUBMIT_EMAIL = "d0b05a2a36fbe69091c2f49016138171d5c1e4cd"
ACTION_SUBMIT_PASSWORD = "fef846a39073c935bea71b63308b177b113269b7"
ACTION_MAGIC_CODE = "f9e8ae3d58a7cd11cccbcdbf210e6f2a6a2550dd"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36")

TURNSTILE_SITEKEY = "0x4AAAAAAAMNIvC45A4Wjjln"

# (sign-in) 路由树，URL 编码后进 next-router-state-tree 头
ROUTER_STATE_TREE = (
    '%5B%22%22%2C%7B%22children%22%3A%5B%22(main)%22%2C%7B%22children%22%3A'
    '%5B%22(root)%22%2C%7B%22children%22%3A%5B%22(sign-in)%22%2C%7B%22children%22'
    '%3A%5B%22__PAGE__%22%2C%7B%7D%5D%7D%5D%7D%5D%7D%5D%7D%5D'
)


def rand_password(n: int = 16) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits + "!@#$", k=n))


def _boundary() -> str:
    return "----WebKitFormBoundary" + "".join(
        random.choices(string.ascii_letters + string.digits, k=16))


def _multipart(fields: dict, boundary: str) -> bytes:
    parts = []
    for name, value in fields.items():
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        )
    parts.append(f"--{boundary}--\r\n")
    return "".join(parts).encode()


class CursorRegister:
    def __init__(self, proxy: str | None = None, log_fn=print):
        from curl_cffi import requests as curl_req
        self.log = log_fn
        # safari17_0 指纹与上游一致：Cursor 对 Chrome 指纹的校验更严
        self.s = curl_req.Session(impersonate="safari17_0")
        if proxy:
            self.s.proxies = {"http": proxy, "https": proxy}

    def _headers(self, next_action: str, referer: str, boundary: str | None = None) -> dict:
        ct = (f"multipart/form-data; boundary={boundary}" if boundary
              else "application/x-www-form-urlencoded")
        return {
            "user-agent": UA,
            "accept": "text/x-component",
            "content-type": ct,
            "origin": AUTH,
            "referer": referer,
            "next-action": next_action,
            "next-router-state-tree": ROUTER_STATE_TREE,
        }

    def step1_get_session(self):
        nonce = str(uuid.uuid4())
        state = {"returnTo": "https://cursor.com/dashboard", "nonce": nonce}
        # 双层编码：Cursor 前端会把 state 再解一次
        state_encoded = urllib.parse.quote(urllib.parse.quote(json.dumps(state, separators=(",", ":"))))
        self.s.get(f"{AUTH}/?state={state_encoded}",
                   headers={"user-agent": UA, "accept": "text/html"}, allow_redirects=True)
        self.log("Step1 完成：session 已建立")
        return state_encoded

    def step2_submit_email(self, email: str, state_encoded: str):
        bd = _boundary()
        referer = f"{AUTH}/sign-up?state={state_encoded}"
        body = _multipart({"1_state": state_encoded, "email": email}, bd)
        self.s.post(f"{AUTH}/sign-up",
                    headers=self._headers(ACTION_SUBMIT_EMAIL, referer, bd),
                    data=body, allow_redirects=False)
        self.log(f"Step2 完成：已提交邮箱 {email}")

    def step3_submit_password(self, password: str, email: str, state_encoded: str,
                              captcha_solver=None):
        captcha_token = ""
        if captcha_solver:
            self.log("获取 Turnstile token...")
            captcha_token = captcha_solver.solve_turnstile(AUTH, TURNSTILE_SITEKEY)
        bd = _boundary()
        referer = f"{AUTH}/sign-up?state={state_encoded}"
        body = _multipart({
            "1_state": state_encoded, "email": email,
            "password": password, "captchaToken": captcha_token,
        }, bd)
        self.s.post(f"{AUTH}/sign-up",
                    headers=self._headers(ACTION_SUBMIT_PASSWORD, referer, bd),
                    data=body, allow_redirects=False)
        self.log("Step3 完成：密码 + Turnstile 已提交")

    def step4_submit_otp(self, otp: str, email: str, state_encoded: str) -> str:
        bd = _boundary()
        referer = f"{AUTH}/sign-up?state={state_encoded}"
        body = _multipart({"1_state": state_encoded, "email": email, "otp": otp}, bd)
        r = self.s.post(f"{AUTH}/sign-up",
                        headers=self._headers(ACTION_MAGIC_CODE, referer, bd),
                        data=body, allow_redirects=False)
        loc = r.headers.get("location", "")
        m = re.search(r"code=([\w-]+)", loc)
        auth_code = m.group(1) if m else ""
        self.log(f"Step4 完成：auth_code={auth_code[:12]}..." if auth_code else "Step4 失败：未取到 code")
        return auth_code

    def step5_get_token(self, auth_code: str, state_encoded: str) -> str:
        url = f"{CURSOR}/api/auth/callback?code={auth_code}&state={state_encoded}"
        self.s.get(url, headers={"user-agent": UA, "accept": "text/html"}, allow_redirects=False)
        self.s.get(url, headers={"user-agent": UA}, allow_redirects=True)
        for cookie in self.s.cookies.jar:
            if cookie.name == "WorkosCursorSessionToken":
                self.log("Step5 完成：已取得 WorkosCursorSessionToken")
                return urllib.parse.unquote(cookie.value)
        raise RuntimeError("未取到 WorkosCursorSessionToken，检查 state 是否被复用")


def register(email: str, otp_getter, password: str = "", proxy: str = "",
             captcha_solver=None, log_fn=print) -> dict:
    """一次完整注册。otp_getter 是无参可调用，返回 6 位验证码字符串。"""
    cli = CursorRegister(proxy=proxy or None, log_fn=log_fn)
    pwd = password or rand_password()
    state = cli.step1_get_session()
    cli.step2_submit_email(email, state)
    cli.step3_submit_password(pwd, email, state, captcha_solver)
    otp = otp_getter()
    if not otp:
        raise RuntimeError("未取得邮箱验证码")
    code = cli.step4_submit_otp(otp, email, state)
    token = cli.step5_get_token(code, state)
    return {"email": email, "password": pwd, "token": token,
            "fmt": f"{email}|{pwd}|{token}"}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: cursor_protocol_register.py <email>")
        raise SystemExit(2)
    print(register(sys.argv[1], lambda: input("OTP: ").strip()))