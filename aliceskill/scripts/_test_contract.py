#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
import alice_contract

print("=== validate ===")
rc = alice_contract.cmd_validate(type("A", (), {})())
print("rc:", rc)

print("\n=== isolation: 代码块中的攻 ===")
print("prompt: 代码块 `攻` 里的内容")
rc = alice_contract.cmd_isolation(type("A", (), {"prompt": "这是一段示例：`攻` 是触发词"})())
print("rc:", rc)

print("\n=== isolation: 真实触发 ===")
rc = alice_contract.cmd_isolation(type("A", (), {"prompt": "攻 web 开始"})())
print("rc:", rc)
