#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""邮箱接码：tempmail.plus 与 generator.email 双通道取 6 位 OTP。

通道 A（推荐，来自 ddCat-main / any-auto-register）：自有域名 → Cloudflare catch-all
转发到 tempmail.plus，再读其 REST API。
通道 B（来自 verssache/chatgpt-creator）：直接读 generator.email 页面，
必须显式带 Cookie: surl=<domain>/<user>，域被拉黑时自动落盘黑名单。
"""
from __future__ import annotations

import json
import os
import random
import re
import string
import time

OTP_RE = re.compile(r"\b(\d{6})\b")
BLACKLIST_FILE = "blacklist.json"


# ---------- 通道 A: tempmail.plus ----------

class TempMailPlus:
    def __init__(self, username: str, domain: str, pin: str = "", proxy: str = ""):
        self.username, self.domain, self.pin = username, domain, pin
        self.session = _new_session(proxy)

    def list_mails(self, limit: int = 20) -> dict:
        url = (f"https://tempmail.plus/api/mails?email={self.username}%40{self.domain}"
               f"&limit={limit}&epin={self.pin}")
        r = self.session.get(url, timeout=30)
        return r.json()

    def check(self) -> bool:
        """result 为 true 才算连通（上游踩过的坑：布尔判断写反会误报失败）。"""
        try:
            return self.list_mails().get("result") is True
        except Exception:
            return False

    def fetch_otp(self, max_retries: int = 20, delay: float = 3.0) -> str:
        seen = set()
        for _ in range(max_retries):
            try:
                data = self.list_mails()
                for mail in data.get("mail_list", []) or []:
                    mid = mail.get("id") or mail.get("mail_id")
                    if mid in seen:
                        continue
                    seen.add(mid)
                    blob = json.dumps(mail, ensure_ascii=False)
                    m = OTP_RE.search(blob)
                    if m and m.group(1) != "177010":
                        return m.group(1)
            except Exception:
                pass
            time.sleep(delay)
        raise TimeoutError(f"tempmail.plus 在 {max_retries} 次轮询内未取得验证码")


# ---------- 通道 B: generator.email ----------

def _new_session(proxy: str = ""):
    from curl_cffi import requests as curl_req
    s = curl_req.Session(impersonate="chrome131")
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def _load_blacklist() -> set:
    if os.path.exists(BLACKLIST_FILE):
        try:
            return set(json.load(open(BLACKLIST_FILE, encoding="utf-8")))
        except Exception:
            pass
    return set()


def _save_blacklist(domains: set) -> None:
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as fh:
        json.dump(sorted(domains), fh, indent=2)


def add_blacklist_domain(domain: str) -> None:
    bl = _load_blacklist()
    bl.add(domain)
    _save_blacklist(bl)


def create_generator_email(default_domain: str = "", proxy: str = "") -> str:
    """建临时邮箱；给了 default_domain 就本地拼名（跳过页面抓取，快得多）。"""
    local = "".join(random.choices(string.ascii_lowercase, k=5))
    first = random.choice(["james", "olivia", "liam", "emma", "noah", "ava", "mia", "ethan"])
    last = random.choice(["smith", "jones", "brown", "davis", "miller", "wilson", "moore"])
    if default_domain:
        return f"{first}{last}{local}@{default_domain}"

    s = _new_session(proxy)
    resp = s.get("https://generator.email/", timeout=30)
    resp.raise_for_status()
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        domains = [p.get_text(strip=True) for p in soup.select(".e7m.tt-suggestions div > p")]
    except Exception:
        domains = re.findall(r"[\w.-]+\.(?:com|de|net|org)", resp.text)
    domains = [d for d in domains if d and d not in _load_blacklist()]
    domains += ["smartmail.de", "enayu.com", "crazymailing.com"]
    return f"{first}{last}{local}@{random.choice(domains)}"


def fetch_generator_otp(email: str, max_retries: int = 20, delay: float = 3.0,
                        proxy: str = "") -> str:
    """从 generator.email 读验证码。Cookie: surl=<domain>/<user> 是关键，缺了必空。"""
    username, _, domain = email.partition("@")
    s = _new_session(proxy)
    for _ in range(max_retries):
        try:
            r = s.get(f"https://generator.email/{domain}/{username}",
                      headers={"Cookie": f"surl={domain}/{username}"}, timeout=30)
            if r.status_code == 200:
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(r.text, "html.parser")
                    for node in soup.select("#email-table div.subj_div_45g45gg"):
                        m = OTP_RE.search(node.get_text())
                        if m and m.group(1) != "177010":
                            return m.group(1)
                except Exception:
                    m = OTP_RE.search(r.text)
                    if m and m.group(1) != "177010":
                        return m.group(1)
        except Exception:
            pass
        time.sleep(delay)
    raise TimeoutError(f"generator.email 在 {max_retries} 次轮询内未取得验证码")


def get_otp(email: str, channel: str = "auto", pin: str = "", proxy: str = "",
            max_retries: int = 20, delay: float = 3.0) -> str:
    """统一入口。channel: auto | tempmail_plus | generator_email。"""
    if channel in ("auto", "tempmail_plus"):
        try:
            username, _, domain = email.partition("@")
            return TempMailPlus(username, domain, pin, proxy).fetch_otp(max_retries, delay)
        except Exception:
            if channel == "tempmail_plus":
                raise
    return fetch_generator_otp(email, max_retries, delay, proxy)


if __name__ == "__main__":
    import sys
    print(fetch_generator_otp(sys.argv[1]) if len(sys.argv) > 1 else "usage: mailbox_otp.py <email>")