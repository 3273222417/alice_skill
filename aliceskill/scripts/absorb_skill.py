#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
absorb_skill.py — 吸收新技能进模组库（AI 主导判类，脚本机械执行）
==================================================================
角色分工:
  AI（agent）: 完整阅读新技能 SKILL.md → 按六类定义判定类目与领域 → 拟 ≤40 字中文
               描述（越短越好但必须清楚，含触发词），带完整参数调用本脚本。
               手册: _modules/alice-absorb。全程向用户汇报「当前进度：N%」。
  脚本（本文件）: 只做机械动作——解包、拷入、写标记、写描述、提示重建；
               绝不做关键词猜测判类。

用法:
  python absorb_skill.py <新技能目录或.zip> --class crack|reverse|pentest|game|ai|assist --domain <领域> --desc "中文描述"

类目来源优先级:
  --class 显式指定 > 源 SKILL.md frontmatter 已有 x-alice-class > 拒绝执行（exit 2）
  --domain 显式指定 > 源 SKILL.md frontmatter 已有 x-alice-domain > 缺失时拒绝执行（避免错误分片）

--desc 行为:
  给出（须含中文）→ 覆写 zh_desc.json 该条目（AI 本次判断优先于旧占位）
  不给且库中无条目 → 用 frontmatter description（仅当含中文）或
                     "<类目中文名>技能：<id>" 占位并警告建议带 --desc 重跑

流程:
  ① zip（如有）解包定位含 SKILL.md 的最浅目录
  ② 确定类目（见优先级；缺失 → exit 2 并打印 AI 判类引导，不拷入任何文件）
  ③ 拷入 skills/_modules/<id>/（id 取目录名；重名加 -N 后缀）
  ④ 写入 x-alice-class 与 x-alice-domain 标记；若无 frontmatter 则包一层 ---
  ⑤ 写入 zh_desc.json 条目
  ⑥ 提示重跑 rebuild_menu.py，并到 skills/alice-<cls>/SKILL.md 确认新条目
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
CODEX_HOME = os.environ.get("CODEX_HOME") or os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if not os.path.isdir(os.path.join(CODEX_HOME, "skills")):
    CODEX_HOME = os.path.expanduser("~/.codex")
SKILLS_ROOT = os.path.join(CODEX_HOME, "skills")
MODULES_ROOT = os.path.join(SKILLS_ROOT, "_modules")
ZH = os.path.join(MODULES_ROOT, "zh_desc.json")

CLASSES = ("crack", "reverse", "pentest", "game", "ai", "assist")
CLASS_CN = {"crack": "破解卡密", "reverse": "逆向脱壳", "pentest": "网络渗透",
            "game": "游戏辅助", "ai": "AI 破限", "assist": "技能助理"}
CLASS_GUIDE = ("crack=授权/卡密/激活  reverse=逆向/脱壳/Hook/取证  "
               "pentest=Web/SQL/端口/资产  game=内存/ESP/反作弊  "
               "ai=LLM越狱/提示注入/MCP/RAG  assist=元技能/平台/工程化")

try:
    # 与生成器共享唯一领域定义，避免吸收器和路由器出现漂移。
    from rebuild_menu import CLASS_DOMAINS
except Exception:
    CLASS_DOMAINS = {
        "crack": {"license-auth": {}, "keygen-patching": {}, "network-vip": {}, "workflow-tooling": {}},
        "reverse": {"native-binary": {}, "mobile": {}, "protocol-web": {}, "forensics-malware": {}, "protection-unpacking": {}, "instrumentation-patching": {}, "firmware-kernel": {}, "advanced-security": {}, "workflow-tooling": {}},
        "pentest": {"recon-discovery": {}, "web-vulnerabilities": {}, "api-cloud": {}, "auth-social": {}, "post-exploit": {}, "network-wireless": {}, "captcha-challenges": {}, "waf-anti-bot": {}, "signed-web-flows": {}, "workflow-tooling": {}},
        "game": {"memory-analysis": {}, "overlay-rendering": {}, "injection-cheat": {}, "anti-cheat-security": {}, "workflow-tooling": {}},
        "ai": {"prompt-injection": {}, "llm-security": {}, "mcp-rag": {}, "offensive-workflows": {}},
        "assist": {"routing-skill-engineering": {}, "security-engineering": {}, "automation-integrations": {}, "research-case": {}, "content-creative": {}, "competition-identity": {}, "competition-platform": {}, "competition-application": {}, "general-assist": {}},
    }
DOMAIN_IDS = {cls: tuple(domains) for cls, domains in CLASS_DOMAINS.items()}


