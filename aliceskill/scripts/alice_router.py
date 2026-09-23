#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice路由编排器（六类重构版）
=====================================================
机制：
  ① NFKC 归一化（ＳＱＬ注入 → sql注入，全角/半角/异体字统一）
  ② 术语加权评分（精确词 > 拆分词，域名/节点名两级命中）
  ③ 阶段链组合（基础阶段 + 能力阶段去重拼接）
  ④ 状态机（IDLE → READY → ROUTED → VERIFIED → 继续/矫正）
  ⑤ 模式词与类别词分离：攻/防只设置模式，六类入口再选择类别

数据源：skills_data.json（category = crack/reverse/pentest/game/ai/assist）
        + _modules/alice_manifest.json（id→class→router）
        + config/command_aliases.json
用法:
  python alice_router.py route "攻 web sql注入"
  python alice_router.py route "防 勒索样本分析"
  python alice_router.py status
  python alice_router.py selfcheck
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
DATA = os.environ.get("ALICE_DATA") or os.path.join(THIS_DIR, "skills_data.json")
MANIFEST = os.path.join(os.path.dirname(SKILL_DIR), "_modules", "alice_manifest.json")
ALIASES = os.path.join(SKILL_DIR, "config", "command_aliases.json")
STATE_FILE = os.path.join(SKILL_DIR, "guard", "router_state.json")
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

CLASS_CN = {
    "crack": "卡密授权",
    "reverse": "逆向分析",
    "pentest": "web安全",
    "game": "游戏攻防",
    "ai": "AI安全测试",
    "assist": "技能指令",
}
ROUTER = {c: f"alice-{c}" for c in CLASS_CN}
# 类别词与模式词分离：旧快捷词继续兼容，新展示名称也可直接进入类别路由。
CLASS_WORDS = {
    "破": "crack", "卡密授权": "crack",
    "逆": "reverse", "逆向分析": "reverse",
    "渗": "pentest", "web安全": "pentest", "web 安全": "pentest",
    "挂": "game", "游戏攻防": "game",
    "智": "ai", "ai安全测试": "ai", "ai 安全测试": "ai",
    "助": "assist", "技能指令": "assist",
}
MODE_WORDS = {"攻": "red", "防": "blue"}
DEFENSE_TERMS = ("样本", "流量", "日志", "pcap", "evtx", "取证", "恶意", "时间线", "ioc")

# 路由页直达词：这些指令的正文不在 _modules 模块里，而在路由页 SKILL.md 中，
# 按模块匹配永远命中不了 → 整条消息等于该词时直接路由到对应路由页。
PAGE_WORDS = {
    "技能评分": "alice-assist", "技能打分": "alice-assist", "技能质量": "alice-assist",
    "检测技能质量": "alice-assist", "给技能打分": "alice-assist", "技能评分规则": "alice-assist",
    "常用指令": "aliceskill", "alice指令": "aliceskill",
    "技能菜单": "aliceskill", "激活词速查": "aliceskill", "技能列表": "aliceskill",
}

SPLIT = re.compile(r"[\s._/\\:+&、，,;；（）()\[\]{}<>与和及]+")
STOP = {
    "analysis", "assurance", "assessment", "audit", "boundary", "check", "configuration",
    "control", "detection", "engineering", "exposure", "integrity", "inventory", "lifecycle",
    "mapping", "modeling", "platform", "review", "simulation", "validation", "workflow",
    "attack", "security", "reversing", "reverse", "exploit", "tool",
}




