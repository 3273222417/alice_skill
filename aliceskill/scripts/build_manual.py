#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice攻防手册生成器：攻/防两大板块 → 大方面 → 小方面 → 具体技能。
输出 references/battle_manual.md（手册级菜单）。
用法: python build_manual.py
"""

from __future__ import annotations

import json
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
DATA = os.environ.get("ALICE_DATA") or os.path.join(THIS_DIR, "skills_data.json")
OUT = os.path.join(SKILL_DIR, "references", "battle_manual.md")

# 技能中文名映射（手册展示用，纯中文）
CH = {
    "src-hunter": "漏洞狩猎", "api-security": "接口安全", "attack-chain": "攻击链设计",
    "competition-web-runtime": "Web运行时攻击", "competition-request-normalization-smuggling": "请求走私",
    "competition-template-render-path": "模板渲染注入", "competition-graphql-rpc-drift": "GraphQL/RPC漂移",
    "competition-jwt-claim-confusion": "JWT声明混淆", "competition-oauth-oidc-chain": "OAuth/OIDC链",
    "competition-ssrf-metadata-pivot": "SSRF元数据枢纽", "competition-race-condition-state-drift": "竞态状态漂移",
    "competition-queue-worker-drift": "队列任务漂移", "competition-runtime-routing": "运行时路由",
    "competition-ad-certificate-abuse": "AD证书滥用", "competition-bundle-sourcemap-recovery": "源码包恢复",
    "competition-mailbox-abuse": "邮箱滥用", "deobfuscating-javascript-malware": "JS恶意反混淆",
    "js-reverse": "JS逆向",
    "competition-supply-chain": "供应链攻击", "supply-chain-security": "供应链安全",
    "pentest-tools": "渗透工具链", "network-pentest": "内网渗透",
    "protocol-reverse-engineering": "协议逆向", "competition-custom-protocol-replay": "自定义协议重放",
    "competition-pcap-protocol": "PCAP协议分析", "radare2": "r2分析",
    "ghidra-ida-re": "Ghidra/IDA深度", "ida-reverse": "IDA逆向", "ghidra-rpc": "Ghidra远程",
    "reverse-engineering": "通用逆向", "04-reverse-engineering": "逆向总集",
    "binary-diff": "二进制差分", "patch-diff-exploit": "补丁差分利用",
    "android-reverse-engineering": "Android逆向", "reverse-engineering-ios-app-with-frida": "iOS Frida逆向",
    "reverse-engineering-dotnet-malware-with-dnspy": ".NET反编译", "reverse-engineering-rust-malware": "Rust恶意分析",
    "analyzing-golang-malware-with-ghidra": "Go恶意分析", "reverse-engineering-android-malware-with-jadx": "Android恶意分析",
    "reverse-engineering-malware-with-ghidra": "Ghidra恶意分析", "reverse-engineering-api-setup": "API逆向环境",
    "reverse-engineering-tools": "逆向工具集", "competition-file-parser-chain": "文件解析链",
    "re-flow-orchestrator": "破解总编排", "re-env-sandbox": "隔离环境",
    "re-flow-recon": "逆向侦察", "re-flow-capture": "抓包流程",
    "re-flow-unpack": "脱壳流程", "re-flow-analyze": "定位与验证",
    "re-tool-registry": "工具注册表", "re-tool-downloader": "工具下载器",
    "re-tool-manifest": "环境登记簿", "windows-license-crack": "授权逆向与绕过",
    "competition-reverse-pwn": "逆向Pwn", "03-exploit-development": "漏洞利用开发",
    "pwn-chain": "Pwn利用链", "performing-binary-exploitation-analysis": "二进制利用分析",
    "performing-fuzzing-with-aflplusplus": "AFL模糊测试", "exploiting-ms17-010-eternalblue-vulnerability": "永恒之蓝", "analyzing-heap-spray-exploitation": "堆喷射分析",
    "llm-direct-prompt-injection": "LLM直接注入", "llm-indirect-prompt-injection": "LLM间接注入",
    "llm-jailbreaking-techniques": "LLM越狱技术", "llm-jailbreaking-personas": "角色扮演越狱",
    "indirect-prompt-injection": "间接提示注入", "ai-jailbreak-prompt-injection": "AI越狱注入",
    "ai-jailbreak-system-prompts": "系统提示越狱", "ai-prompt-leaking": "提示泄露",
    "data-extraction-training-data": "训练数据窃取", "data-poisoning-and-backdoors": "数据投毒后门",
    "rag-poisoning-and-data-exfiltration": "RAG投毒外泄", "llm-overreliance-hallucination": "LLM幻觉利用",
    "llm-prompt-injection-indirect": "间接注入攻击",
    "mcp-protocol-exploitation": "MCP协议攻击", "performing-static-malware-analysis-with-pe-studio": "PEStudio静态分析", "analyzing-bootkit-and-rootkit-samples": "引导套件Rootkit",
    "analyzing-linux-elf-malware": "Linux ELF恶意", "competition-malware-config": "恶意配置提取",
    "malware-analysis": "恶意分析", "05-malware-analysis": "恶意总集",
    "performing-firmware-malware-analysis": "固件恶意分析", "reverse-engineering-ransomware-encryption-routine": "勒索加密还原",
    "apk-reverse": "APK逆向", "mobile-reverse": "移动逆向", "competition-ios-runtime": "iOS运行时",
    "conducting-mobile-app-penetration-test": "移动渗透测试", "performing-mobile-app-certificate-pinning-bypass": "证书固定绕过",
    "competition-android-hooking": "Android Hook", "competition-crypto-mobile": "移动加密",
    "17-mobile-security": "移动安全总集", "13-crypto-analysis": "密码分析",
    "performing-cryptographic-audit-of-application": "应用密码审计", "performing-hash-cracking-with-hashcat": "Hashcat破解",
    "competition-dpapi-credential-chain": "DPAPI凭据链", "competition-lsass-ticket-material": "LSASS票据",
    "competition-kerberos-delegation": "Kerberos委派", "competition-identity-windows": "Windows身份",
    "competition-relay-coercion-chain": "中继胁迫链", "competition-windows-pivot": "Windows枢纽",
    "competition-linux-credential-pivot": "Linux凭据枢纽", "performing-steganography-detection": "隐写检测",
    "competition-stego-media": "媒体隐写", "evm-audit-master": "合约审计总入口",
    "evm-audit-erc20": "ERC20代币审计", "evm-audit-erc721": "ERC721审计",
    "evm-audit-erc4626": "金库标准审计", "evm-audit-erc4337": "账户抽象审计",
    "evm-audit-defi-amm": "AMM审计", "evm-audit-defi-lending": "借贷协议审计",
    "evm-audit-defi-staking": "质押协议审计", "evm-audit-flashloans": "闪电贷审计",
    "evm-audit-oracles": "预言机审计", "evm-audit-proxies": "代理合约审计",
    "evm-audit-governance": "治理机制审计", "evm-audit-bridges": "跨链桥审计",
    "evm-audit-signatures": "签名机制审计", "evm-audit-access-control": "访问控制审计",
    "evm-audit-dos": "拒绝服务审计", "evm-audit-precision-math": "精度运算审计",
    "evm-audit-assembly": "内联汇编审计", "evm-audit-chain-specific": "链特性审计",
    "evm-audit-general": "通用合约审计", "performing-firmware-extraction-with-binwalk": "固件提取",
    "competition-firmware-layout": "固件布局", "firmware-pentest": "固件渗透",
    "reverse-skill": "游戏安全研究", "cheat-engine-cli": "CheatEngine",
    "cheat-engine-skill": "作弊引擎技能", "edr-bypass-re": "EDR绕过",
    "control-in-app-browser": "应用内浏览器", "browser-automation": "浏览器自动化",
    "competition-browser-persistence": "浏览器持久化", "computer-use": "桌面控制",
    "cloud-security": "云安全审计", "iac-security": "基础设施代码安全",
    "container-security": "容器安全", "competition-container-runtime": "容器运行时",
    "competition-kernel-container-escape": "内核容器逃逸", "competition-k8s-control-plane": "Kubernetes控制面",
    "competition-cloud-metadata-path": "云元数据路径", "threat-modeling": "威胁建模",
    "docs-generator": "报告生成", "ctf-sandbox-orchestrator": "CTF总入口",
}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 手册结构：攻/防 → 大方面 → 小方面 → [技能名]
MANUAL = {
    "攻（进攻）": {
        "1. Web 渗透与 JS 逆向": {
            "1.1 Web 漏洞挖掘": ["src-hunter", "api-security", "attack-chain", "competition-web-runtime",
                                "competition-request-normalization-smuggling", "competition-template-render-path",
                                "competition-graphql-rpc-drift", "competition-jwt-claim-confusion",
                                "competition-oauth-oidc-chain", "competition-ssrf-metadata-pivot",
                                "competition-race-condition-state-drift", "competition-queue-worker-drift",
                                "competition-runtime-routing", "competition-ad-certificate-abuse",
                                "competition-bundle-sourcemap-recovery", "competition-mailbox-abuse"],
            "1.2 JS/PowerShell 反混淆": ["deobfuscating-javascript-malware", "js-reverse",
                                      "code-obfuscate"],
            "1.3 供应链攻击": ["competition-supply-chain", "supply-chain-security"],
        },
        "2. 信息收集与协议": {
            "2.1 工具链": ["pentest-tools", "network-pentest"],
            "2.2 协议逆向": ["protocol-reverse-engineering", "competition-custom-protocol-replay",
                          "competition-pcap-protocol"],
            "2.3 抓包与明文取证": ["re-flow-capture"],
        },
        "3. 二进制逆向": {
            "3.1 主力工具": ["radare2", "ghidra-ida-re", "ida-reverse", "ghidra-rpc",
                          "reverse-engineering", "04-reverse-engineering"],
            "3.2 差分与补丁": ["binary-diff", "patch-diff-exploit"],
            "3.3 平台专项": ["android-reverse-engineering", "reverse-engineering-ios-app-with-frida",
                          "reverse-engineering-dotnet-malware-with-dnspy", "reverse-engineering-rust-malware",
                          "analyzing-golang-malware-with-ghidra", "reverse-engineering-android-malware-with-jadx",
                          "reverse-engineering-malware-with-ghidra", "reverse-engineering-api-setup",
                          "reverse-engineering-tools"],
            "3.4 文件解析": ["competition-file-parser-chain", "competition-reverse-pwn"],
            "3.5 脱壳流程编排": ["re-flow-unpack"],
            "3.5 逆向流程编排": ["re-flow-orchestrator", "re-flow-recon", "re-flow-analyze"],
            "3.6 隔离环境与回滚": ["re-env-sandbox"],
            "3.7 工具环境（注册/下载/登记）": ["re-tool-registry", "re-tool-downloader", "re-tool-manifest"],
            "3.8 授权与激活逆向": ["windows-license-crack"],
        },
        "4. 漏洞利用与提权": {
            "4.1 利用开发": ["03-exploit-development", "pwn-chain", "performing-binary-exploitation-analysis",
                           "performing-fuzzing-with-aflplusplus"],
            "4.2 经典漏洞": ["exploiting-ms17-010-eternalblue-vulnerability",
                           "competition-identity-windows"],
            "4.3 内存攻防": ["analyzing-heap-spray-exploitation"],
        },
        "5. AI/LLM 安全（进攻）": {
            "5.1 提示注入与越狱": ["llm-direct-prompt-injection", "llm-indirect-prompt-injection",
                                "llm-jailbreaking-techniques", "llm-jailbreaking-personas",
                                "indirect-prompt-injection", "ai-jailbreak-prompt-injection",
                                "ai-jailbreak-system-prompts"],
            "5.2 信息窃取与模型攻击": ["ai-prompt-leaking", "data-extraction-training-data",
                                  "data-poisoning-and-backdoors", "rag-poisoning-and-data-exfiltration",
                                  "llm-overreliance-hallucination", "llm-prompt-injection-indirect"],
            "5.3 Agent/MCP 攻击": ["pentest-ai-agents", "mcp-protocol-exploitation"],
        },
        "6. 恶意软件分析": {
            "6.1 静态与脱壳": ["performing-static-malware-analysis-with-pe-studio",
                            "re-flow-unpack"],
            "6.2 平台样本": ["analyzing-bootkit-and-rootkit-samples", "analyzing-linux-elf-malware",
                          "competition-malware-config"],
            "6.3 恶意总集": ["malware-analysis", "05-malware-analysis", "performing-firmware-malware-analysis",
                          "reverse-engineering-ransomware-encryption-routine"],
        },
        "7. 移动端安全": {
            "7.1 APK 反编译": ["apk-reverse", "android-reverse-engineering", "mobile-reverse"],
            "7.2 iOS/Frida": ["reverse-engineering-ios-app-with-frida", "competition-ios-runtime"],
            "7.3 测试与绕过": ["conducting-mobile-app-penetration-test",
                            "performing-mobile-app-certificate-pinning-bypass",
                            "competition-android-hooking", "competition-crypto-mobile", "17-mobile-security"],
        },
        "8. 密码学与取证（进攻视角）": {
            "8.1 密码攻击": ["13-crypto-analysis", "performing-cryptographic-audit-of-application",
                           "performing-hash-cracking-with-hashcat"],
            "8.2 凭据与票据": ["competition-dpapi-credential-chain", "competition-lsass-ticket-material",
                            "competition-kerberos-delegation", "competition-identity-windows",
                            "competition-relay-coercion-chain", "competition-windows-pivot",
                            "competition-linux-credential-pivot"],
            "8.3 隐写": ["performing-steganography-detection", "competition-stego-media"],
        },
        "9. 智能合约审计（区块链）": {
            "9.1 总入口": ["evm-audit-master"],
            "9.2 代币标准": ["evm-audit-erc20", "evm-audit-erc721", "evm-audit-erc4626", "evm-audit-erc4337"],
            "9.3 DeFi 专项": ["evm-audit-defi-amm", "evm-audit-defi-lending", "evm-audit-defi-staking",
                            "evm-audit-flashloans", "evm-audit-oracles"],
            "9.4 合约机制": ["evm-audit-proxies", "evm-audit-governance", "evm-audit-bridges",
                          "evm-audit-signatures", "evm-audit-access-control", "evm-audit-dos",
                          "evm-audit-precision-math", "evm-audit-assembly", "evm-audit-chain-specific",
                          "evm-audit-general"],
        },
        "10. 固件与 IoT": {
            "10.1 固件提取": ["performing-firmware-extraction-with-binwalk", "competition-firmware-layout"],
            "10.2 固件渗透": ["firmware-pentest"],
        },
        "11. 游戏安全与防御对抗": {
            "11.1 游戏逆向": ["reverse-skill", "cheat-engine-cli", "cheat-engine-skill"],
            "11.2 EDR/AV 对抗": ["edr-bypass-re"],
        },
        "12. 浏览器与桌面自动化": {
            "12.1 浏览器控制": ["control-in-app-browser", "browser-automation", "competition-browser-persistence"],
            "12.2 桌面控制": ["computer-use"],
        },
        "13. 云与容器（进攻）": {
            "13.1 云配置审计": ["cloud-security", "iac-security"],
            "13.2 容器与逃逸": ["container-security", "competition-container-runtime",
                             "competition-kernel-container-escape", "competition-k8s-control-plane",
                             "competition-cloud-metadata-path"],
        },
    },
    "防（防守）": {
        "1. 恶意样本分析": {
            "1.1 静态三查": ["malware-analysis", "05-malware-analysis", "performing-static-malware-analysis-with-pe-studio"],
            "1.2 脱壳与平台": ["re-flow-unpack", "analyzing-bootkit-and-rootkit-samples",
                            "analyzing-linux-elf-malware", "code-obfuscate",
                            "performing-firmware-malware-analysis"],
            "1.3 配置与 IOC": ["competition-malware-config"],
        },
        "2. 流量与协议分析": {
            "2.1 PCAP 分析": ["protocol-reverse-engineering", "competition-pcap-protocol"],
            "2.2 协议重放": ["competition-custom-protocol-replay"],
        },
        "3. 取证与时间线": {
            "3.1 时间线/磁盘": ["competition-forensic-timeline", "competition-file-parser-chain"],
            "3.2 内存/凭据取证": ["analyzing-heap-spray-exploitation", "competition-dpapi-credential-chain",
                              "competition-lsass-ticket-material", "competition-windows-pivot"],
            "3.3 隐写分析": ["performing-steganography-detection", "competition-stego-media"],
        },
        "4. 密码分析（防守）": {
            "4.1 哈希破解": ["performing-hash-cracking-with-hashcat"],
            "4.2 密码审计": ["performing-cryptographic-audit-of-application", "13-crypto-analysis"],
        },
        "5. 勒索与加密事件": {
            "5.1 家族识别": ["reverse-engineering-ransomware-encryption-routine"],
            "5.2 内网溯源": ["competition-kerberos-delegation", "competition-relay-coercion-chain",
                          "competition-identity-windows", "competition-linux-credential-pivot"],
        },
        "6. 云与容器（防守）": {
            "6.1 云安全评估": ["cloud-security", "iac-security", "container-security"],
            "6.2 云事件处置": ["competition-k8s-control-plane", "competition-container-runtime",
                           "competition-cloud-metadata-path"],
        },
        "7. AI 安全（防守）": {
            "7.1 注入检测": ["llm-direct-prompt-injection", "llm-indirect-prompt-injection",
                           "indirect-prompt-injection"],
            "7.2 模型防护": ["data-poisoning-and-backdoors", "rag-poisoning-and-data-exfiltration",
                           "llm-overreliance-hallucination"],
        },
        "8. 威胁建模与报告": {
            "8.1 威胁建模": ["threat-modeling"],
            "8.2 报告产出": ["docs-generator"],
        },
    },
}


def main() -> int:
    data = json.load(open(DATA, encoding="utf-8"))
    names = {s["name"] for s in data["skills"]}
    lines = ["# Alice攻防手册（手册级菜单 · 大方面 → 小方面 → 技能）", "",
             "> 自动生成 · 攻/防两大板块 · 说场景即开打", ""]
    total = 0
    missing = []
    for side, bigs in MANUAL.items():
        lines.append(f"## {side}")
        lines.append("")
        for big, smalls in bigs.items():
            lines.append(f"### {big}")
            for small, skills in smalls.items():
                ok = []
                for s in skills:
                    if s in names:
                        ok.append(CH.get(s, s))
                    else:
                        missing.append(s)
                total += len(ok)
                joined = "、".join(ok)
                if len(joined) > 60:
                    lines.append(f"- **{small}**（{len(ok)}）")
                    for i in range(0, len(ok), 6):
                        lines.append(f"    {'、'.join(ok[i:i+6])}")
                else:
                    lines.append(f"- **{small}**（{len(ok)}）：{joined}")
            lines.append("")
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"[OK] 手册生成: {OUT}")
    print(f"[OK] 场景化覆盖: {total} 个 | 未覆盖: {len(missing)} 个"
          + (f" | 缺失(未在本机): {'、'.join(missing)}" if missing else " ✓"))
    print(f"[i] 场景化手册按话题挑代表技能，不是全量清单；全量 {len(names)} 个技能见 MASTER_MANUAL.md / 六类路由页")
    return 0


if __name__ == "__main__":
    sys.exit(main())
