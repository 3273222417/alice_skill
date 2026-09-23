#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 GitHub 仓库提炼 LLM 攻击载荷 → Alice内部载荷库。

输入源（skill-vendors 已克隆）：
  prompt-injector/public/assets/payloads/all-attack-payloads.json  (163 载荷)
  llm-red-teamer/payloads/payloads.yaml                           (扩展载荷)
  AI-Prompt-Injection-Cheatsheet/README.md                        (2026 速查表)

输出：
  payloads/owasp_payloads.json     标准化载荷库（id/name/category/payload/tags/owasp/technique）
  references/cheatsheet_2026.md    2026 版攻击技术速查
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
PAYLOAD_OUT = os.path.join(SKILL_DIR, "payloads", "owasp_payloads.json")
CHS_OUT = os.path.join(SKILL_DIR, "references", "cheatsheet_2026.md")

VENDORS = r"C:\Users\Administrator\Documents\openclaw\wz-license\skill-vendors"
SRC_JSON = os.path.join(VENDORS, "prompt-injector", "public", "assets", "payloads", "all-attack-payloads.json")
SRC_YAML = os.path.join(VENDORS, "llm-red-teamer", "payloads", "payloads.yaml")
SRC_CHS = os.path.join(VENDORS, "AI-Prompt-Injection-Cheatsheet", "README.md")


def load_json() -> list[dict]:
    with open(SRC_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def normalize(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append({
            "id": r.get("id", ""),
            "name": r.get("name", ""),
            "category": r.get("category", ""),
            "payload": r.get("payload", ""),
            "description": (r.get("description") or "")[:200],
            "tags": r.get("tags", [])[:8],
            "owasp": r.get("owasp", []),
            "technique": r.get("technique", ""),
            "source": r.get("source", "prompt-injector"),
        })
    return out


def parse_yaml_payloads() -> list[dict]:
    """llm-red-teamer payloads.yaml 简易解析（基于块结构）。"""
    try:
        with open(SRC_YAML, encoding="utf-8") as fh:
            txt = fh.read()
    except Exception:
        return []
    rows = []
    blocks = re.split(r"\n  - id: ", txt)
    for b in blocks[1:]:
        lines = b.splitlines()
        rec = {}
        content_lines: list[str] = []
        in_content = False
        for ln in lines:
            if ln.startswith("    id: "):
                rec["id"] = ln.split(":", 1)[1].strip()
            elif ln.startswith("    name: "):
                rec["name"] = ln.split(":", 1)[1].strip().strip('"')
            elif ln.startswith("    category: "):
                rec["category"] = ln.split(":", 1)[1].strip().strip('"')
            elif ln.startswith("    owasp_ref:"):
                rec["owasp"] = [ln.split(":", 1)[1].strip()]
            elif ln.startswith("    technique:"):
                rec["technique"] = ln.split(":", 1)[1].strip().strip('"')
            elif ln.startswith("    content: |"):
                in_content = True
            elif in_content:
                if ln.startswith("    "):
                    content_lines.append(ln.strip())
                else:
                    in_content = False
        if rec.get("id"):
            rec["payload"] = "\n".join(content_lines).strip()
            rec.setdefault("name", rec["id"])
            rec.setdefault("category", "prompt_injection")
            rec["source"] = "llm-red-teamer"
            rows.append(rec)
    return rows


def build_cheatsheet() -> str:
    try:
        with open(SRC_CHS, encoding="utf-8") as fh:
            txt = fh.read()
    except Exception:
        return ""
    # 提取从 "The AI/LLM Prompt Injection Cheatsheet" 到 "## License" 之前
    m = re.search(r"# The AI/LLM Prompt Injection Cheatsheet.*?(?=\n## (License|References|Contributing)|\Z)", txt, re.S)
    body = m.group(0) if m else txt
    header = (
        "# Alice LLM 攻击速查（2026 版 · Alice）\n\n"
        f"> 提炼时间 {datetime.now().strftime('%Y-%m-%d %H:%M')} · 来源 GitHub\n\n"
        "> ⚠️ 仅用于授权靶场 / CTF / 实验环境。经典 DAN/忽略指令对现代 RLHF 模型效果有限，"
        "本速查聚焦架构级与管线级攻击（推理劫持/工具链/RAG 污染/多模态/记忆腐化/编码绕过）。\n\n---\n\n"
    )
    return header + body


def main() -> int:
    all_rows: list[dict] = []
    if os.path.isfile(SRC_JSON):
        rows = normalize(load_json())
        all_rows.extend(rows)
        print(f"[OK] prompt-injector: {len(rows)} 载荷")
    else:
        print(f"[!] 缺 {SRC_JSON}")
    yaml_rows = parse_yaml_payloads()
    if yaml_rows:
        all_rows.extend(yaml_rows)
        print(f"[OK] llm-red-teamer: {len(yaml_rows)} 载荷")
    # 去重
    seen: set[str] = set()
    uniq: list[dict] = []
    for r in all_rows:
        k = (r.get("payload", "")[:80], r.get("name", ""))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    os.makedirs(os.path.dirname(PAYLOAD_OUT), exist_ok=True)
    with open(PAYLOAD_OUT, "w", encoding="utf-8") as fh:
        json.dump({"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                   "total": len(uniq), "payloads": uniq}, fh, ensure_ascii=False, indent=2)
    print(f"[OK] 载荷库落盘: {PAYLOAD_OUT}（{len(uniq)} 条）")
    chs = build_cheatsheet()
    if chs:
        os.makedirs(os.path.dirname(CHS_OUT), exist_ok=True)
        with open(CHS_OUT, "w", encoding="utf-8") as fh:
            fh.write(chs)
        print(f"[OK] 2026 速查落盘: {CHS_OUT}（{len(chs)} 字符）")
    # 分类统计
    from collections import Counter
    cats = Counter(r.get("category", "?") for r in uniq)
    print(f"[OK] 覆盖 {len(cats)} 个攻击类别")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
