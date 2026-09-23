#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenAI 纯协议注册链（Go 版 chatgpt-creator 的 Python 移植）。

依赖: pip install curl_cffi
流程: 首页 -> CSRF -> signin -> authorize -> register -> send OTP -> validate OTP
      -> create_account(带 sentinel token) -> callback
每一步之间带随机延时，这是过风控的必要动作。
"""
from __future__ import annotations

import json
import random
import re
import string
import time
import uuid

from openai_sentinel_pow import build_sentinel_token, SentinelTokenGenerator

BASE = "https://chatgpt.com"
AUTH = "https://auth.openai.com"

DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36")
SEC_CH_UA = '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"'


def _new_session(proxy: str = ""):
    from curl_cffi import requests as curl_req
    s = curl_req.Session(impersonate="chrome131")
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def rand_password(n: int = 14) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits + "!@#$", k=n))


def rand_name() -> str:
    first = random.choice(["James", "Olivia", "Liam", "Emma", "Noah", "Ava", "Ethan", "Mia"])
    last = random.choice(["Smith", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore"])
    return f"{first} {last}"


def rand_birthdate() -> str:
    return f"{random.randint(1975, 2003):04d}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"


class OpenAIRegister:
    def __init__(self, proxy: str = "", ua: str = "", log_fn=print):
        self.log = log_fn
        self.ua = ua or DEFAULT_UA
        self.device_id = str(uuid.uuid4())
        self.s = _new_session(proxy)
        self.s.cookies.set("oai-did", self.device_id, domain="chatgpt.com")

    def _h(self, extra: dict | None = None) -> dict:
        base = {
            "User-Agent": self.ua,
            "Accept-Language": "en-US,en;q=0.9",
            "sec-ch-ua": SEC_CH_UA,
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        base.update(extra or {})
        return base

    @staticmethod
    def _delay(low: float = 0.2, high: float = 1.5) -> None:
        time.sleep(low + random.random() * (high - low))

    def visit_homepage(self) -> None:
        for attempt in range(3):
            r = self.s.get(f"{BASE}/", headers=self._h({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1"}), timeout=30)
            self.log(f"Visit Homepage (Try {attempt + 1}) | {r.status_code}")
            if r.status_code in (200, 302, 307):
                return
            time.sleep(1)
        raise RuntimeError("首页访问连续失败")

    def get_csrf(self) -> str:
        r = self.s.get(f"{BASE}/api/auth/csrf",
                       headers=self._h({"Accept": "application/json", "Referer": f"{BASE}/"}),
                       timeout=30)
        token = r.json().get("csrfToken", "")
        if not token:
            raise RuntimeError("csrfToken 为空")
        self.log(f"Get CSRF | {r.status_code}")
        return token

    def signin(self, email: str, csrf: str) -> str:
        params = {
            "prompt": "login",
            "ext-oai-did": self.device_id,
            "auth_session_logging_id": str(uuid.uuid4()),
            "screen_hint": "login_or_signup",
            "login_hint": email,
        }
        r = self.s.post(f"{BASE}/api/auth/signin/openai", params=params,
                        data={"callbackUrl": f"{BASE}/", "csrfToken": csrf, "json": "true"},
                        headers=self._h({"Accept": "application/json",
                                         "Referer": f"{BASE}/", "Origin": BASE}),
                        timeout=30)
        url = r.json().get("url", "")
        if not url:
            raise RuntimeError(f"未拿到 authorize url: {r.text[:200]}")
        self.log(f"Signin | {r.status_code}")
        return url

    def authorize(self, auth_url: str) -> str:
        r = self.s.get(auth_url, headers=self._h({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": f"{BASE}/", "Upgrade-Insecure-Requests": "1"}),
            timeout=30, allow_redirects=True)
        self.log(f"Authorize | {r.status_code}")
        return str(r.url)

    def register(self, email: str, password: str) -> dict:
        r = self.s.post(f"{AUTH}/api/accounts/user/register",
                        json={"username": email, "password": password},
                        headers=self._h({"Content-Type": "application/json",
                                         "Accept": "application/json",
                                         "Referer": f"{AUTH}/create-account/password",
                                         "Origin": AUTH}),
                        timeout=30)
        self.log(f"Register | {r.status_code}")
        return r.json() if r.text else {}

    def send_otp(self) -> dict:
        r = self.s.post(f"{AUTH}/api/accounts/email-otp/send",
                        headers=self._h({"Accept": "application/json",
                                         "Referer": f"{AUTH}/create-account/password",
                                         "Origin": AUTH}), timeout=30)
        self.log(f"Send OTP | {r.status_code}")
        return r.json() if r.text else {}

    def validate_otp(self, otp: str) -> dict:
        r = self.s.post(f"{AUTH}/api/accounts/email-otp/validate",
                        json={"code": otp},
                        headers=self._h({"Content-Type": "application/json",
                                         "Accept": "application/json",
                                         "Referer": f"{AUTH}/email-verification",
                                         "Origin": AUTH}), timeout=30)
        self.log(f"Validate OTP [{otp}] | {r.status_code}")
        return r.json() if r.text else {}

    def create_account(self, name: str, birthdate: str, flow: str = "create_account") -> dict:
        # sentinel token 是这一步的硬门槛，缺了必被拒
        token = build_sentinel_token(self.s, self.device_id, flow, self.ua, SEC_CH_UA)
        r = self.s.post(f"{AUTH}/api/accounts/create_account",
                        json={"name": name, "birthdate": birthdate},
                        headers=self._h({"Content-Type": "application/json",
                                         "Accept": "application/json",
                                         "Referer": f"{AUTH}/about-you",
                                         "Origin": AUTH,
                                         "openai-sentinel-token": token}),
                        timeout=30)
        self.log(f"Create Account | {r.status_code}")
        return r.json() if r.text else {}

    def callback(self, url: str) -> int:
        r = self.s.get(url, headers=self._h({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1"}), timeout=30, allow_redirects=True)
        self.log(f"Callback | {r.status_code}")
        return r.status_code

    def run(self, email: str, otp_getter, password: str = "") -> dict:
        pwd = password or rand_password()
        self.visit_homepage(); self._delay(0.3, 0.8)
        csrf = self.get_csrf(); self._delay(0.2, 0.5)
        auth_url = self.signin(email, csrf); self._delay(0.3, 0.8)
        final = self.authorize(auth_url); self._delay(0.3, 0.8)
        path = final.split("?", 1)[0]

        if "create-account/password" in path:
            self._delay(0.5, 1.0)
            self.register(email, pwd); self._delay(0.3, 0.8)
            self.send_otp()
        elif "email-verification" not in path and "email-otp" not in path \
                and "about-you" not in path and "callback" not in final:
            self.log(f"未知跳转，按注册路径兜底: {final}")
            self.register(email, pwd)
            self.send_otp()

        if "about-you" not in path:
            otp = otp_getter()
            if not otp:
                raise RuntimeError("未取得验证码")
            self._delay(0.3, 0.8)
            res = self.validate_otp(otp)
            if not res and "error" in str(res).lower():
                self.log("验证码失败，重发一次")
                self.send_otp(); self._delay(1.0, 2.0)
                self.validate_otp(otp_getter())

        self._delay(0.5, 1.5)
        data = self.create_account(rand_name(), rand_birthdate())
        cb = data.get("continue_url") or data.get("url") or data.get("redirect_url") or ""
        if cb:
            self._delay(0.2, 0.5)
            self.callback(cb)
        return {"email": email, "password": pwd, "flow": final}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: openai_protocol_register.py <email> [password]")
        raise SystemExit(2)
    reg = OpenAIRegister()
    print(reg.run(sys.argv[1],
                  lambda: input("OTP: ").strip(),
                  sys.argv[2] if len(sys.argv) > 2 else ""))