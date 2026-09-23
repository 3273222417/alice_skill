#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenAI sentinel requirements / proof-of-work token 生成器。

移植自 verssache/chatgpt-creator internal/sentinel（Go）。
流程：POST sentinel/req 拿 challenge -> 若 proofofwork.required 则本地解 PoW -> 组装 token。
仅用于自有/授权环境的账号注册链路测试。
"""
from __future__ import annotations

import base64
import json
import random
import time
import uuid

SENTINEL_REQ = "https://sentinel.openai.com/backend-api/sentinel/req"
SENTINEL_FRAME = "https://sentinel.openai.com/sentinel/20260124ceb8/frame.html"
SDK_JS = "https://sentinel.openai.com/sentinel/20260124ceb8/sdk.js"

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)

_NAV_PROPS = [
    "vendorSub", "productSub", "vendor", "maxTouchPoints", "scheduling",
    "userActivation", "doNotTrack", "geolocation", "connection", "plugins",
    "mimeTypes", "pdfViewerEnabled", "webkitTemporaryStorage",
    "webkitPersistentStorage", "hardwareConcurrency", "cookieEnabled",
    "credentials", "mediaDevices", "permissions", "locks", "ink",
]
_PROBE_A = ["location", "implementation", "URL", "documentURI", "compatMode"]
_PROBE_B = ["Object", "Function", "Array", "Number", "parseFloat", "undefined"]


def fnv1a32(text: str) -> str:
    """32 位 FNV-1a + avalanche 收尾，与上游 Go/Python 参考实现逐字节一致。"""
    h = 2166136261
    for ch in text:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    h ^= h >> 16
    h = (h * 2246822507) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 3266489909) & 0xFFFFFFFF
    h ^= h >> 16
    return "%08x" % h


class SentinelTokenGenerator:
    def __init__(self, device_id: str = "", ua: str = ""):
        self.device_id = device_id or str(uuid.uuid4())
        self.ua = ua or DEFAULT_UA
        self.requirements_seed = "%f" % random.random()
        self.sid = str(uuid.uuid4())

    def get_config(self) -> list:
        now = time.gmtime()
        now_str = time.strftime("%a %b %d %Y %H:%M:%S GMT+0000 (Coordinated Universal Time)", now)
        perf_now = random.random() * 49000 + 1000
        time_origin = (time.time() * 1000) - perf_now
        nav_prop = random.choice(_NAV_PROPS)
        return [
            "1920x1080",
            now_str,
            4294705152,
            0,                       # nonce 占位，PoW 循环里替换
            self.ua,
            SDK_JS,
            None,
            None,
            "en-US",
            "en-US,en",
            random.random(),
            f"{nav_prop}-undefined",
            random.choice(_PROBE_A),
            random.choice(_PROBE_B),
            perf_now,
            self.sid,
            "",
            random.choice([4, 8, 12, 16]),
            time_origin,
        ]

    @staticmethod
    def _b64(data) -> str:
        return base64.b64encode(json.dumps(data, separators=(",", ":")).encode()).decode()

    def generate_requirements_token(self) -> str:
        config = self.get_config()
        config[3] = 1
        config[9] = random.randint(5, 50)
        return "gAAAAAC" + self._b64(config)

    def generate_token(self, seed: str = "", difficulty: str = "", max_iter: int = 500000) -> str:
        seed = seed or self.requirements_seed
        difficulty = difficulty or "0"
        start = time.time()
        config = self.get_config()
        for i in range(max_iter):
            config[3] = i
            config[9] = int((time.time() - start) * 1000)
            data = self._b64(config)
            if fnv1a32(seed + data)[: len(difficulty)] <= difficulty:
                return "gAAAAAB" + data + "~S"
        raise RuntimeError(f"PoW 未在 {max_iter} 次迭代内收敛，检查 difficulty={difficulty}")


def build_sentinel_token(session, device_id: str, flow: str, ua: str = "",
                         sec_ch_ua: str = "", impersonate: str = "") -> str:
    """完整流程：请求 challenge ->（必要时）解 PoW -> 返回可直接放进
    `openai-sentinel-token` 头的 JSON 字符串。"""
    gen = SentinelTokenGenerator(device_id, ua)
    headers = {
        "Content-Type": "text/plain;charset=UTF-8",
        "Referer": SENTINEL_FRAME,
        "Origin": "https://sentinel.openai.com",
        "User-Agent": gen.ua,
        "sec-ch-ua": sec_ch_ua or '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "oai-device-id": device_id,
        "oai-language": "en-US",
    }
    body = {"p": gen.generate_requirements_token(), "id": device_id, "flow": flow}
    resp = session.post(SENTINEL_REQ, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    challenge = resp.json()

    c_value = challenge.get("token", "")
    pow_data = challenge.get("proofofwork") or {}
    if pow_data.get("required") and pow_data.get("seed"):
        p_value = gen.generate_token(pow_data["seed"], str(pow_data.get("difficulty", "0")))
    else:
        p_value = gen.generate_requirements_token()

    return json.dumps({"p": p_value, "t": "", "c": c_value, "id": device_id, "flow": flow})


if __name__ == "__main__":
    g = SentinelTokenGenerator()
    print("requirements:", g.generate_requirements_token()[:80], "...")
    print("fnv1a32('hello') =", fnv1a32("hello"))