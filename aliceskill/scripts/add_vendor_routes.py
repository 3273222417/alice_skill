#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将新增技能（验证码/滑块/风控/签名/协议/游戏逆向）的中文路由词
批量并入 config/command_aliases.json 的 red 表（不覆盖已有词）。
用法: python add_vendor_routes.py
"""
from __future__ import annotations

import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIAS_FILE = os.path.join(SKILL_DIR, "config", "command_aliases.json")

# 新增词 -> 目标技能（必须是 skills_data.json 里真实存在的技能名）
NEW_RED = {
    # ---- 验证码 / 滑块 / 人机验证 ----
    "验证码": ["captcha-protocol-analysis"],
    "滑块": ["captcha-protocol-analysis", "vendor-geetest-captcha"],
    "滑块验证": ["vendor-geetest-captcha"],
    "点选": ["captcha-protocol-analysis", "vendor-netease-yidun"],
    "拼图": ["vendor-geetest-captcha", "vendor-dingxiang-captcha"],
    "拖拽": ["vendor-geetest-captcha"],
    "极验": ["vendor-geetest-captcha"],
    "geetest": ["vendor-geetest-captcha"],
    "数美": ["vendor-shumei-captcha"],
    "shumei": ["vendor-shumei-captcha"],
    "易盾": ["vendor-netease-yidun"],
    "yidun": ["vendor-netease-yidun"],
    "顶象": ["vendor-dingxiang-captcha"],
    "dingxiang": ["vendor-dingxiang-captcha"],
    "腾讯验证": ["vendor-tencent-tcaptcha"],
    "tcaptcha": ["vendor-tencent-tcaptcha"],
    "字节验证": ["vendor-bytedance-captcha"],
    "字节滑块": ["vendor-bytedance-captcha"],
    "谷歌验证": ["vendor-google-recaptcha"],
    "recaptcha": ["vendor-google-recaptcha"],
    "hcaptcha": ["vendor-hcaptcha"],
    "cloudflare验证": ["vendor-cloudflare-turnstile", "vendor-cloudflare-waf"],
    "turnstile": ["vendor-cloudflare-turnstile"],
    "cloudflare": ["vendor-cloudflare-waf", "vendor-cloudflare-turnstile"],
    "cf盾": ["vendor-cloudflare-waf"],
    "akamai": ["vendor-akamai-bm"],
    "阿卡迈": ["vendor-akamai-bm"],
    "arkose": ["vendor-arkose-labs"],
    "datadome": ["vendor-datadome"],
    "kasada": ["vendor-kasada"],
    "perimeterx": ["vendor-perimeterx"],
    "imperva": ["vendor-imperva-incapsula"],
    "瑞数": ["vendor-ruishu-rs"],
    "瑞数rs": ["vendor-ruishu-rs"],
    "rs盾": ["vendor-ruishu-rs"],
    "盾方": ["vendor-shield-square"],
    "aws盾": ["vendor-aws-waf"],
    "阿里验证": ["vendor-aliyun-nvc-baxia"],
    "nvc": ["vendor-aliyun-nvc-baxia"],
    "无感验证": ["vendor-aliyun-nvc-baxia"],
    "yandex验证": ["vendor-yandex-smartcaptcha"],
    "smartcaptcha": ["vendor-yandex-smartcaptcha"],
    "人机验证": ["captcha-protocol-analysis"],
    "行为验证": ["captcha-protocol-analysis"],
    "风控": ["anti-bot-analysis", "captcha-protocol-analysis"],
    "反爬": ["anti-bot-analysis"],
    "反机器人": ["anti-bot-analysis"],
    "指纹": ["browser-fingerprint-analysis", "anti-bot-analysis"],
    "浏览器指纹": ["browser-fingerprint-analysis"],
    "设备指纹": ["browser-fingerprint-analysis"],
    # ---- 网站签名 / 大厂逆向 ----
    "抖音": ["web-douyin-abogus-xbogus"],
    "abogus": ["web-douyin-abogus-xbogus"],
    "xbogus": ["web-douyin-abogus-xbogus"],
    "抖音签名": ["web-douyin-abogus-xbogus"],
    "淘宝": ["web-taobao-mtop-h5st"],
    "h5st": ["web-taobao-mtop-h5st"],
    "mtop": ["web-taobao-mtop-h5st"],
    "天猫签名": ["web-taobao-mtop-h5st"],
    "美团": ["web-meituan-mtgsig"],
    "mtgsig": ["web-meituan-mtgsig"],
    "小红书": ["web-xiaohongshu-xs-xt"],
    "xsxt": ["web-xiaohongshu-xs-xt"],
    "小红书签名": ["web-xiaohongshu-xs-xt"],
    "知乎": ["web-zhihu-zse"],
    "zse": ["web-zhihu-zse"],
    "知乎签名": ["web-zhihu-zse"],
    "雪球": ["web-xueqiu-acw"],
    "acw": ["web-xueqiu-acw"],
    "雪球签名": ["web-xueqiu-acw"],
    "微博": ["web-weibo-login-risk"],
    "微博签名": ["web-weibo-login-risk"],
    "b站": ["web-bilibili-login-risk"],
    "bilibili": ["web-bilibili-login-risk"],
    "b站签名": ["web-bilibili-login-risk"],
    "百度翻译": ["web-baidu-translate-sign"],
    "百度翻译签名": ["web-baidu-translate-sign"],
    "有道翻译": ["web-youdao-translate-sign"],
    "有道签名": ["web-youdao-translate-sign"],
    "网易登录": ["web-netease-login-crypto"],
    "网易签名": ["web-netease-login-crypto"],
    "网易严选": ["web-youpin-mars-sign"],
    "mars签名": ["web-youpin-mars-sign"],
    "qq音乐": ["web-qmusic-sign-encrypt"],
    "q音乐": ["web-qmusic-sign-encrypt"],
    "shein": ["web-shein-armor-token"],
    "希音": ["web-shein-armor-token"],
    "trip": ["web-trip-phantom-token"],
    "phantom": ["web-trip-phantom-token"],
    "携程签名": ["web-trip-phantom-token"],
    "京东": ["vendor-jd-jcap-h5st"],
    "jcap": ["vendor-jd-jcap-h5st"],
    "签名算法": ["web-signature-analysis"],
    "签名逆向": ["web-signature-analysis"],
    "sign逆向": ["web-signature-analysis"],
    "webcrypto": ["webcrypto-hooking"],
    "webpack": ["webpack-vite-nextjs-reversing"],
    "vite逆向": ["webpack-vite-nextjs-reversing"],
    "webpack逆向": ["webpack-vite-nextjs-reversing"],
    # ---- 协议逆向 ----
    "协议逆向": ["protocol-reconstruction", "protocol-reverse-engineering"],
    "协议重建": ["protocol-reconstruction"],
    "协议还原": ["protocol-reconstruction"],
    "代理流量": ["proxy-traffic-analysis"],
    "代理抓包": ["proxy-traffic-analysis"],
    "流量分析": ["proxy-traffic-analysis", "protocol-reverse-engineering"],
    "tls分析": ["tls-pinning-analysis"],
    "证书固定": ["tls-pinning-analysis"],
    "pinning": ["tls-pinning-analysis", "performing-mobile-app-certificate-pinning-bypass"],
    "websocket逆向": ["websocket-grpc-analysis", "websocket-live-reversing"],
    "grpc逆向": ["websocket-grpc-analysis"],
    "websocket抓包": ["websocket-live-reversing"],
    "调用图": ["api-call-graph-recovery"],
    "api调用链": ["api-call-graph-recovery"],
    # ---- 游戏逆向 ----
    "游戏": ["game-security-reversing", "game-hacking"],
    "游戏逆向": ["game-security-reversing", "game-hacking"],
    "游戏外挂": ["game-hacking", "game-security-reversing"],
    "反作弊": ["anti-cheat", "anti-cheat-kernel-analysis"],
    "反作弊绕过": ["anti-cheat-kernel-analysis", "debugger-bypass-analysis"],
    "eac": ["anti-cheat"],
    "battleye": ["anti-cheat"],
    "be反作弊": ["anti-cheat"],
    "vanguard": ["anti-cheat"],
    "内核反作弊": ["anti-cheat-kernel-analysis"],
    "dma": ["dma-attack"],
    "dma攻击": ["dma-attack"],
    "pcileech": ["dma-attack"],
    "fpga": ["dma-attack"],
    "dma外挂": ["dma-attack"],
    "游戏引擎": ["game-engine"],
    "unity": ["unity-il2cpp-analysis", "game-engine"],
    "unreal": ["game-engine"],
    "虚幻引擎": ["game-engine"],
    "ue4": ["game-engine"],
    "ue5": ["game-engine"],
    "il2cpp": ["unity-il2cpp-analysis"],
    "il2cpp逆向": ["unity-il2cpp-analysis"],
    "unity逆向": ["unity-il2cpp-analysis"],
    "图形api": ["graphics-api"],
    "d3d": ["graphics-api"],
    "directx": ["graphics-api"],
    "vulkan": ["graphics-api"],
    "opengl": ["graphics-api"],
    "绘制hook": ["graphics-api"],
    "overlay": ["graphics-api"],
    "自瞄": ["game-hacking"],
    "aimbot": ["game-hacking"],
    "透视": ["game-hacking"],
    "esp": ["game-hacking"],
    "worldtoscreen": ["game-hacking"],
    "内存断点": ["memory-breakpoint-tracing"],
    "硬件断点": ["hardware-breakpoint-observation"],
    "断点绕过": ["debugger-bypass-analysis"],
    "反调试": ["debugger-bypass-analysis"],
    "反调试绕过": ["debugger-bypass-analysis"],
    "内核驱动": ["kernel-driver-analysis"],
    "驱动分析": ["kernel-driver-analysis"],
    "内核逆向": ["windows-kernel", "linux-kernel-reversing", "macos-kernel-reversing"],
    "windows内核": ["windows-kernel"],
    "linux内核": ["linux-kernel-reversing"],
    "macos内核": ["macos-kernel-reversing"],
    "直接系统调用": ["direct-syscall-analysis"],
    "directsyscall": ["direct-syscall-analysis"],
    "syscall": ["direct-syscall-analysis", "syscall-observation-lab"],
    "系统调用追踪": ["syscall-ebpf-frida-correlation", "syscall-observation-lab"],
    "ebpf": ["syscall-ebpf-frida-correlation"],
    "syscall绕过": ["syscall-filter-evidence"],
    "hook隐藏": ["stealth-hook-methodology"],
    "隐身hook": ["stealth-hook-methodology"],
    "反hook": ["anti-hook-artifact-analysis"],
    "hook检测": ["anti-hook-artifact-analysis"],
    "匿名内存": ["anonymous-executable-memory"],
    "可执行内存": ["anonymous-executable-memory"],
    "自修改代码": ["self-modifying-code"],
    "自改码": ["self-modifying-code"],
    "花指令": ["self-modifying-code", "anti-analysis-and-integrity"],
    "反分析": ["anti-analysis-and-integrity"],
    "完整性校验": ["anti-analysis-and-integrity"],
    "gadget": ["gadget-and-injection-analysis"],
    "注入分析": ["gadget-and-injection-analysis"],
    "隐藏内存": ["hidden-rx-memory-reconstruction"],
    "隐藏rx": ["hidden-rx-memory-reconstruction"],
    "nativehook": ["native-api-hooking"],
    "nativehook绕过": ["frida-stealth-hooking", "native-api-hooking"],
    "frida隐身": ["frida-stealth-hooking"],
    "frida检测绕过": ["frida-anti-detection-analysis"],
    "native脱壳": ["native-unpacking"],
    "so脱壳": ["native-unpacking", "packed-so-elf-rebuild"],
    "elf重建": ["packed-so-elf-rebuild"],
    "so修复": ["packed-so-elf-rebuild"],
    "ollvm": ["ollvm-deobfuscation", "ollvm-recovery-workflow"],
    "混淆还原": ["obfuscator-io-analysis", "ollvm-deobfuscation"],
    "obfuscatorio": ["obfuscator-io-analysis"],
    "壳分析": ["packer-and-loader-analysis"],
    "加壳分析": ["packer-and-loader-analysis"],
    "vmp": ["virtualization-protection"],
    "虚拟化保护": ["virtualization-protection"],
    "vmprotect": ["virtualization-protection"],
    "游戏保护": ["virtualization-protection", "anti-cheat"],
    "root检测绕过": ["root-emulator-detection"],
    "模拟器检测绕过": ["root-emulator-detection"],
    "模拟器逆向": ["root-emulator-detection"],
}


def main() -> int:
    with open(ALIAS_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    red = data.setdefault("red", {})
    added, merged = 0, 0
    for word, targets in NEW_RED.items():
        if word in red:
            old = red[word]
            new = list(dict.fromkeys(old + targets))
            if new != old:
                red[word] = new
                merged += 1
        else:
            red[word] = list(targets)
            added += 1
    with open(ALIAS_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print(f"[OK] 新增路由词: {added}  合并增强: {merged}  red 总数: {len(red)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
