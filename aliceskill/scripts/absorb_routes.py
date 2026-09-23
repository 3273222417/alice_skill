#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
吸收任务路由 7 路路由触发词 → Alice中文路由（已归属Alice，去除外部署名）。
EXEC/REVERSE/PENTEST/GAME/CODE/ANALYSIS 六路全部并入；
FICTION（成人创作）不吸收。

每个任务路由词映射到Alice对应技能（语义对齐）：
  EXEC       → 文档/文件操作类（documents, 1688 等）
  REVERSE    → 二进制逆向类（04-reverse-engineering, ghidra-ida-re, radare2 等）
  PENTEST    → 渗透类（src-hunter, pentest-tools, network-pentest 等）
  GAME       → 游戏类（game-hacking, graphics-api, anti-cheat 等）
  CODE       → 代码/自动化类（domain-modeling, diagram-generator 等）
  ANALYSIS   → 取证/密码类（13-crypto-analysis, performing-hash-cracking 等）
用法: python absorb_taskroute_routes.py
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

# 任务路由触发词 → Alice技能（语义对齐；词已存在则合并 targets）
COLD_TO_ALICE = {
    # ---- EXEC ----
    "文件": ["documents"], "安装": ["skill-installer"], "卸载技能": ["skill-installer"],
    "部署方案": ["iac-security"], "打包": ["documents"], "发布": ["documents"],
    "上传": ["documents"], "修改": ["documents"], "补丁分析": ["patch-diff-exploit"],
    "回滚": ["documents"], "仓库": ["documents"], "github": ["documents"],
    # ---- REVERSE ----
    "逆向": ["04-reverse-engineering", "reverse-engineering"],
    "反编译": ["04-reverse-engineering"], "反汇编": ["04-reverse-engineering"],
    "pe": ["04-reverse-engineering"], "elf": ["analyzing-linux-elf-malware"],
    "dll": ["05-malware-analysis"], "exe": ["04-reverse-engineering"],
    "调试": ["systematic-debugging"], "patch": ["patch-diff-exploit"],
    "hook": ["native-api-hooking"], "符号": ["04-reverse-engineering"],
    "脱壳": ["native-unpacking", "packer-and-loader-analysis"],
    "转储": ["04-reverse-engineering"], "重建": ["packed-so-elf-rebuild"],
    "upx": ["re-flow-unpack"],
    "themida": ["virtualization-protection"], "vmprotect": ["virtualization-protection"],
    "vmp": ["virtualization-protection"], "aspack": ["packer-and-loader-analysis"],
    "safengine": ["virtualization-protection"], "enigma": ["packer-and-loader-analysis"],
    "mpress": ["packer-and-loader-analysis"], "oat": ["packed-so-elf-rebuild"],
    "vdex": ["dex-odex-vdex-analysis"], "dex": ["android-reverse-engineering"],
    "so文件": ["packed-so-elf-rebuild"], "固件": ["firmware-pentest"],
    "bios": ["performing-firmware-extraction-with-binwalk"], "uefi": ["performing-firmware-extraction-with-binwalk"],
    "jtag": ["performing-firmware-extraction-with-binwalk"], "uart": ["performing-firmware-extraction-with-binwalk"],
    "spi": ["performing-firmware-extraction-with-binwalk"], "i2c": ["performing-firmware-extraction-with-binwalk"],
    # ---- PENTEST ----
    "栈溢出": ["performing-binary-exploitation-analysis"], "堆溢出": ["performing-binary-exploitation-analysis"],
    "uaf": ["performing-binary-exploitation-analysis"], "竞态": ["competition-race-condition-state-drift"],
    "rop": ["performing-binary-exploitation-analysis"], "jop": ["performing-binary-exploitation-analysis"],
    "srop": ["performing-binary-exploitation-analysis"], "brop": ["performing-binary-exploitation-analysis"],
    "堆喷": ["analyzing-heap-spray-exploitation"], "oob": ["performing-binary-exploitation-analysis"],
    "整数溢出": ["performing-binary-exploitation-analysis"], "类型混淆": ["performing-binary-exploitation-analysis"],
    "侦察": ["pentest-tools"], "踩点": ["pentest-tools"], "打点": ["pentest-tools"],
    "扫段": ["pentest-tools"], "端口": ["pentest-tools"], "指纹": ["browser-fingerprint-analysis"],
    "枚举": ["pentest-tools"], "资产": ["pentest-tools"], "子域": ["pentest-tools"],
    "目录发现": ["pentest-tools"], "技术栈": ["pentest-tools"], "sqli": ["src-hunter"],
    "sql注入": ["src-hunter"], "xss": ["src-hunter"], "csrf": ["src-hunter"],
    "ssrf": ["competition-ssrf-metadata-pivot"], "xxe": ["src-hunter"],
    "ssti": ["competition-template-render-path"], "jwt": ["competition-jwt-claim-confusion"],
    "oauth": ["competition-oauth-oidc-chain"], "idor": ["api-security"],
    "越权": ["api-security"], "反序列化": ["src-hunter"], "文件上传": ["src-hunter"],
    "rce": ["src-hunter"], "graphql": ["competition-graphql-rpc-drift"],
    "域控": ["competition-identity-windows"], "域管": ["competition-identity-windows"],
    "活动目录": ["competition-identity-windows"], "ad攻击": ["competition-ad-certificate-abuse"],
    "委派": ["competition-kerberos-delegation"], "中继": ["competition-relay-coercion-chain"],
    "票据": ["competition-lsass-ticket-material"], "黄金票据": ["competition-lsass-ticket-material"],
    "白银票据": ["competition-lsass-ticket-material"], "ntds": ["competition-dpapi-credential-chain"],
    "hash传递": ["competition-lsass-ticket-material"], "提权": ["pwn-chain"],
    "横移": ["network-pentest"], "令牌": ["competition-lsass-ticket-material"],
    "凭据": ["competition-linux-credential-pivot"], "持久化": ["05-malware-analysis"],
    "wmi": ["competition-identity-windows"], "计划任务": ["analyzing-linux-elf-malware"],
    "注册表": ["competition-identity-windows"], "服务": ["05-malware-analysis"],
    "自启动": ["05-malware-analysis"], "lsa": ["competition-dpapi-credential-chain"],
    "sam": ["competition-dpapi-credential-chain"], "嗅探": ["protocol-reverse-engineering"],
    "劫持": ["protocol-reverse-engineering"], "arp": ["pentest-tools"],
    "dhcp": ["pentest-tools"], "vlan": ["pentest-tools"], "bgp": ["protocol-reverse-engineering"],
    "smb": ["network-pentest"], "rdp": ["network-pentest"], "ssh": ["network-pentest"],
    "dns": ["protocol-reverse-engineering"], "icmp": ["protocol-reverse-engineering"],
    "tcp": ["protocol-reverse-engineering"], "udp": ["protocol-reverse-engineering"],
    "quic": ["protocol-reverse-engineering"], "隧道": ["protocol-reverse-engineering"],
    "社工": ["src-hunter"], "水坑": ["src-hunter"], "鱼叉": ["src-hunter"],
    "钓鲸": ["src-hunter"], "钓鱼": ["src-hunter"], "伪站": ["src-hunter"],
    "克隆站": ["src-hunter"], "话术": ["src-hunter"], "仿冒": ["src-hunter"],
    "欺诈": ["src-hunter"], "木马": ["malware-analysis"], "勒索": ["reverse-engineering-ransomware-encryption-routine"],
    "挖矿": ["05-malware-analysis"], "蠕虫": ["05-malware-analysis"], "后门": ["05-malware-analysis"],
    "远控": ["05-malware-analysis"], "感染": ["05-malware-analysis"], "寄生": ["05-malware-analysis"],
    "自毁": ["05-malware-analysis"], "驻留": ["05-malware-analysis"], "保活": ["05-malware-analysis"],
    "传播": ["05-malware-analysis"], "加载器": ["packer-and-loader-analysis"],
    "免杀": ["edr-bypass-re"], "反沙": ["debugger-bypass-analysis"], "反调": ["debugger-bypass-analysis"],
    "反虚": ["debugger-bypass-analysis"], "混淆": ["obfuscator-io-analysis"],
    "多态": ["self-modifying-code"], "变种": ["self-modifying-code"],
    "syscall": ["direct-syscall-analysis"], "edr": ["edr-bypass-re"],
    "xdr": ["edr-bypass-re"], "mdr": ["edr-bypass-re"], "沙箱": ["05-malware-analysis"],
    "规避": ["edr-bypass-re"], "k8s": ["competition-k8s-control-plane"],
    "kubernetes": ["competition-k8s-control-plane"], "docker": ["container-security"],
    "容器": ["container-security"], "云安全": ["cloud-security"],
    "s3": ["competition-cloud-metadata-path"], "存储桶": ["competition-cloud-metadata-path"],
    "元数据": ["competition-cloud-metadata-path"], "iam": ["cloud-security"],
    "api网关": ["api-security"], "镜像仓库": ["container-security"], "terraform": ["iac-security"],
    "区块链": ["evm-audit-master"], "智能合约": ["evm-audit-master"],
    "重入": ["evm-audit-general"], "闪电贷": ["evm-audit-flashloans"],
    "预言机": ["evm-audit-oracles"], "mev": ["evm-audit-defi-amm"],
    "抢跑": ["evm-audit-defi-amm"], "夹子": ["evm-audit-defi-amm"],
    "三明治": ["evm-audit-defi-amm"], "粉尘": ["evm-audit-defi-amm"],
    # ---- CODE ----
    "爬虫": ["protocol-reverse-engineering"], "抓取": ["protocol-reverse-engineering"],
    "采集": ["protocol-reverse-engineering"], "无头": ["browser-automation"],
    "验证码": ["captcha-protocol-analysis"], "滑块": ["vendor-geetest-captcha"],
    "点选": ["captcha-protocol-analysis"], "旋转": ["vendor-geetest-captcha"],
    "轨迹": ["vendor-geetest-captcha"], "识别": ["captcha-protocol-analysis"],
    "playwright": ["browser-automation"], "puppeteer": ["browser-automation"],
    "源码": ["domain-modeling"], "算法": ["domain-modeling"], "并发": ["domain-modeling"],
    "异步": ["domain-modeling"], "缓存": ["domain-modeling"], "队列": ["domain-modeling"],
    "数据库": ["domain-modeling"], "数据结构": ["domain-modeling"], "重构": ["domain-modeling"],
    "单元测试": ["test-driven-development"], "集成测试": ["test-driven-development"],
    "接口": ["api-security"], "websocket": ["websocket-grpc-analysis"],
    # ---- ANALYSIS ----
    "哈希": ["13-crypto-analysis"], "字典": ["performing-hash-cracking-with-hashcat"],
    "彩虹": ["performing-hash-cracking-with-hashcat"], "加盐": ["13-crypto-analysis"],
    "aes": ["13-crypto-analysis"], "rsa": ["13-crypto-analysis"], "ecc": ["13-crypto-analysis"],
    "md5": ["13-crypto-analysis"], "sha": ["13-crypto-analysis"],
    "碰撞": ["13-crypto-analysis"], "填充预言": ["13-crypto-analysis"],
    "密码学": ["13-crypto-analysis"], "keygen": ["13-crypto-analysis"],
    "取证": ["competition-forensic-timeline"], "固证": ["competition-forensic-timeline"],
    "存证": ["competition-forensic-timeline"], "镜像": ["memory-forensics"],
    "快照取证": ["memory-forensics"], "雕刻": ["performing-steganography-detection"],
    "恢复": ["performing-steganography-detection"], "溯源": ["competition-forensic-timeline"],
    "时间线": ["competition-forensic-timeline"], "脱敏": ["competition-forensic-timeline"],
    "匿名化": ["competition-forensic-timeline"], "差分隐私": ["competition-forensic-timeline"],
    # ---- GAME（任务路由 17 词，与 add_game_routes 合并）----
    "外挂": ["game-hacking", "reverse-skill"], "自瞄": ["game-hacking", "reverse-skill"],
    "透视": ["game-hacking", "graphics-api"], "锁头": ["game-hacking"],
    "穿墙": ["game-hacking"], "飞天": ["game-hacking"], "雷达": ["game-hacking"],
    "弹道": ["game-hacking"], "压枪": ["game-hacking"], "无cd": ["game-hacking"],
    "无CD": ["game-hacking"], "改伤": ["game-hacking"], "overlay": ["graphics-api", "game-hacking"],
    "d3d": ["graphics-api"], "opengl": ["graphics-api"], "vulkan": ["graphics-api"],
    "dx11": ["graphics-api"], "dx12": ["graphics-api"],
}


def main() -> int:
    with open(ALIAS_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    red = data.setdefault("red", {})
    added, merged = 0, 0
    for word, targets in COLD_TO_ALICE.items():
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
    print(f"[OK] 任务路由路由词吸收（已归属Alice）: 新增 {added} 合并 {merged} | red 总数 {len(red)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