def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def load(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default if default is not None else {}


def save(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def expanded_terms(values: list[str]) -> list[tuple[str, int]]:
    """把路由词展开成 (词, 权重) 供模糊匹配。

    单字词（表里有 52 个，如「看」「开」「打」「干」）**不参与模糊子串匹配**：
    它们权重最高（4）又是子串匹配，会把「看门狗」判给别名里含「看」的
    ctf-sandbox-orchestrator（历史缺陷）。单字词的正确用法是「整条消息恰好等于它」，
    由 route() 的精确词表处理，这里直接跳过。
    """
    weighted: dict[str, int] = {}
    for raw in values:
        full = normalize(raw)
        if not full:
            continue
        if len(full) >= 2:
            weighted[full] = max(weighted.get(full, 0), 4)
        for piece in SPLIT.split(full.replace("-", " ")):
            if piece and piece not in STOP and len(piece) >= 2:
                weighted[piece] = max(weighted.get(piece, 0), 1)
    return sorted(weighted.items(), key=lambda x: (-x[1], -len(x[0]), x[0]))


def hits(prompt: str, values: list[str]) -> list[tuple[str, int]]:
    return [(t, w) for t, w in expanded_terms(values) if t in prompt]


def build_catalog() -> dict:
    """从 _modules/alice_manifest.json 构建 Alice 能力目录：六类 → 技能 → 别名。"""
    manifest = load(MANIFEST, {})
    aliases = load(ALIASES, {})
    red = aliases.get("red", {})
    blue = aliases.get("blue", {})
    data = load(DATA, {})
    code_of = {s.get("name"): s.get("code", "") for s in data.get("skills", [])}
    rel_of = {s.get("name"): s.get("rel", "") for s in data.get("skills", [])}
    cats: dict[str, list[dict]] = {}
    for name, info in manifest.get("skills", {}).items():
        cat = info.get("class", "assist")
        terms = [name, CLASS_CN.get(cat, cat), info.get("desc", "")]
        for tbl in (red, blue):
            for word, targets in tbl.items():
                if name in targets:
                    terms.append(word)
        cats.setdefault(cat, []).append({
            "id": name, "label": info.get("desc", "")[:80], "terms": terms,
            "code": code_of.get(name, name), "rel": rel_of.get(name, info.get("rel", "")),
            "domain": info.get("domain"),
        })
    domains = {info.get("domain") for info in manifest.get("skills", {}).values() if info.get("domain")}
    return {"categories": cats, "cat_cn": CLASS_CN, "domain_count": len(domains)}


def _alias_index() -> dict[str, list[str]]:
    """精确路由词表：normalize(词) → [真实存在的目标模块 id]，red 优先于 blue。

    为什么要这张表：`route()` 的类词前缀逻辑会先吃掉首字（「破甲」→ 前缀「破」+
    body「甲」），而「甲」匹配不到任何模块 → 整条精确路由词落空。需要一张
    「整词精确命中」表，在类词前缀之前先用。
    """
    aliases = load(ALIASES, {})
    known = set(load(MANIFEST, {}).get("skills", {}))
    idx: dict[str, list[str]] = {}
    for table in ("red", "blue"):
        for word, targets in aliases.get(table, {}).items():
            key = normalize(word)
            if not key:
                continue
            bucket = idx.setdefault(key, [])
            for t in targets:
                if t in known and t not in bucket:
                    bucket.append(t)
    return idx


def _route_by_skill_id(catalog: dict, sid: str, mode: str, matched: list[str]) -> dict | None:
    """按模块 id 直接成路由结果（用于精确词命中）。"""
    for cat, skills in catalog["categories"].items():
        for sk in skills:
            if sk["id"] == sid:
                return {
                    "event": "route",
                    "mode": mode,
                    "category": f"{cat} {CLASS_CN.get(cat, cat)}",
                    "router": ROUTER.get(cat, "aliceskill"),
                    "skill": sk["id"],
                    "skill_code": sk["code"],
                    "domain": sk.get("domain"),
                    "domain_index": f"{ROUTER[cat]}/references/{sk['domain']}.md" if sk.get("domain") else None,
                    "matched_terms": matched,
                    "chain": ["target-lock", "open-router-skill", "pick-domain", "load-skill", "execute", "verify", "deliver"],
                }
    return None


def route(prompt: str) -> dict:
    text = normalize(prompt)
    catalog = build_catalog()
    # 路由页直达（正文在路由页/总控 SKILL.md，不在 _modules 模块里）
    if text in {normalize(w) for w in PAGE_WORDS}:
        page = PAGE_WORDS[[w for w in PAGE_WORDS if normalize(w) == text][0]]
        return {"event": "route", "mode": "class", "page_route": page,
                "category": "assist 技能指令" if page == "alice-assist" else "总控 技能菜单",
                "router": page, "skill": None,
                "chain": ["target-lock", "open-router-skill", "pick-domain", "pick-module", "execute", "verify", "deliver"]}
    # 模式词只设置模式，不固定映射到任何类别。
    if text in MODE_WORDS:
        return {"event": "activate", "mode": text, "full_chain": True,
                "coverage": sum(len(v) for v in catalog["categories"].values()),
                "domain_count": catalog["domain_count"]}
    # 类别词（旧快捷词与新版展示名称均支持）
    if text in CLASS_WORDS:
        return {"event": "route", "mode": "class",
                "class_route": ROUTER[CLASS_WORDS[text]],
                "category": f"{CLASS_WORDS[text]} {CLASS_CN[CLASS_WORDS[text]]}",
                "router": ROUTER[CLASS_WORDS[text]],
                "chain": ["target-lock", "open-router-skill", "pick-domain", "pick-module", "execute", "verify", "deliver"]}
    if text in {"alice", "爱丽丝"}:
        return {"event": "activate", "mode": text, "full_chain": True,
                "coverage": sum(len(v) for v in catalog["categories"].values()),
                "domain_count": catalog["domain_count"]}
    # 精确路由词优先于类词前缀：避免「破甲」被前缀「破」吞成 body「甲」而落空。
    idx = _alias_index()
    if text in idx:
        word = [w for w in load(ALIASES, {}).get("red", {}) if normalize(w) == text]
        matched = word or [text]
        for sid in idx[text]:
            hit = _route_by_skill_id(catalog, sid, "red", matched)
            if hit:
                return hit
    # 类目词前缀（破/逆/渗/挂/智/助 + 空格 + 正文）
    # 只有「前缀后的剩余部分能真正命中」时才按前缀算；否则回退整串匹配。
    # 否则「破甲」「破甲模式」会被前缀「破」吃掉首字，剩下「甲」匹配不到任何模块
    # → 整条精确路由词落空（历史缺陷）。
    for w in ("破", "逆", "渗", "挂", "智", "助"):
        if text.startswith(w) and len(text) > 1:
            cls = CLASS_WORDS[w]
            body = text[1:].strip()
            if not body:
                continue
            # 前缀 + 路由页直达词（如「助 技能评分」）→ 直接落到该路由页
            for pw, page in PAGE_WORDS.items():
                if normalize(pw) == body:
                    return {"event": "route", "mode": "class", "page_route": page,
                            "category": f"{cls} {CLASS_CN[cls]}",
                            "router": page, "skill": None,
                            "matched_terms": [w, pw],
                            "chain": ["target-lock", "open-router-skill", "pick-domain", "pick-module",
                                      "execute", "verify", "deliver"]}
            hit = _match_skill(catalog, cls, "blue" if w in ("破", "逆") else "red" if w in ("渗", "挂") else "class", body)
            if hit["event"] == "route":
                return hit
            # 前缀后无命中 → 不吞并，继续尝试整串
            break
    # 模式判定：攻/防 前缀
    mode = "red"
    if text.startswith("防") or text.startswith("blue"):
        mode = "blue"
    body = text[1:].strip() if text and text[0] in "攻防" else text
    if mode == "blue" and any(term in body for term in DEFENSE_TERMS):
        preferred = _match_skill(catalog, "reverse", mode, body)
        if preferred["event"] == "route":
            return preferred
        return {
            "event": "route", "mode": mode, "page_route": "alice-reverse",
            "category": "reverse 逆向分析", "router": "alice-reverse", "skill": None,
            "domain": None, "domain_index": None,
            "matched_terms": [term for term in DEFENSE_TERMS if term in body],
            "chain": ["target-lock", "open-router-skill", "pick-domain", "pick-module", "execute", "verify", "deliver"],
        }
    return _match_skill(catalog, None, mode, body)



def _match_skill(catalog: dict, cls: str | None, mode: str, body: str) -> dict:
    candidates = []
    for cat, skills in catalog["categories"].items():
        if cls and cat != cls:
            continue
        for skill in skills:
            sh = hits(body, skill["terms"])
            if not sh:
                continue
            # 评分：具体长词优先 → 命中权重和 → 命中数 → 分类稳定序
            score = (max(len(t) for t, _ in sh), sum(w for _, w in sh), len(sh),
                     -len(cat), skill["id"])
            candidates.append((score, cat, skill, sorted({t for t, _ in sh})))
    if not candidates:
        return {"event": "unmatched", "mode": mode, "normalized": body,
                "available_cats": [f"{k} {v}" for k, v in catalog["cat_cn"].items()]}
    _, cat, skill, terms = max(candidates, key=lambda x: (x[0], x[2]["id"]))
    return {
        "event": "route",
        "mode": mode,
        "category": f"{cat} {CLASS_CN.get(cat, cat)}",
        "router": ROUTER.get(cat, "aliceskill"),
        "skill": skill["id"],
        "skill_code": skill["code"],
        "domain": skill.get("domain"),
        "domain_index": f"{ROUTER[cat]}/references/{skill['domain']}.md" if skill.get("domain") else None,
        "matched_terms": terms,
        "chain": ["target-lock", "open-router-skill", "pick-domain", "load-skill", "execute", "verify", "deliver"],
    }


def cmd_route(a) -> int:
    r = route(a.prompt)
    print("=" * 60)
    if r["event"] == "activate":
        print(f"[✓] 激活: 「{r['mode']}」模式 | 全链覆盖 {r['coverage']} 技能 / {r['domain_count']} 个领域")
        print("    类别路由: 卡密授权→alice-crack 逆向分析→alice-reverse web安全→alice-pentest 游戏攻防→alice-game AI安全测试→alice-ai 技能指令→alice-assist")
        save(STATE_FILE, {"active": True, "last_route": r,
                          "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return 0
    elif r["event"] == "route" and r.get("skill"):
        print(f"[✓] 路由: {r['mode'].upper()} | {r['category']}")
        print(f"    技能: {r['skill']}（{r['skill_code']}）")
        print(f"    领域: {r.get('domain', '—')} | 索引: {r.get('domain_index', '—')}")
        print(f"    命中: {', '.join(r['matched_terms'][:6])}")
        print(f"    阶段链: {' → '.join(r['chain'])}")
        save(STATE_FILE, {"active": True, "last_route": r,
                          "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    elif r["event"] == "route" and r.get("page_route"):
        print(f"[✓] 路由页直达: {r['category']} → {r['page_route']}/SKILL.md")
        print(f"    阶段链: {' → '.join(r['chain'])}")
        save(STATE_FILE, {"active": True, "last_route": r,
                          "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    elif r["event"] == "route" and r.get("router"):
        print(f"[✓] 类目路由: {r['category']} → {r['router']}/SKILL.md")
        print(f"    阶段链: {' → '.join(r['chain'])}")
        save(STATE_FILE, {"active": True, "last_route": r,
                          "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    return 0


def cmd_status(a) -> int:
    st = load(STATE_FILE, {})
    print("=" * 60)
    if not st.get("active"):
        print("[⏳] 路由状态: 空闲（IDLE）")
        return 0
    r = st.get("last_route", {})
    print(f"[✓] 路由状态: 已路由（ROUTED）")
    print(f"    时间: {st.get('time')}")
    print(f"    技能: {r.get('skill', '—')} | 分类: {r.get('category', '—')} | 领域: {r.get('domain', '—')}")
    return 0


def cmd_selfcheck(a) -> int:
    print("=" * 60)
    web_route = route("攻 web sql注入")
    defense_route = route("防 样本分析")
    def index_exists(result: dict) -> bool:
        domain = result.get("domain")
        router = result.get("router")
        if not domain or not router:
            return False
        path = os.path.join(SKILL_DIR, "..", router, "references", f"{domain}.md")
        return os.path.isfile(path)

    checks = [
        ("NFKC归一化", normalize("ＳＱＬ注入") == "sql注入"),
        ("激活词", route("Alice")["event"] == "activate" and route("攻")["event"] == "activate" and route("防")["event"] == "activate"),
        ("路由匹配", web_route["event"] == "route" and bool(web_route.get("domain"))),
        ("术语扩展", len(expanded_terms(["web攻击", "sql注入"])) >= 2),
        ("类目词路由", route("破")["router"] == "alice-crack" and route("逆向分析")["router"] == "alice-reverse" and route("Web 安全")["router"] == "alice-pentest" and route("技能指令")["router"] == "alice-assist"),
        ("防御优先逆向", defense_route["router"] == "alice-reverse"),
        ("领域索引存在", index_exists(web_route) and index_exists(defense_route)),
        ("分类覆盖", set(build_catalog()["categories"].keys()) == {"crack", "reverse", "pentest", "game", "ai", "assist"}),
    ]
    ok = True
    for name, passed in checks:
        print(("  ✓ " if passed else "  ✗ ") + name)
        ok &= passed
    print(f"\n自检结果: {sum(p for _, p in checks)}/{len(checks)} 通过")
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Alice路由编排器")
    sub = p.add_subparsers(dest="cmd")
    rt = sub.add_parser("route")
    rt.add_argument("prompt")
    rt.set_defaults(func=cmd_route)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("selfcheck").set_defaults(func=cmd_selfcheck)
    a = p.parse_args()
    if not hasattr(a, "func"):
        p.print_help()
        return 0
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
