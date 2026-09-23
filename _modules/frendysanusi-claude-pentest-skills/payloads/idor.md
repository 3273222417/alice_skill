# IDOR (Insecure Direct Object Reference) Payloads

## Overview
IDOR occurs when an application exposes internal object references (IDs, filenames, keys) and fails to verify the user is authorized to access the referenced object.

## Methodology

### 1. Identify Object References
- Sequential IDs in URLs: `/api/users/1001/profile`
- UUIDs in API responses, URLs, or JavaScript files
- Encoded/hashed IDs (Base64, MD5)
- GraphQL node IDs

### 2. Testing Approach
- **Horizontal IDOR**: Access another user's data at the same privilege level
- **Vertical IDOR**: Access admin resources as a regular user
- **Requires 2+ accounts** for reliable testing

### 3. Test Patterns

| Pattern | Technique |
|---------|-----------|
| Sequential ID | Increment/decrement the ID in the URL |
| UUID | Harvest UUIDs from API responses, JS files, error messages |
| Body parameter | Change `user_id` or `account_id` in POST/PUT body |
| HTTP method switch | If GET is blocked, try POST/PUT/PATCH/DELETE |
| Parameter pollution | `?id=1001&id=1002` (HPP) |
| GraphQL | Query `node(id: "...")` with another user's encoded ID |
| Encoded ID | Decode, modify, re-encode (Base64, URL encoding) |

### 4. What to Check
- Every endpoint that uses an object reference
- All HTTP methods (GET, POST, PUT, PATCH, DELETE)
- Both the URL path and request body
- API responses that leak other users' IDs

## Payload Reference

> Full methodology: [PayloadAllTheThings - IDOR](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Insecure%20Direct%20Object%20References)

For local curated payloads, see `local-payloads/idor.md`.

## Context Notes
- **UUID does not equal secure** — if UUIDs are leaked anywhere, they become predictable references
- **Always test with 2 accounts** — one to access the other's resources
- **Don't just test GET** — POST, PUT, PATCH, DELETE are often less protected
- **Mobile APIs** often have weaker IDOR protections than web
