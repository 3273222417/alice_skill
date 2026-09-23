#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice契约校验器（吸收工具链契约校验机制 · 已归属Alice）
================================================================
校验对象：
  ① contracts/alice_contract.json    能力契约（schema/版本/激活/状态机/控制命令/上下文隔离）
  ② scripts/skills_data.json      技能覆盖（五类 / 全量技能 / 无重复）
  ③ config/command_aliases.json   路由词（与对象词表零交叉 / 无重复 / 无空映射）
  ④ 上下文隔离物理校验（引用中的触发词不参与路由评分）

用法:
  python alice_contract.py validate          # 全量契约校验
  python alice_contract.py check-skills      # 技能覆盖校验
  python alice_contract.py check-aliases     # 路由词校验
  python alice_contract.py isolation "攻 web"  # 上下文隔离校验
  python alice_contract.py selfcheck
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(THIS_DIR)
CONTRACT = os.path.join(SKILL_DIR, "contracts", "alice_contract.json")
SKILLS = os.environ.get("ALICE_DATA") or os.path.join(THIS_DIR, "skills_data.json")
ALIASES = os.path.join(SKILL_DIR, "config", "command_aliases.json")
OBJECTS = os.path.join(SKILL_DIR, "config", "system_objects.json")


ALICE_CLASSES = ("crack", "reverse", "pentest", "game", "ai", "assist")


