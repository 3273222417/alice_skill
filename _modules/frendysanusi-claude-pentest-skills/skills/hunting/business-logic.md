# Hunting Skill: Business Logic Vulnerabilities

Covers: Race Conditions, Workflow Bypass, Price/Quantity Manipulation, Feature Abuse

## Sub-Class Resolution

| Sub-Class | Payload File | WSTG Reference |
|-----------|-------------|----------------|
| `race-condition` | `payloads/race-condition.md` | WSTG-BUSL-07 |

## Methodology

Business logic vulnerabilities are **unique to each application** — they can't be found with generic payloads. This skill requires understanding the application's purpose and assumptions.

### Step 1: Understand the Application's Business Logic

Before testing, answer:
- What does this application do? (e-commerce, banking, social, SaaS?)
- What are the high-value operations? (payments, transfers, account creation, content publishing)
- What are the trust assumptions? (users can't set their own prices, coupons are single-use, etc.)
- What are the multi-step workflows? (checkout: cart → address → payment → confirm)

### Step 2: Workflow Bypass Testing (WSTG-BUSL-01, 02)

Test if steps in multi-step processes can be skipped:

1. **Identify multi-step workflows** (registration, checkout, approval processes)
2. **Skip steps**: Go directly to step 3 URL without completing steps 1-2
3. **Replay earlier steps**: Go back to step 1 after completing step 3
4. **Modify step order**: Submit step 3 data to step 2 endpoint

```
# Example: Checkout flow bypass
# Normal: /cart → /shipping → /payment → /confirm
# Test: Direct POST to /confirm without going through /payment
# Test: Complete /payment with $0, then /confirm
```

### Step 3: Parameter Manipulation (WSTG-BUSL-03, 04)

Test if business-critical values can be modified:

1. **Price manipulation**: Intercept checkout request, change price to $0.01 or negative
2. **Quantity manipulation**: Set quantity to 0, -1, or extremely large numbers
3. **Discount/coupon abuse**: Apply same coupon multiple times, use expired coupons
4. **Currency confusion**: If multi-currency, test conversion edge cases
5. **Role/permission in request**: Add `role=admin` or `is_premium=true`

```
# Price manipulation examples:
POST /api/checkout
{"item_id": 1, "quantity": 1, "price": 0.01}    # Client-controlled price
{"item_id": 1, "quantity": -1, "price": 99.99}   # Negative quantity = credit?
{"item_id": 1, "quantity": 999999}                # Integer overflow
```

### Step 4: Race Condition Testing (WSTG-BUSL-07)

Load `payloads/race-condition.md` for concurrent request templates.

Common targets:
1. **Coupon/discount redemption**: Redeem same code concurrently
2. **Balance operations**: Transfer more than available balance concurrently
3. **Vote/like manipulation**: Vote multiple times simultaneously
4. **Rate limit bypass**: Send requests faster than the limit allows
5. **Invitation/seat limits**: Join when at capacity using concurrent requests

**Warn the user before testing** — race conditions can have real side effects.

### Step 5: Feature Abuse (WSTG-BUSL-05, 06)

Test if legitimate features can be abused:

1. **Email functionality abuse**: Can the app be used to send spam? (password reset to arbitrary emails)
2. **File generation abuse**: Can PDF/image generation be used for SSRF or resource exhaustion?
3. **Referral system abuse**: Can referral rewards be self-granted?
4. **API rate limit abuse**: Are expensive operations rate-limited?
5. **Data export abuse**: Can export features be used to enumerate all data?

### Step 6: Integer/Boundary Testing (WSTG-BUSL-08, 09)

Test boundary values:
```
0, -1, -999999
2147483647 (INT_MAX 32-bit)
9999999999999999 (large number)
0.001, 0.0000001 (tiny decimals)
NaN, Infinity, null, undefined
Empty string ""
Very long strings (10000+ chars)
```

### Step 7: Update Coverage

Mark WSTG-BUSL-01 through WSTG-BUSL-09 in `coverage.md`.

## Context Notes

- **Business logic bugs are the hardest to find** but often the most impactful — they can't be detected by scanners
- **Conversational interaction is key**: Discuss your hypotheses with the user — they understand the business context better
- **Always think about chains**: A low-severity logic flaw + another low-severity issue might chain into a high-severity finding
- **Document the expected vs actual behavior** clearly in findings
