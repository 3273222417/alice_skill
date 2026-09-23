# Open Redirect Payloads

## Overview
Open redirect occurs when an application redirects users to a URL specified in user-controlled input without proper validation, enabling phishing and OAuth token theft.

## Methodology

### 1. Find Redirect Parameters
Common names: `url`, `redirect`, `redirect_uri`, `next`, `return`, `returnTo`, `dest`, `continue`, `go`, `callback`, `target`, `forward`

Common locations: Login/logout flows, OAuth callbacks, email links

### 2. Test Patterns

| Technique | Example |
|-----------|---------|
| Direct URL | `?next=https://evil.com` |
| Protocol-relative | `?next=//evil.com` |
| Backslash | `?next=\/evil.com` |
| URL encoding | `?next=%2f%2fevil.com` |
| `@` symbol | `?next=https://trusted.com@evil.com` |
| Fragment | `?next=https://evil.com#trusted.com` |
| Subdomain | `?next=https://trusted.com.evil.com` |

### 3. Impact Chains
Open redirect alone is typically low severity, but chains with:
- **OAuth token theft**: Redirect authorization code to attacker server
- **Phishing**: Redirect from trusted domain to phishing page
- **SSRF bypass**: Redirect from allowed domain to internal IP

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - Open Redirect](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Open%20Redirect)

For local curated payloads, see `local-payloads/open-redirect.md`.

## Context Notes
- **Demonstrate the chain** in reports — standalone open redirect may be informational
- **Test both server-side (301/302) and client-side (JavaScript) redirects**
