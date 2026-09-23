# Hunting Skill: Session Management

Covers: Session Fixation, Token Weakness, Cookie Security, Session Handling Flaws

## WSTG References

- WSTG-SESS-01: Session Management Schema
- WSTG-SESS-02: Cookie Attributes
- WSTG-SESS-03: Session Fixation
- WSTG-SESS-04: Exposed Session Variables
- WSTG-SESS-05: CSRF (covered in client-side.md)
- WSTG-SESS-06: Logout Functionality
- WSTG-SESS-07: Session Timeout
- WSTG-SESS-08: Session Puzzling
- WSTG-SESS-09: Session Hijacking

## Methodology

### Step 1: Cookie Attribute Audit

For each session cookie, check:

| Attribute | Secure Value | Finding if Missing |
|-----------|-------------|-------------------|
| `Secure` | Present | Cookie sent over HTTP — session hijacking via MitM |
| `HttpOnly` | Present | Cookie accessible to JavaScript — XSS can steal session |
| `SameSite` | `Strict` or `Lax` | Cross-site request forgery possible |
| `Path` | Specific (e.g., `/app`) | Cookie sent to unrelated paths |
| `Domain` | Specific | Cookie shared with subdomains that may be less secure |
| `Expires/Max-Age` | Reasonable duration | Persistent sessions increase hijacking window |

```bash
# Inspect cookies:
curl -sI https://target.com/login | grep -i set-cookie
```

### Step 2: Session Token Analysis

1. **Entropy check**: Collect 20+ session tokens, look for patterns
   - Are tokens sequential or predictable?
   - Do tokens contain encoded user data (base64 decode to check)?
   - Is the token length sufficient (128+ bits of entropy)?

2. **Token format**: Identify if it's a random hex string, UUID, JWT, or encoded object

3. **Token in URL**: Does the session ID appear in URLs? (leaks via Referer, logs, browser history)

### Step 3: Session Fixation Testing

1. **Get a session token** before authentication (visit the site anonymously)
2. **Authenticate** with that session
3. **Check if the token changed** after login
4. If token stays the same → Session fixation vulnerability

```bash
# Step 1: Get pre-auth token
curl -sI https://target.com/login | grep -i set-cookie

# Step 2: Authenticate with that token
curl -s -X POST https://target.com/login \
  -H "Cookie: session=PRE_AUTH_TOKEN" \
  -d "username=test&password=test"

# Step 3: Check if cookie changed in response
# If no new Set-Cookie → session fixation
```

### Step 4: Session Lifecycle Testing

1. **Logout completeness**: After logout, try using the old session token
   - If it still works → Session not invalidated on server side

2. **Session timeout**: Leave a session idle for 15-30 minutes, try using it
   - No timeout on sensitive applications is a finding

3. **Concurrent sessions**: Log in from two browsers simultaneously
   - Does the first session get invalidated? (depends on application requirements)

4. **Session after password change**: After changing password, are other sessions invalidated?

### Step 5: Session Token Handling

1. **Token in GET parameters**: Check if session ID appears in URLs
2. **Token in hidden form fields**: Check if passed via POST
3. **Token via Referer**: If token is in URL, check if external resources on the page leak it
4. **Cross-subdomain leakage**: If cookie domain is too broad, check if less-secure subdomains can access it

### Step 6: Update Coverage

Mark WSTG-SESS-01 through WSTG-SESS-09 in `coverage.md`.
