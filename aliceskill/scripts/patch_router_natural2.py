#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补「动词+工具」自然说法路由词（下载/安装优先于同名分析技能）。幂等。"""
from __future__ import annotations
import json, os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIAS = os.path.join(SKILL_DIR, "config", "command_aliases.json")
OBJ = os.path.join(SKILL_DIR, "config", "system_objects.json")
al = json.load(open(ALIAS, encoding="utf-8"))
obj = {o.lower() for o in json.load(open(OBJ, encoding="utf-8"))["objects"]}
red = al["red"]

MORE = {
    "下载工具装一下": ["re-tool-downloader"],
    "把工具装上": ["re-tool-downloader"],
    "工具装一下": ["re-tool-downloader"],
    "下载并安装": ["re-tool-downloader"],
    "下载安装工具": ["re-tool-downloader"],
    "帮我下载工具": ["re-tool-downloader"],
    "环境里有哪些工具": ["re-tool-manifest"],
    "工具装了没": ["re-tool-manifest"],
    "环境体检": ["re-tool-manifest"],
    "还缺哪些工具": ["re-tool-manifest"],
    "看看这个程序是什么壳": ["re-flow-recon"],
    "这个程序连了什么": ["re-flow-recon"],
    "脱完壳怎么办": ["re-flow-unpack"],
    "脱壳之后": ["re-flow-unpack"],
    "破解到什么程度": ["re-flow-orchestrator"],
    "下一步该干什么": ["re-flow-orchestrator"],
    "卡密校验在哪": ["re-flow-analyze"],
    "定位校验函数": ["re-flow-analyze"],
    "打补丁还是hook": ["re-flow-analyze"],
    "补丁打完怎么验": ["re-flow-analyze"],
    "抓它的网络流量": ["re-flow-capture"],
    "把流量抓下来": ["re-flow-capture"],
    "样本隔离跑": ["re-env-sandbox"],
    "回滚到快照": ["re-env-sandbox"],
    "破解激活码": ["windows-license-crack"],
    "破解卡密": ["windows-license-crack"],
    "写注册机": ["windows-license-crack"],
    "验签怎么绕": ["windows-license-crack"],
}
added, merged, blocked = 0, 0, []
for w, t in MORE.items():
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
print(f"  [ok] 动词+工具自然说法: 新增 {added} 合并 {merged} | red 总数 {len(red)}")
if blocked:
    print(f"  [!] 对象词表冲突跳过: {blocked}")