def write_bytes_atomic(path: str, data: bytes) -> None:
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".alice-write-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_json_atomic(path: str, data: dict) -> None:
    write_bytes_atomic(path, (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def unique_dir(mid: str) -> str:
    d = os.path.join(MODULES_ROOT, mid)
    if not os.path.exists(d):
        return d
    for i in range(2, 100):
        d = os.path.join(MODULES_ROOT, f"{mid}-{i}")
        if not os.path.exists(d):
            return d
    raise SystemExit("[!] 无法生成唯一目录名")


def ensure_marker(skillmd: str, cls: str, domain: str) -> None:
    with open(skillmd, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8", errors="replace")
    bom = ""
    if text.startswith("\ufeff"):
        bom, text = "\ufeff", text[1:]
    if text.lstrip("\ufeff").startswith("---"):
        m = re.search(r"^---\s*\n(.*?)\n---", text, re.S | re.M)
        if m:
            block = m.group(1)
            if re.search(r"^x-alice-class:", block, re.M):
                block = re.sub(r"^x-alice-class:.*$", f"x-alice-class: {cls}", block, flags=re.M)
            else:
                block += f"\nx-alice-class: {cls}"
            if re.search(r"^x-alice-domain:", block, re.M):
                block = re.sub(r"^x-alice-domain:.*$", f"x-alice-domain: {domain}", block, flags=re.M)
            else:
                block += f"\nx-alice-domain: {domain}"
            text = text[:m.start()] + "---\n" + block + "\n---" + text[m.end():]
        else:
            text = f"---\nx-alice-class: {cls}\nx-alice-domain: {domain}\n---\n" + text
    else:
        text = f"---\nx-alice-class: {cls}\nx-alice-domain: {domain}\n---\n" + text.lstrip("\ufeff")
    write_bytes_atomic(skillmd, (bom + text).encode("utf-8"))


def read_desc(skillmd: str) -> str:
    try:
        txt = open(skillmd, encoding="utf-8", errors="replace").read(3000)
        m = re.search(r"^description:\s*(.*)$", txt, re.M)
        d = (m.group(1).strip().strip('"')[:60]) if m else ""
        if d and not re.search(r"[\u4e00-\u9fff]", d):
            # 英文/空壳描述 → 留空，交给占位逻辑，保证路由页中文可读
            return ""
        return d
    except Exception:
        return ""


def load_zh() -> dict:
    try:
        with open(ZH, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_marker(skillmd: str) -> str:
    """读源 SKILL.md frontmatter 已有的 x-alice-class（无/非法 → 空串）。"""
    try:
        head = open(skillmd, encoding="utf-8", errors="replace").read(4000)
    except Exception:
        return ""
    m = re.search(r"^x-alice-class:\s*(\w+)", head, re.M)
    return m.group(1) if m and m.group(1) in CLASSES else ""


def read_domain_marker(skillmd: str) -> str:
    """读取源 SKILL.md 的 x-alice-domain；合法性在结合 class 后校验。"""
    try:
        head = open(skillmd, encoding="utf-8", errors="replace").read(4000)
    except Exception:
        return ""
    m = re.search(r"^x-alice-domain:\s*([a-z0-9-]+)", head, re.M)
    return m.group(1) if m else ""


def refuse_class(source: str, skillmd: str) -> int:
    print("[!] 未指定 --class 且源 SKILL.md 无合法 x-alice-class 标记，脚本不做猜测判类（exit 2）。")
    print()
    print("AI 操作指引:")
    print(f"  1. 完整阅读该技能 SKILL.md: {os.path.abspath(skillmd)}")
    print("  2. 按六类定义判类:")
    print(f"     {CLASS_GUIDE}")
    print("  3. 同时判定该类下的领域（可用 --list-domains <类> 查看），拟 ≤40 字中文描述:")
    print(f'     python "{os.path.abspath(__file__)}" "{os.path.abspath(source)}" --class <类> --domain <领域> --desc "中文描述"')
    return 2


def refuse_domain(source: str, skillmd: str, cls: str) -> int:
    print(f"[!] 未指定 --domain 且源 SKILL.md 无合法 x-alice-domain 标记；为避免错误分片，脚本不猜测领域（exit 2）。")
    print(f"[i] 当前类目：{cls}（{CLASS_CN[cls]}）")
    print("[i] 可选领域：" + ", ".join(DOMAIN_IDS[cls]))
    print("AI 操作指引：完整阅读 SKILL.md，选择一个最匹配领域后重跑：")
    print(f'  python "{os.path.abspath(__file__)}" "{os.path.abspath(source)}" --class {cls} --domain <领域> --desc "中文描述"')
    return 2


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="吸收新技能进模组库（AI 主导判类，脚本机械执行）")
    ap.add_argument("source", nargs="?", help="新技能目录或 .zip")
    ap.add_argument("--class", dest="cls", choices=CLASSES,
                    help="AI 判定的类目；缺省且源无 x-alice-class 标记时拒绝执行")
    ap.add_argument("--domain", help="AI 判定的领域；必须属于所选 class，可复用源 x-alice-domain")
    ap.add_argument("--list-domains", choices=CLASSES, metavar="CLASS",
                    help="列出指定类目的合法领域后退出")
    ap.add_argument("--desc", help="AI 拟的 ≤40 字中文描述（越短越好但必须清楚，含触发词）；给出即覆写 zh_desc 条目")
    a = ap.parse_args()

    if a.list_domains:
        cls = a.list_domains
        print(f"{cls}（{CLASS_CN[cls]}）合法领域：")
        for domain, meta in CLASS_DOMAINS[cls].items():
            title = meta.get("title", "") if isinstance(meta, dict) else ""
            when = meta.get("when", "") if isinstance(meta, dict) else ""
            print(f"  {domain}: {title} — {when}".rstrip(" —"))
        return 0
    if not a.source:
        ap.error("需要 source，或使用 --list-domains <class>")

    if a.desc and not re.search(r"[\u4e00-\u9fff]", a.desc):
        print("[!] --desc 必须为含中文的描述（AI 拟定，含触发词），拒绝执行（exit 2）。")
        return 2

    src = a.source
    tmp = None
    if src.lower().endswith(".zip"):
        if not os.path.isfile(src):
            raise SystemExit(f"[!] zip 不存在: {src}")
        tmp = tempfile.mkdtemp(prefix="absorb_")
        with zipfile.ZipFile(src) as zf:
            zf.extractall(tmp)
        # 定位含 SKILL.md 的目录
        candidates = []
        for dp, dn, fn in os.walk(tmp):
            if "SKILL.md" in fn:
                candidates.append(dp)
        if not candidates:
            raise SystemExit("[!] zip 内未找到 SKILL.md")
        # 取最浅的
        src = min(candidates, key=lambda p: p.count(os.sep))
        print(f"[i] zip 解出技能目录: {os.path.basename(src)}")
    if not os.path.isdir(src):
        raise SystemExit(f"[!] 源目录不存在: {src}")
    if not os.path.isfile(os.path.join(src, "SKILL.md")):
        raise SystemExit("[!] 源目录缺 SKILL.md，不吸收")

    # 类目解析：--class 显式 > 源已有标记 > 拒绝（在拷入之前，拒绝时零副作用）
    src_skillmd = os.path.join(src, "SKILL.md")
    if a.cls:
        cls = a.cls
        marked = read_marker(src_skillmd)
        if marked and marked != cls:
            print(f"[i] 源已有标记 x-alice-class: {marked}，按 --class 覆写为 {cls}")
    else:
        cls = read_marker(src_skillmd)
        if not cls:
            try:
                tmp and shutil.rmtree(tmp, ignore_errors=True)
            except Exception:
                pass
            return refuse_class(src, src_skillmd)
        print(f"[i] 源已有标记 x-alice-class: {cls}（{CLASS_CN[cls]}）")

    # 领域解析：--domain 显式 > 源已有标记 > 拒绝；且必须属于当前类。
    marked_domain = read_domain_marker(src_skillmd)
    domain = a.domain or marked_domain
    if not domain:
        try:
            tmp and shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass
        return refuse_domain(src, src_skillmd, cls)
    if domain not in DOMAIN_IDS[cls]:
        print(f"[!] 领域 `{domain}` 不属于 {cls}；合法值：{', '.join(DOMAIN_IDS[cls])}（exit 2）。")
        try:
            tmp and shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass
        return 2
    if a.domain and marked_domain and marked_domain != domain:
        print(f"[i] 源已有标记 x-alice-domain: {marked_domain}，按 --domain 覆写为 {domain}")

    mid = os.path.basename(os.path.normpath(src))
    # 清洗非法字符
    mid = re.sub(r"[^\w.\-一-龥]+", "-", mid).strip("-") or "new-skill"
    dst = unique_dir(mid)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
        ".git", "node_modules", "__pycache__", ".venv", "venv"))
    final_id = os.path.basename(dst)
    print(f"[1/4] 已拷入 _modules/{final_id}")

    skillmd = os.path.join(dst, "SKILL.md")
    ensure_marker(skillmd, cls, domain)
    print(f"[2/4] 标记已写入 frontmatter: x-alice-class: {cls}; x-alice-domain: {domain}")

    # zh_desc：--desc 覆写 > 库中已有 > description(中文) > 占位+警告
    zh = load_zh()
    if a.desc:
        existed = final_id in zh
        zh[final_id] = a.desc.strip()
        write_json_atomic(ZH, zh)
        print(f"[3/4] zh_desc {'覆写' if existed else '写入'}: {zh[final_id]}")
    elif final_id in zh:
        print(f"[3/4] zh_desc 已有条目，未改动: {zh[final_id]}")
    else:
        zh[final_id] = read_desc(skillmd) or f"{CLASS_CN[cls]}技能：{final_id}"
        write_json_atomic(ZH, zh)
        print(f"[3/4] zh_desc 占位: {zh[final_id]}")
        print("[warn] 未提供 --desc，已用占位描述；建议带 --desc 重跑优化（AI 本次判断优先）。")

    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    print("[4/4] 完成。收尾两步:")
    print("[next] 重跑生成器刷新路由索引：")
    print(f'  python "{os.path.join(HERE, "rebuild_menu.py")}"')
    print(f"[check] 到 skills/alice-{cls}/references/{domain}.md 确认 `- {final_id}` 与中文描述出现")
    print(f"[done] {final_id} → 类 {cls}（{CLASS_CN[cls]}）→ 领域 {domain} → 路由 alice-{cls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
