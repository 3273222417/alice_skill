# Hunting Skill: Authentication & Access Control

Covers: IDOR, Broken Access Control, Authentication Bypass, JWT Attacks, OAuth Flaws, Privilege Escalation

## Sub-Class Resolution

| Sub-Class | Payload File | WSTG Reference |
|-----------|-------------|----------------|
| `idor` | `payloads/idor.md` | WSTG-ATHZ-04 |
| `jwt` | `payloads/jwt.md` | WSTG-ATHN-09 |
| `oauth` | `payloads/oauth.md` | WSTG-ATHN-10 |

## Methodology

### Step 1: Map Authentication & Authorization Model

From recon data, identify:
- **Auth mechanism**: Session cookie, JWT, API key, OAuth, Basic Auth
- **User roles**: Anonymous, regular user, admin, API consumer
- **Access control model**: Role-based, resource-based, attribute-based
- **Object references**: IDs in URLs, API parameters, request bodies

### Step 2: IDOR Testing

**Requires at least 2 test accounts** (or 1 account + knowledge of another user's IDs).

1. **Identify all endpoints with object references** (user IDs, document IDs, order IDs)
2. **For each endpoint**: Change the object ID to another user's
3. **Test all HTTP methods**: GET (read), POST (create), PUT/PATCH (modify), DELETE (remove)
4. **Check both horizontal** (same role, different user) **and vertical** (lower role accessing higher role's resources)
5. **Log every attempt** to `payload-log.md`

Key patterns from `payloads/idor.md`:
- Sequential ID manipulation
- UUID harvesting from API responses
- Parameter pollution (HPP)
- HTTP method switching
- Body parameter IDOR
- GraphQL IDOR via node queries
- Encoded/hashed ID manipulation

### Step 3: Authentication Testing

1. **Default credentials**: Check admin panels, API documentation pages
2. **Login bypass**: Test SQL injection in login form (see `payloads/sqli.md` auth bypass section)
3. **Account enumeration**: Compare responses for valid vs invalid usernames
4. **Password reset flaws**: Token predictability, token reuse, host header injection
5. **Brute-force protection**: Is there rate limiting? Account lockout?

### Step 4: JWT Testing (if JWT is used)

From `payloads/jwt.md`:
1. **Decode the JWT** — understand the claims structure
2. **Test algorithm none**: Set `"alg":"none"`, remove signature
3. **Test algorithm confusion**: RS256 → HS256 with public key
4. **Test KID injection**: Path traversal, SQLi in kid parameter
5. **Test claim manipulation**: Change user ID, role, permissions
6. **Test weak secret**: Brute-force HMAC key with common wordlists

### Step 5: OAuth Testing (if OAuth is used)

From `payloads/oauth.md`:
1. **Map OAuth endpoints**: Fetch `.well-known/openid-configuration`
2. **Test redirect_uri manipulation**: Subdomain, path traversal, encoding tricks
3. **Test state parameter**: Remove it, reuse old values
4. **Test scope escalation**: Add admin/write scopes
5. **Test PKCE enforcement**: Remove code_challenge parameters
6. **Test token leakage**: Check Referer headers from callback page

### Step 6: Privilege Escalation

1. **Forced browsing**: Access admin endpoints as regular user
2. **Parameter tampering**: Add `role=admin` or `is_admin=true` to requests
3. **HTTP method override**: `X-HTTP-Method-Override: PUT` on restricted endpoints
4. **Mass assignment**: Send extra fields in POST/PUT that shouldn't be user-controllable

### Step 7: Update Coverage

Mark these WSTG categories:
- WSTG-ATHN-01 to 10 (Authentication)
- WSTG-ATHZ-01 to 04 (Authorization)
- WSTG-IDNT-01 to 05 (Identity Management)
