# OAuth / OIDC Payloads

## Overview
OAuth 2.0 and OpenID Connect vulnerabilities arise from improper implementation of the authorization flow, allowing token theft, account takeover, or privilege escalation.

## Methodology

### 1. Map OAuth Flow
- Fetch `/.well-known/openid-configuration` for all endpoints
- Identify flow type: Authorization Code, Implicit (deprecated), PKCE

### 2. Attack Techniques

| Attack | Target | Technique |
|--------|--------|-----------|
| **Redirect URI manipulation** | `/authorize` endpoint | Subdomain, path traversal, encoding, `@` symbol tricks |
| **State parameter absence** | CSRF on login | Remove `state` param — forces victim to log in as attacker |
| **Token leakage** | Implicit flow | Tokens in URL leak via Referer, browser history |
| **Scope escalation** | Token request | Add `admin`, `write`, `*` to scope parameter |
| **PKCE downgrade** | Code exchange | Remove `code_challenge` — if token still issued, PKCE not enforced |
| **Authorization code reuse** | Token endpoint | Use same code twice — should only work once |
| **Client secret brute-force** | Token endpoint | Try common secrets: `secret`, `password`, `client_id` |

### 3. Redirect URI Bypass Patterns
- `https://trusted.com@evil.com`
- `https://trusted.com.evil.com`
- `https://trusted.com%40evil.com`
- `https://evil.com#.trusted.com`
- `https://trusted.com/../evil`

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - OAuth](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/OAuth%20Misconfiguration/README.md)

For local curated payloads, see `local-payloads/oauth.md`.

## Context Notes
- **redirect_uri manipulation** is the most common and impactful OAuth vulnerability
- **Implicit flow** is deprecated and inherently insecure — if found, note as finding
- **OIDC discovery** (`/.well-known/openid-configuration`) reveals all endpoint URLs
