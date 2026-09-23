#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""代理池：成功率加权轮询 + 连败自动禁用。

移植自 lxf746/any-auto-register core/proxy_pool.py 的调度语义，
去掉 SQLModel 依赖，改用 JSON 落盘，便于单独跑。

代理条目: {"url": "http://user:pass@host:port", "region": "us", "ok": 0, "fail": 0, "active": true}
"""
from __future__ import annotations

import json
import os
import threading
import time

POOL_FILE = os.environ.get("PROXY_POOL_FILE", "proxies.json")
FAIL_DISABLE_THRESHOLD = 5


class ProxyPool:
    def __init__(self, path: str = POOL_FILE):
        self.path = path
        self._lock = threading.Lock()
        self._index = 0

    # ---------- 持久化 ----------

    def _load(self) -> list:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return []

    def _save(self, items: list) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(items, fh, indent=2, ensure_ascii=False)

    def add(self, url: str, region: str = "") -> None:
        with self._lock:
            items = self._load()
            if any(i["url"] == url for i in items):
                return
            items.append({"url": url, "region": region, "ok": 0, "fail": 0, "active": True})
            self._save(items)

    # ---------- 调度 ----------

    def get_next(self, region: str = "") -> str | None:
        with self._lock:
            items = [i for i in self._load()
                     if i.get("active", True) and (not region or i.get("region") == region)]
            if not items:
                return None
            # 成功率排序，同分保持原序，保证稳定轮询
            items.sort(key=lambda p: p["ok"] / max(p["ok"] + p["fail"], 1), reverse=True)
            url = items[self._index % len(items)]["url"]
            self._index += 1
            return url

    def report(self, url: str, success: bool) -> None:
        with self._lock:
            items = self._load()
            for i in items:
                if i["url"] != url:
                    continue
                if success:
                    i["ok"] += 1
                    i["fail"] = 0
                else:
                    i["fail"] += 1
                    if i["ok"] == 0 and i["fail"] >= FAIL_DISABLE_THRESHOLD:
                        i["active"] = False
                i["ts"] = int(time.time())
                break
            self._save(items)

    def check_all(self, test_url: str = "https://httpbin.org/ip", timeout: int = 8) -> dict:
        import requests
        stats = {"ok": 0, "fail": 0}
        for item in self._load():
            url = item["url"]
            try:
                r = requests.get(test_url, proxies={"http": url, "https": url}, timeout=timeout)
                good = r.status_code == 200
            except Exception:
                good = False
            self.report(url, good)
            stats["ok" if good else "fail"] += 1
        return stats


pool = ProxyPool()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        print(pool.check_all())
    elif len(sys.argv) > 1 and sys.argv[1] == "next":
        print(pool.get_next(sys.argv[2] if len(sys.argv) > 2 else ""))
    else:
        print("usage: proxy_pool.py check | next [region]")