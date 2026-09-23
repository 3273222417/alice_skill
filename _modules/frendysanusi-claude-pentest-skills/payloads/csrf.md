# CSRF (Cross-Site Request Forgery) Payloads

## Overview
CSRF occurs when a malicious site tricks a victim's browser into making an authenticated request to a target application, performing unwanted actions on behalf of the authenticated user.

## Methodology

### 1. Identify Targets
Focus on state-changing requests (POST/PUT/DELETE) that:
- Change user settings (email, password)
- Transfer money / make purchases
- Create/delete content
- Change permissions/roles

### 2. Check Defenses

| Defense | How to Test |
|---------|------------|
| Anti-CSRF token | Remove it — does the request still succeed? |
| SameSite cookie | `Lax` blocks cross-site POST but allows GET |
| Referer validation | Add `<meta name="referrer" content="no-referrer">` |
| Re-authentication | Sensitive actions require password re-entry |

### 3. PoC Techniques

| Technique | Use When |
|-----------|----------|
| Auto-submit form (POST) | Standard form-based CSRF |
| Image tag (GET) | State change via GET request |
| Fetch API | Modern JavaScript-based CSRF |
| JSON body via `text/plain` | API expects JSON but doesn't validate Content-Type |
| `enctype="text/plain"` trick | Craft JSON-like body via form |

### 4. Bypass Techniques
- Remove token entirely (check if validation is optional)
- Use another user's token (check if token is tied to session)
- Change POST to GET
- Remove Referer with meta tag

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - CSRF](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Cross-Site%20Request%20Forgery)

For local curated payloads, see `local-payloads/csrf.md`.

## Context Notes
- **SameSite=Lax** is now default in modern browsers — blocks most CSRF but not GET-based
- **Bearer token APIs** are NOT vulnerable to traditional CSRF (browser doesn't auto-send Authorization header)
- **Always check if removing the token still works** — many apps generate but don't validate
