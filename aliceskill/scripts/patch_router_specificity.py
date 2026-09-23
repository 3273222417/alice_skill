#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""评分精细化：①具体长词优先于泛词 ②补自然说法路由词。幂等。"""
from __future__ import annotations
import json, os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS)

# ---- ① alice_router 评分：最长命中词优先（具体压泛）----
P = os.path.join(THIS, "alice_router.py")
src = open(P, encoding="utf-8").read()
old = '''            # 同分裁定：命中词越多越优先，再比最长命中词（长意图压短词）
            score = (sum(w for _, w in sh), len(sh), max(len(t) for t, _ in sh),
                     -len(cat), skill["id"])'''
new = '''            # 评分：具体长词优先 → 命中权重和 → 命中数 → 分类稳定序
            score = (max(len(t) for t, _ in sh), sum(w for _, w in sh), len(sh),
                     -len(cat), skill["id"])'''
if new in src:
    print("  [skip] alice_router.score: 已应用")
elif old in src:
    open(P, "w", encoding="utf-8").write(src.replace(old, new, 1))
    print("  [ok] alice_router.score: 具体长词优先")
else:
    print("  [!] alice_router.score: 锚点未命中")

# ---- ② 补自然说法路由词 ----
ALIAS = os.path.join(SKILL_DIR, "config", "command_aliases.json")
OBJ = os.path.join(SKILL_DIR, "config", "system_objects.json")
al = json.load(open(ALIAS, encoding="utf-8"))
obj = {o.lower() for o in json.load(open(OBJ, encoding="utf-8"))["objects"]}
red = al["red"]

NATURAL = {
    # re-flow-orchestrator
    "要我完整破解": ["re-flow-orchestrator"],
    "开始破解任务": ["re-flow-orchestrator"],
    "破解到哪一步了": ["re-flow-orchestrator"],
    "破解进度": ["re-flow-orchestrator"],
    # re-env-sandbox
    "搭个隔离环境": ["re-env-sandbox"],
    "分析样本环境": ["re-env-sandbox"],
    "断网分析": ["re-env-sandbox"],
    "改系统时间实验": ["re-env-sandbox"],
    # re-flow-recon
    "这是什么壳": ["re-flow-recon"],
    "查一下壳": ["re-flow-recon"],
    "判断什么壳": ["re-flow-recon"],
    "它连了哪些地址": ["re-flow-recon"],
    # re-flow-unpack
    "IAT修不好": ["re-flow-unpack"],
    "dump完之后": ["re-flow-unpack"],
    "怎么脱壳": ["re-flow-unpack"],
    "OEP在哪": ["re-flow-unpack"],
    # re-flow-analyze
    "该hook还是patch": ["re-flow-analyze"],
    "hook还是patch": ["re-flow-analyze"],
    "断点下在哪": ["re-flow-analyze"],
    "卡密在哪比较": ["re-flow-analyze"],
    "改完怎么验证": ["re-flow-analyze"],
    # re-flow-capture
    "抓一下它的包": ["re-flow-capture"],
    "看看它发了什么请求": ["re-flow-capture"],
    # re-tool-manifest
    "装了哪些工具": ["re-tool-manifest"],
    "装了啥工具": ["re-tool-manifest"],
    "现在有什么工具": ["re-tool-manifest"],
    # re-tool-downloader
    "帮我把工具装上": ["re-tool-downloader"],
    "给我装ghidra": ["re-tool-downloader"],
    "下载个x64dbg": ["re-tool-downloader"],
    # windows-license-crack
    "注册机怎么写": ["windows-license-crack"],
    "怎么破这个软件": ["windows-license-crack"],
    "激活码怎么破": ["windows-license-crack"],
    "绕过签名校验": ["windows-license-crack"],
}

added, merged, blocked = 0, 0, []
for w, t in NATURAL.items():
    if w.lower() in obj:
        blocked.append(w)
        continue
    if w in red:
        nv = list(dict.fromkeys(list(red[w]) + t))
        if nv != red[w]:
            red[w] = nv
            merged += 1
    else:
        red[w] = list(t)
        added += 1
json.dump(al, open(ALIAS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"  [ok] 自然说法路由词: 新增 {added} 合并 {merged} | red 总数 {len(red)}")
if blocked:
    print(f"  [!] 对象词表冲突跳过: {blocked}")
