# JWT (JSON Web Token) Payloads

## Overview
JWT vulnerabilities arise from weak signing implementations, algorithm confusion, or improper validation, allowing token forgery, privilege escalation, or authentication bypass.

## Methodology

### 1. Decode the Token
JWT format: `base64(header).base64(payload).signature`. Always decode first to understand claims.

### 2. Attack Techniques

| Attack | Description | Precondition |
|--------|-------------|-------------|
| **Algorithm None** | Set `alg: "none"`, remove signature | Server accepts unsigned tokens |
| **RS256→HS256 confusion** | Switch to HMAC, sign with public key | Server doesn't enforce algorithm |
| **KID injection** | Path traversal or SQLi in `kid` header | `kid` value used in file/DB lookup |
| **JKU/X5U injection** | Point to attacker-hosted key | Server fetches keys from header URL |
| **Claim manipulation** | Modify `sub`, `role`, `is_admin` | After forging valid signature |
| **Weak secret brute-force** | Crack HMAC key with wordlist | HMAC algorithm with weak secret |
| **Expired token reuse** | Use expired token | Server doesn't check `exp` claim |

### 3. Testing Progression
1. Decode header — identify algorithm and `kid`
2. Try `alg: "none"` variants (`none`, `None`, `NONE`, `nOnE`)
3. Fetch public key from `/.well-known/jwks.json`
4. Try algorithm confusion if RS256
5. Test claim manipulation after signature bypass
6. Brute-force HMAC secrets with `hashcat -m 16500`

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - JWT](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/JSON%20Web%20Token)

For local curated payloads, see `local-payloads/jwt.md`.

## Context Notes
- **Algorithm none** is the quickest win — test first
- **Public key locations**: `/.well-known/jwks.json`, `/oauth/jwks`, TLS certificate
- **jwt.io** is useful for manual decoding/encoding
