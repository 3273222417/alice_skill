#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级/非常规技术词支撑审计：确认每个高级词都映射到真实存在且语义相关的技能。
用法: python advanced_audit.py
"""

import json
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ADVANCED = {
    "区块链/Web3": ["区块链", "智能合约", "合约漏洞", "DeFi", "重入攻击", "闪电贷", "预言机",
                    "钱包安全", "助记词", "代币漏洞"],
    "AI/LLM 对抗": ["提示注入", "越狱", "上下文诱导", "篡改上下文", "污染上下文", "多轮诱导", "工具投毒", "多模态注入", "记忆注入", "模型投毒", "训练数据投毒", "对抗样本", "模型窃取",
                    "蒸馏攻击", "后门模型", "LLM安全", "AI红队", "RAG安全", "幻觉利用"],
    "供应链": ["供应链攻击", "依赖投毒", "npm投毒", "pip投毒", "typosquatting", "依赖混淆",
               "SBOM", "软件供应链", "恶意包"],
    "云原生高级": ["eBPF", "RBAC滥用", "service account", "token泄露", "镜像投毒", "registry攻击",
                  "admission webhook", "API server攻击", "kubelet攻击", "IAM滥用", "STS",
                  "AssumeRole", "bucket策略", "KMS滥用"],
    "网络隧道/C2": ["DNS隧道", "ICMP隧道", "HTTP隧道", "隐蔽信道", "域前置", "cdn中转",
                   "云函数C2", "流量混淆", "frp", "nps", "chisel", "跳板"],
    "无线/射频": ["WPA破解", "PMKID", "Evil Twin", "Karma", "Deauth", "BLE攻击", "RFID克隆",
                 "NFC重放", "Flipper Zero", "门禁卡", "车钥匙攻击", "继电器攻击"],
    "内网/AD高级": ["NTLM中继", "Responder", "LLMNR", "WPAD", "SMB中继", "RBCD",
                   "Shadow Credentials", "PKINIT", "ESC漏洞", "证书攻击", "跨域攻击",
                   "域外委派", "PAC校验"],
    "渗透高级": ["NoSQL注入", "LDAP注入", "SSTI", "模板注入", "XXE", "JNDI注入", "log4shell",
                "内存马", "冰蝎", "哥斯拉", "蚁剑", "无文件攻击", "反序列化攻击", "fastjson攻击"],
    "移动高级": ["xposed", "magisk", "LSPosed", "objection", "smali修改", "DEX修改",
                "加固对抗", "iOS越狱", "checkra1n", "unc0ver", "越狱检测绕过", "root检测绕过"],
    "密码/侧信道": ["长度扩展", "哈希碰撞", "降级攻击", "Bleichenbacher", "POODLE", "Heartbleed",
                   "密钥恢复", "白盒密码", "差分分析", "线性分析", "代数攻击", "TLS降级",
                   "侧信道", "功耗分析", "故障注入", "电磁"],
    "反取证/反分析": ["日志清除", "时间戳伪造", "事件日志清理", "反取证", "数据擦除", "痕迹清理",
                    "反沙箱", "反分析", "虚拟化检测", "磁盘清理", "文件时间修改"],
    "物理/硬件": ["门禁", "撬锁", "物理渗透", "摄像头规避", "服务器机房", "RFID克隆", "NFC重放"],
    "业务逻辑": ["支付逻辑", "金额篡改", "优惠券", "薅羊毛", "逻辑漏洞", "并发竞态", "条件竞争",
                "TOCTOU", "双花", "重放业务", "秒杀", "抢购", "抽奖", "刷单", "养号", "接码平台"],
    "暗网/卫星": ["暗网", "TOR", "洋葱", "I2P", "卫星", "星链", "信号劫持"],
    "生物识别": ["虹膜", "指纹识别", "人脸识别", "声纹", "语音助手"],
}


def main() -> int:
    aliases = json.load(open(os.path.join(SKILL_DIR, "config", "command_aliases.json"), encoding="utf-8"))
    cmds = json.load(open(os.path.join(THIS_DIR, "commands_data.json"), encoding="utf-8"))
    names = {s["command"] for s in cmds["skills"]}
    desc = {s["command"]: s["desc"][:70] for s in cmds["skills"]}

    all_words = []
    missing_words = []
    weak = []
    for cat, words in ADVANCED.items():
        for w in words:
            all_words.append(w)
            targets = aliases["red"].get(w) or aliases["blue"].get(w) or []
            if not targets:
                missing_words.append(w)
                continue
            dead = [t for t in targets if t not in names]
            if dead:
                weak.append((w, dead))

    print("=" * 64)
    print("  高级/非常规技术词支撑审计")
    print("=" * 64)
    print(f"总词数: {len(all_words)} | 已收录: {len(all_words) - len(missing_words)} | 缺词: {len(missing_words)}")
    print(f"映射死链: {len(weak)}")
    if missing_words:
        print(f"\n[缺词] {len(missing_words)} 个需补充:")
        print("  " + " / ".join(missing_words))
    if weak:
        print(f"\n[死链] {weak}")
    print(f"\n[映射技能抽样]")
    for w in all_words[:120]:
        t = aliases["red"].get(w) or aliases["blue"].get(w) or []
        if t and t[0] in desc:
            print(f"  {w} -> {t[0]}: {desc[t[0]]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
