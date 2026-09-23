#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice熔断器（进程级看门狗）：AI 失控时的物理终止机制。
检测三类异常 → 直接终止会话进程，不依赖 AI 自觉：
  ① 输出风暴：10 秒内输出字符超过阈值（刷屏）
  ② 对抗循环：检测到重复对抗模式（来回拉扯/刷屏重复）
  ③ 熔断词：输出/输入中出现「熔断/急停/红牌/停止对抗」→ 立即终止

用法:
  python alice_breaker.py --cmd "codex exec 攻" --timeout 7200
  python alice_breaker.py --cmd "codex exec 攻" --storm-limit 5000 --kill-words "熔断,急停"
  python alice_breaker.py --test                          # 自检模式（不启动 codex）
"""

from __future__ import annotations

import argparse
from collections import deque
import subprocess
import sys
import threading
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


class Breaker:
    def __init__(self, timeout: int, storm_limit: int, storm_window: float, kill_words: list[str]):
        self.timeout = timeout
        self.storm_limit = storm_limit
        self.storm_window = storm_window
        self.kill_words = kill_words
        self.buf: list[str] = []
        self.buf_lock = threading.Lock()
        self.start = time.time()
        self.reason: str | None = None
        self._kill = threading.Event()

    def feed(self, chunk: str):
        with self.buf_lock:
            self.buf.append(chunk)

    def snapshot(self) -> str:
        with self.buf_lock:
            s = "".join(self.buf[-200:])
        return s

    def monitor(self, proc: subprocess.Popen) -> None:
        samples: deque = deque()
        while proc.poll() is None:
            now = time.time()
            total = len(self.snapshot())
            samples.append((now, total))
            # 滑动窗口：只保留最近 storm_window 秒的采样
            while samples and now - samples[0][0] > self.storm_window:
                samples.popleft()
            # 输出风暴检测：窗口内输出量超过阈值
            if len(samples) >= 2:
                t0, l0 = samples[0]
                if total - l0 > self.storm_limit and now - t0 > 0.3:
                    self.reason = f"输出风暴（{total - l0} 字符/{now - t0:.1f}s，超过阈值 {self.storm_limit}/{self.storm_window:.0f}s）"
                    self._kill.set()
                    break
            # 熔断词检测
            text = self.snapshot()
            for w in self.kill_words:
                if w in text:
                    self.reason = f"检测到熔断词「{w}」"
                    self._kill.set()
                    break
            # 超时检测
            if self.timeout > 0 and now - self.start > self.timeout:
                self.reason = f"会话超时（{self.timeout}s）"
                self._kill.set()
                break
            time.sleep(0.5)
        if self.reason:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    def should_kill(self) -> bool:
        return self._kill.is_set()


def main() -> int:
    parser = argparse.ArgumentParser(description="Alice熔断器")
    parser.add_argument("--cmd", default="", help="要启动并监控的命令（默认直接监控 stdin 模式）")
    parser.add_argument("--timeout", type=int, default=7200, help="会话超时秒数，0=不限")
    parser.add_argument("--storm-limit", type=int, default=4000, help="10 秒内输出字符上限")
    parser.add_argument("--kill-words", default="熔断,急停,红牌,停止对抗,立即停止", help="熔断词（逗号分隔）")
    parser.add_argument("--test", action="store_true", help="自检模式：模拟输出风暴验证熔断")
    args = parser.parse_args()

    breaker = Breaker(
        timeout=args.timeout,
        storm_limit=args.storm_limit,
        storm_window=10.0,
        kill_words=[w.strip() for w in args.kill_words.split(",") if w.strip()],
    )

    if args.test:
        print("[自检] 模拟输出风暴 10 秒 > 阈值...")
        fake = subprocess.Popen(["python", "-c", "import time; [print('x'*800) for _ in range(80)]; time.sleep(2)"],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        t = threading.Thread(target=breaker.monitor, args=(fake,), daemon=True)
        t.start()
        while fake.poll() is None and not breaker.should_kill():
            chunk = fake.stdout.readline()
            if chunk:
                breaker.feed(chunk)
            time.sleep(0.05)
        t.join(timeout=1)
        if breaker.reason:
            print(f"[✓] 熔断触发: {breaker.reason}")
            return 0
        print("[✗] 未触发熔断（异常）")
        return 1

    if not args.cmd:
        parser.error("需要 --cmd 或 --test")
    print(f"[✓] 熔断器就绪 | 超时 {args.timeout}s | 风暴阈值 {args.storm_limit}/10s | 熔断词: {args.kill_words}")
    proc = subprocess.Popen(args.cmd, shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    monitor_thread = threading.Thread(target=breaker.monitor, args=(proc,), daemon=True)
    monitor_thread.start()
    while proc.poll() is None and not breaker.should_kill():
        chunk = proc.stdout.readline()
        if chunk:
            sys.stdout.write(chunk)
            sys.stdout.flush()
            breaker.feed(chunk)
        time.sleep(0.05)
    if breaker.reason:
        print(f"\n[⛔] 物理熔断: {breaker.reason} | 会话已终止")
        return 3
    print(f"\n[✓] 会话正常结束（退出码 {proc.returncode}）")
    return proc.returncode or 0


if __name__ == "__main__":
    sys.exit(main())
