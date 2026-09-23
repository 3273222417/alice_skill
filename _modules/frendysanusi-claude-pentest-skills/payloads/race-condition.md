# Race Condition Payloads

## Overview
Race conditions occur when an application performs non-atomic check-then-act operations, allowing attackers to exploit the time window between the check and the action by sending concurrent requests.

## Methodology

### 1. Identify Vulnerable Operations (TOCTOU)
- Check balance → deduct balance (double-spend)
- Check coupon not used → apply coupon (reuse)
- Check vote count → increment (manipulation)
- Check rate limit → allow request (bypass)
- Check seat available → book seat (overbooking)

### 2. Testing Approach

| Technique | Best For |
|-----------|----------|
| **HTTP/2 single-packet** | Most reliable — all requests arrive simultaneously via multiplexing |
| **Last-byte sync (HTTP/1.1)** | Send all but last byte, then send final bytes simultaneously |
| **Connection warming** | Pre-establish connections to reduce jitter |
| **Turbo Intruder (Burp)** | Best tool — supports single-packet attacks |
| **Parallel curl** | Quick-and-dirty — `for i in $(seq 1 10); do curl ... &; done; wait` |

### 3. Common Targets
- Coupon/discount redemption
- Fund transfers / balance operations
- Vote/like manipulation
- Rate limit bypass
- Invitation/seat limits
- Account email change + password reset race

### 4. Documentation
Always record success rate: "Succeeded 7 out of 20 attempts" — important for the report.

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - Race Condition](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Race%20Condition)

For local curated payloads with script templates, see `local-payloads/race-condition.md`.

## Context Notes
- **HTTP/2 single-packet attacks** eliminate network timing as a variable
- **These tests can have side effects** — double-spending, duplicate records. Confirm with user
- **Turbo Intruder** (Burp extension) is the best tool for this
- **Document success rate** clearly in findings