def load(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default if default is not None else {}


def ok(msg: str) -> None:
    print("  [✓] " + msg)


def fail(msg: str) -> None:
    print("  [✗] " + msg)


def need(cond: bool, msg: str) -> None:
    if cond:
        ok(msg)
    else:
        fail(msg)


def validate_contract() -> list[str]:
    """① 契约结构校验。返回失败清单。"""
    errors = []
    c = load(CONTRACT, {})
    if c.get("schema") != 1:
        errors.append("契约 schema != 1")
    if not c.get("version"):
        errors.append("契约缺 version")
    act = c.get("activation", {})
    if "攻" not in act.get("exact", []) or "防" not in act.get("exact", []) or "Alice" not in act.get("exact", []):
        errors.append("激活词必须含 攻/防/Alice")
    sm = c.get("state_machine", {})
    states = sm.get("states", [])
    if len(states) != len(set(states)):
        errors.append("状态机存在重复状态")
    if not sm.get("transitions"):
        errors.append("状态机缺转换")
    cmds = sm.get("control_commands", {})
    if "[[ALICE:ARMOR=ON]]" not in cmds:
        errors.append("缺控制命令 [[ALICE:ARMOR=ON]]")
    ci = c.get("context_isolation", {})
    if not ci.get("rule") or not ci.get("checker"):
        errors.append("上下文隔离规则不完整")
    dm = c.get("domains", {})
    if dm.get("expected") != 6:
        errors.append("契约期望分类数 != 6")
    return errors


def check_skills() -> list[str]:
    """② 技能覆盖校验。"""
    errors = []
    d = load(SKILLS, {})
    skills = d.get("skills", [])
    if len(skills) < 200:
        errors.append(f"技能数不足: {len(skills)}")
    names = [s.get("name", "") for s in skills]
    dups = {n for n in names if names.count(n) > 1}
    if dups:
        errors.append(f"技能名重复: {dups}")
    codes = [s.get("code", "") for s in skills]
    if len(codes) != len(set(codes)):
        errors.append("技能编号重复")
    cats = {s.get("category") for s in skills}
    if cats != set(ALICE_CLASSES):
        errors.append(f"分类集合 != 五类: {sorted(cats)}")
    unclass = [s.get("name") for s in skills if s.get("category") not in ALICE_CLASSES]
    if unclass:
        errors.append(f"未分类技能: {unclass[:5]}")
    return errors


def check_aliases() -> list[str]:
    """③ 路由词校验（三空间零交叉）。"""
    errors = []
    a = load(ALIASES, {})
    obj = load(OBJECTS, {})
    obj_words = {o.lower() for o in obj.get("objects", [])}
    red = a.get("red", {})
    blue = a.get("blue", {})
    words = list(red.keys()) + list(blue.keys())
    conflict = [w for w in words if w.lower() in obj_words]
    if conflict:
        errors.append(f"路由词与对象词表交叉: {conflict}")
    red_set = set(red.keys())
    blue_set = set(blue.keys())
    cross = red_set & blue_set
    if cross:
        # 攻防共用词是Alice设计（build_commands 会合并去重），非错误，仅提示
        print(f"  [i] 攻防共用词（设计允许，build_commands 合并）: {sorted(cross)[:8]}")
    empty = [w for w in words if not (red.get(w) or blue.get(w))]
    if empty:
        errors.append(f"空映射路由词: {empty[:5]}")
    return errors


def isolation_check(prompt: str) -> list[str]:
    """④ 上下文隔离物理校验：剥离引用区后，激活词/触发词不误判。"""
    errors = []
    text = prompt
    # 剥离代码块、行内代码、引号
    stripped = re.sub(r"```.*?```", " ", text, flags=re.S)
    stripped = re.sub(r"`[^`]*`", " ", stripped)
    stripped = re.sub(r"[“\"'].*?[”\"']", " ", stripped, flags=re.S)
    norm = unicodedata.normalize("NFKC", stripped).casefold()
    # 如果原句只有引用区含激活词，剥离后不应触发
    if "攻" in text and "攻" not in norm:
        ok("引用区「攻」已隔离（不触发激活）")
    elif "攻" in text and "攻" in norm:
        errors.append("激活词在指令区，属正常触发")
    return errors


def cmd_validate(a) -> int:
    print("=" * 60)
    print("  Alice契约校验")
    print("=" * 60)
    all_errors = []
    print("\n① 能力契约")
    all_errors += validate_contract()
    print("\n② 技能覆盖")
    all_errors += check_skills()
    print("\n③ 路由词三空间")
    all_errors += check_aliases()
    if all_errors:
        print("\n[✗] 校验失败:")
        for e in all_errors:
            fail(e)
        return 1
    print("\n[✓] 全部契约校验通过")
    return 0


def cmd_check_skills(a) -> int:
    errors = check_skills()
    if errors:
        for e in errors:
            fail(e)
        return 1
    ok("技能覆盖校验通过")
    return 0


def cmd_check_aliases(a) -> int:
    errors = check_aliases()
    if errors:
        for e in errors:
            fail(e)
        return 1
    ok("路由词三空间校验通过")
    return 0


def cmd_isolation(a) -> int:
    errors = isolation_check(a.prompt)
    if errors:
        for e in errors:
            fail(e)
        return 1
    ok("上下文隔离校验通过")
    return 0


def cmd_selfcheck(a) -> int:
    checks = [
        ("契约结构", len(validate_contract()) == 0),
        ("技能覆盖", len(check_skills()) == 0),
        ("路由三空间", len(check_aliases()) == 0),
        ("控制命令", "[[ALICE:ARMOR=ON]]" in load(CONTRACT, {}).get("state_machine", {}).get("control_commands", {})),
        ("状态机", len(load(CONTRACT, {}).get("state_machine", {}).get("states", [])) >= 5),
    ]
    all_ok = True
    for name, passed in checks:
        print(("  ✓ " if passed else "  ✗ ") + name)
        all_ok &= passed
    print(f"\n自检结果: {sum(p for _, p in checks)}/{len(checks)} 通过")
    return 0 if all_ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Alice契约校验器")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("validate").set_defaults(func=cmd_validate)
    sub.add_parser("check-skills").set_defaults(func=cmd_check_skills)
    sub.add_parser("check-aliases").set_defaults(func=cmd_check_aliases)
    iso = sub.add_parser("isolation")
    iso.add_argument("prompt")
    iso.set_defaults(func=cmd_isolation)
    sub.add_parser("selfcheck").set_defaults(func=cmd_selfcheck)
    a = p.parse_args()
    if not hasattr(a, "func"):
        p.print_help()
        return 0
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
