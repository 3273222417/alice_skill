#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量创建 Codex 侧边栏会话 (session-batch-creator)

用法:
  python create_sessions.py --title "网站开发" --count 5
  python create_sessions.py --from "网站开发 创建五个"
  python create_sessions.py --from "创建三个 测试"
  python create_sessions.py --title "网站开发" --count 5 --clone-from <session_id>
  python create_sessions.py --delete <session_id> [<session_id> ...]

创建后自动注册 5 处（与本机 Codex 桌面端存储结构一致）:
  1. rollout JSONL 会话文件  ~/.codex/sessions/<yyyy>/<mm>/<dd>/rollout-*.jsonl
  2. session_index.jsonl 索引
  3. state_5.sqlite (threads 表)
  4. .codex-global-state.json (桌面端 UI 状态: 项目归属/心跳权限/提示历史)
  5. config.toml ([projects.'<session_id>'] trust_level = "trusted")
"""
import argparse
import datetime
import json
import os
import random
import re
import shutil
import sqlite3
import sys
import time

CODEX_HOME = os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")
SESSIONS_ROOT = os.path.join(CODEX_HOME, "sessions")
INDEX_FILE = os.path.join(CODEX_HOME, "session_index.jsonl")
STATE_DB = os.path.join(CODEX_HOME, "state_5.sqlite")
GLOBAL_STATE_FILE = os.path.join(CODEX_HOME, ".codex-global-state.json")
CONFIG_FILE = os.path.join(CODEX_HOME, "config.toml")
BACKUP_ROOT = os.path.join(CODEX_HOME, "backups")
DEFAULT_CWD = r"C:\Users\Administrator\Documents\openclaw"
# 参考会话: 用于继承 git 信息 / 模型 / 权限等默认列值
REFERENCE_THREAD_ID = "01a04e4c-83e6-7273-a271-e6a83d9e6398"
DEFAULT_PERM = {
    "activePermissionProfile": {"id": ":danger-full-access", "extends": None},
    "approvalPolicy": "never",
    "approvalsReviewer": "user",
    "sandboxPolicy": {"type": "dangerFullAccess"},
}

# ---------------- 终端 UI ----------------
class UI:
    def __init__(self):
        self.color = sys.stdout.isatty()
    def paint(self, s, code):
        return f"\033[{code}m{s}\033[0m" if self.color else s
    def ok(self, s):   return self.paint(s, "32")
    def err(self, s):  return self.paint(s, "31")
    def warn(self, s): return self.paint(s, "33")
    def info(self, s): return self.paint(s, "36")
    def title(self, s): return self.paint(s, "1;35")
    def banner(self, text):
        line = "=" * 58
        print(self.info(line)); print(self.title(text)); print(self.info(line))

# ---------------- 基础工具 ----------------
def utc_now_iso():
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"

def local_now_str():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

def uuid7():
    ms = int(time.time() * 1000)
    b = bytearray(16)
    b[0] = (ms >> 40) & 0xFF; b[1] = (ms >> 32) & 0xFF
    b[2] = (ms >> 24) & 0xFF; b[3] = (ms >> 16) & 0xFF
    b[4] = (ms >> 8) & 0xFF;  b[5] = ms & 0xFF
    b[6] = 0x70 | (random.getrandbits(4) & 0x0F)
    b[7] = random.getrandbits(8)
    b[8] = 0x80 | (random.getrandbits(6) & 0x3F)
    for i in range(9, 16):
        b[i] = random.getrandbits(8)
    h = b.hex()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

def backup(path, tag):
    if not os.path.exists(path):
        return None
    os.makedirs(BACKUP_ROOT, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(BACKUP_ROOT, f"{os.path.basename(path)}.bak.{tag}-{ts}")
    shutil.copy2(path, dst)
    return dst

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))

def find_rollout(sid):
    for root, _dirs, files in os.walk(SESSIONS_ROOT):
        for fn in files:
            if sid in fn and fn.endswith(".jsonl"):
                return os.path.join(root, fn)
    return None

# ---------------- 中文数字 / 输入解析 ----------------
CN = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

def parse_count_token(tok):
    tok = tok.strip()
    if not tok:
        return None
    if tok.isdigit():
        return int(tok)
    if "十" in tok:
        left, _, right = tok.partition("十")
        tens = (CN.get(left, 1) if left else 1) * 10
        ones = CN.get(right, 0) if right else 0
        return tens + ones
    if tok in CN:
        return CN[tok]
    try:
        return sum(CN.get(ch, 0) for ch in tok)
    except TypeError:
        return None

def clean_title(text):
    t = text.strip()
    while True:
        nt = re.sub(r"^(创建|新建|添加|给我|帮我|来|搞|弄)\s*", "", t)
        if nt == t:
            break
        t = nt
    while True:
        nt = re.sub(r"\s*(创建|新建|添加|来|搞|弄|吧|啊|了|个|会话|任务|聊天|侧边栏|项目)$", "", t)
        if nt == t:
            break
        t = nt
    return t.strip() or "新会话"

def parse_request(text):
    m = re.search(r"([0-9]+|[零一二两三四五六七八九十]{1,3})\s*个?", text)
    count = None
    if m:
        count = parse_count_token(m.group(1))
        text = text[:m.start()] + text[m.end():]
    title = clean_title(text)
    return title, count

# ---------------- 创建单个会话 ----------------
def create_rollout(nid, cwd, clone_from):
    d = datetime.datetime.now()
    day_dir = os.path.join(SESSIONS_ROOT, str(d.year), f"{d.month:02d}", f"{d.day:02d}")
    os.makedirs(day_dir, exist_ok=True)
    fpath = os.path.join(day_dir, f"rollout-{local_now_str()}-{nid}.jsonl")
    now = utc_now_iso()
    if clone_from:
        src = find_rollout(clone_from)
        if not src:
            raise SystemExit(f"[x] 克隆源会话不存在: {clone_from}")
        with open(src, encoding="utf-8") as f:
            lines = f.read().splitlines()
        meta = json.loads(lines[0])
        meta["timestamp"] = now
        p = meta["payload"]
        p["session_id"] = nid; p["id"] = nid; p["parent_thread_id"] = clone_from
        p["timestamp"] = now
        body = lines[1:]
    else:
        meta = {
            "timestamp": now,
            "type": "session_meta",
            "payload": {
                "session_id": nid, "id": nid, "timestamp": now,
                "cwd": cwd, "originator": "Codex Desktop",
                "cli_version": "0.146.0-alpha.9.2", "source": "vscode",
                "thread_source": "user", "model_provider": "custom",
                "base_instructions": {"text": "# Codex bridge instructions\n\nUse the configured model provider and follow the user's requests."},
                "dynamic_tools": [],
            },
        }
        body = []
    with open(fpath, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")
        for ln in body:
            f.write(ln + "\n")
    return fpath

# ---------------- 注册到各存储 ----------------
def append_index(entries):
    backup(INDEX_FILE, "index")
    with open(INDEX_FILE, "a", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

def insert_threads(rows, edges):
    backup(STATE_DB, "db")
    con = sqlite3.connect(STATE_DB, timeout=15)
    try:
        cur = con.cursor()
        cur.execute("SELECT * FROM threads WHERE id=?", (REFERENCE_THREAD_ID,))
        src = cur.fetchone()
        if src is None:
            cur.execute("SELECT * FROM threads LIMIT 1")
            src = cur.fetchone()
        if src is None:
            raise SystemExit("[x] state_5.sqlite 里没有可参考的 threads 行")
        cols = [d[0] for d in cur.description]
        for r in rows:
            merged = dict(zip(cols, src))
            merged.update(r)
            vals = [merged.get(c) for c in cols]
            cur.execute(f"INSERT INTO threads ({','.join(cols)}) VALUES ({','.join(['?'] * len(cols))})", vals)
        for parent, child in edges:
            cur.execute("INSERT INTO thread_spawn_edges (parent_thread_id, child_thread_id, status) VALUES (?,?,?)",
                        (parent, child, "open"))
        con.commit()
    finally:
        con.close()

def resolve_project(data, cwd):
    tpa = data.get("thread-project-assignments", {})
    cwd_l = cwd.lower().replace("\\\\", "\\")
    for _nid, a in tpa.items():
        if isinstance(a, dict) and a.get("cwd", "").lower().replace("\\\\", "\\") == cwd_l:
            return a
    return None

def update_global_state(assignments, perms, histories, projectless_add):
    backup(GLOBAL_STATE_FILE, "gs")
    data = load_json(GLOBAL_STATE_FILE, {})
    atom = data.setdefault("electron-persisted-atom-state", {})
    tpa = data.setdefault("thread-project-assignments", {})
    hb = atom.setdefault("heartbeat-thread-permissions-by-id", {})
    ph = atom.setdefault("prompt-history", {})
    pl = data.setdefault("projectless-thread-ids", [])
    for nid, a in assignments.items():
        if nid not in tpa and a is not None:
            tpa[nid] = a
    for nid, p in perms.items():
        if nid not in hb:
            hb[nid] = p
    for nid, h in histories.items():
        if nid not in ph:
            ph[nid] = h
    for nid in projectless_add:
        if nid not in pl:
            pl.append(nid)
    save_json(GLOBAL_STATE_FILE, data)

def add_config_entries(ids):
    if not ids:
        return 0
    backup(CONFIG_FILE, "cfg")
    with open(CONFIG_FILE, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8")
    added = [nid for nid in ids if f"[projects.'{nid}']" not in text]
    if not added:
        return 0
    block = "\n\n# ===== 批量会话登记 (session-batch-creator) =====\n"
    for nid in added:
        block += f"[projects.'{nid}']\ntrust_level = \"trusted\"\n\n"
    with open(CONFIG_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(text.rstrip("\n") + "\n" + block)
    return len(added)

def remove_config_entries(ids):
    if not ids:
        return
    backup(CONFIG_FILE, "cfg-del")
    with open(CONFIG_FILE, "rb") as f:
        text = f.read().decode("utf-8")
    for nid in ids:
        text = re.sub(re.escape(f"[projects.'{nid}']") + r"\ntrust_level = \"trusted\"\n\n?", "", text)
    text = re.sub(r"\n# ===== [^\n]*\(session-batch-creator\) =====\n", "\n", text)
    with open(CONFIG_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(text)

# ---------------- 删除 ----------------
def delete_sessions(ids, ui):
    ui.banner("删除会话 (session-batch-creator)")
    for nid in ids:
        fp = find_rollout(nid)
        if fp and os.path.exists(fp):
            os.remove(fp)
            print(ui.ok(f"[+] 删除文件 {fp}"))
        else:
            print(ui.warn(f"[!] 未找到文件 {nid}"))
    backup(INDEX_FILE, "index-del")
    keep = []
    with open(INDEX_FILE, encoding="utf-8") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                keep.append(line)
                continue
            if o.get("id") in ids:
                continue
            keep.append(line.rstrip("\n"))
    with open(INDEX_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(keep) + "\n")
    print(ui.ok(f"[+] 清理 session_index.jsonl ({len(ids)} 条)"))
    backup(STATE_DB, "db-del")
    con = sqlite3.connect(STATE_DB, timeout=15)
    try:
        cur = con.cursor()
        q = ",".join("?" for _ in ids)
        cur.execute(f"DELETE FROM threads WHERE id IN ({q})", ids)
        n_threads = cur.rowcount
        cur.execute(f"DELETE FROM thread_spawn_edges WHERE child_thread_id IN ({q})", ids)
        con.commit()
        print(ui.ok(f"[+] 清理 state_5.sqlite (threads {n_threads})"))
    finally:
        con.close()
    backup(GLOBAL_STATE_FILE, "gs-del")
    data = load_json(GLOBAL_STATE_FILE, {})
    tpa = data.get("thread-project-assignments", {})
    hb = data.get("electron-persisted-atom-state", {}).get("heartbeat-thread-permissions-by-id", {})
    ph = data.get("electron-persisted-atom-state", {}).get("prompt-history", {})
    pl = data.get("projectless-thread-ids", [])
    for nid in ids:
        tpa.pop(nid, None)
        hb.pop(nid, None)
        ph.pop(nid, None)
    data["projectless-thread-ids"] = [x for x in pl if x not in ids]
    save_json(GLOBAL_STATE_FILE, data)
    print(ui.ok("[+] 清理 .codex-global-state.json"))
    remove_config_entries(ids)
    print(ui.ok("[+] 清理 config.toml"))
    print(ui.ok("完成。"))
    return 0

# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser(description="批量创建 Codex 侧边栏会话")
    ap.add_argument("--title", help="会话标题，如 网站开发")
    ap.add_argument("--count", type=int, help="创建数量，如 5")
    ap.add_argument("--from", dest="from_str", help="自然语言，如 网站开发 创建五个")
    ap.add_argument("--clone-from", help="克隆已有会话 id（可选）")
    ap.add_argument("--cwd", default=DEFAULT_CWD, help="工作目录（默认 openclaw）")
    ap.add_argument("--no-config", action="store_true", help="不写 config.toml")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不写文件")
    ap.add_argument("--delete", nargs="+", help="删除指定会话 id")
    args = ap.parse_args()

    ui = UI()
    if args.delete:
        return delete_sessions(args.delete, ui)

    if args.from_str:
        title, count = parse_request(args.from_str)
    else:
        title, count = args.title, args.count
    if not title:
        print(ui.err("[x] 缺少标题。示例: --title \"网站开发\" --count 5  或  --from \"网站开发 创建五个\"  --help"))
        return 2
    if not count or count <= 0:
        print(ui.err("[x] 缺少数量。示例: --count 5  /  创建五个  /  3个"))
        return 2

    ui.banner(f"批量创建会话: {title} x {count}")
    ids = [uuid7() for _ in range(count)]
    print(ui.info(f"[>] 生成 {count} 个会话 ID"))
    if args.dry_run:
        for i, nid in enumerate(ids, 1):
            print(f"  - {title} 副本{i}  {nid}")
        print(ui.warn("[!] dry-run 模式，未写入任何文件"))
        return 0

    now_ms = int(time.time() * 1000)
    now_s = now_ms // 1000
    now_iso = utc_now_iso()

    files = []
    for i, nid in enumerate(ids, 1):
        fp = create_rollout(nid, args.cwd, args.clone_from)
        files.append(fp)
        print(ui.ok(f"[✓] 会话 {i}/{count}  {title} 副本{i}  {nid}"))

    entries = [{"id": nid, "thread_name": f"{title} 副本{i+1}", "updated_at": now_iso} for i, nid in enumerate(ids)]
    append_index(entries)
    print(ui.ok(f"[✓] session_index.jsonl 追加 {len(entries)} 条"))

    rows = []
    edges = []
    for i, nid in enumerate(ids, 1):
        rows.append({
            "id": nid,
            "rollout_path": "\\\\?\\" + files[i-1],
            "created_at": now_s, "updated_at": now_s,
            "created_at_ms": now_ms, "updated_at_ms": now_ms,
            "title": f"{title} 副本{i}",
            "first_user_message": title,
            "preview": f"{title} 副本{i}",
            "recency_at": now_s, "recency_at_ms": now_ms,
            "tokens_used": 0, "has_user_event": 0, "archived": 0, "is_pinned": 0,
        })
        if args.clone_from:
            edges.append((args.clone_from, nid))
    insert_threads(rows, edges)
    print(ui.ok(f"[✓] state_5.sqlite threads 插入 {len(rows)} 行" + (f", 派生关系 {len(edges)} 条" if edges else "")))

    gs = load_json(GLOBAL_STATE_FILE, {})
    proj = resolve_project(gs, args.cwd)
    assignments = {}
    perms = {}
    histories = {}
    projectless = []
    for nid in ids:
        perms[nid] = json.loads(json.dumps(DEFAULT_PERM))
        histories[nid] = []
        if proj is not None:
            assignments[nid] = json.loads(json.dumps(proj))
        else:
            projectless.append(nid)
    update_global_state(assignments, perms, histories, projectless)
    if proj:
        print(ui.ok("[✓] .codex-global-state.json 登记完成（项目归属: " + proj.get("projectId", "?") + "）"))
    else:
        print(ui.ok("[✓] .codex-global-state.json 登记完成（无匹配项目，加入 projectless）"))

    if not args.no_config:
        n = add_config_entries(ids)
        print(ui.ok(f"[✓] config.toml 追加 [projects] 登记 {n} 条"))
    else:
        print(ui.warn("[!] 已跳过 config.toml（--no-config）"))

    ui.banner("完成")
    print(f"{'会话名':<16}{'会话 ID':<40}")
    print("-" * 58)
    for i, nid in enumerate(ids, 1):
        print(f"{ui.info(title + ' 副本' + str(i)):<18}{nid}")
    print()
    print(ui.warn("提示: 若侧边栏未立即显示，重启 Codex 桌面端。"))
    print(ui.warn("备份目录: " + BACKUP_ROOT))
    return 0

if __name__ == "__main__":
    sys.exit(main())