# Hunting Skill: Client-Side Vulnerabilities

Covers: XSS (Reflected, Stored, DOM), CSRF, Open Redirect

## Sub-Class Resolution

| Sub-Class | Payload File | WSTG Reference |
|-----------|-------------|----------------|
| `xss` | `payloads/xss.md` | WSTG-INPV-01, WSTG-INPV-02, WSTG-CLNT-01 |
| `csrf` | `payloads/csrf.md` | WSTG-SESS-05 |
| `open-redirect` | `payloads/open-redirect.md` | WSTG-CLNT-04 |

## Methodology

### Step 1: Map Client-Side Attack Surface

From recon data, identify:
- **All reflected input**: Search bars, error messages, URL parameters echoed in page
- **Stored input**: Comments, profile fields, messages, forum posts
- **DOM manipulation**: JavaScript reading from `location.hash`, `document.referrer`, `postMessage`
- **State-changing forms**: Any POST/PUT/DELETE without anti-CSRF tokens
- **Redirect parameters**: `?url=`, `?next=`, `?return=`, `?redirect=`

### Step 2: XSS Testing

#### 2a: Reflected XSS
1. **Identify reflection points**: Inject a unique string (e.g., `aaa123bbb`) and search for it in the response
2. **Determine the context**: Is the reflection in HTML body, HTML attribute, JavaScript string, URL, or CSS?
3. **Select context-appropriate payloads** from `payloads/xss.md`:
   - HTML body: `<script>alert(1)</script>`, `<img src=x onerror=alert(1)>`
   - HTML attribute: `" onfocus=alert(1) autofocus="`
   - JavaScript string: `'; alert(1);//`, `</script><script>alert(1)</script>`
   - URL context: `javascript:alert(1)`
4. **If filtered/encoded**: Check what's being filtered and use bypass payloads (encoding, tag mutation, event handler alternatives)
5. **Log every payload** to `payload-log.md`

#### 2b: Stored XSS
1. **Identify all user-stored content**: Profile name/bio, comments, messages, file names, metadata
2. **Inject detection payloads** into each field
3. **Navigate to where the content is displayed** (other user's view, admin panel, email)
4. **Check if the payload executes** in the display context

#### 2c: DOM XSS
1. **Analyze JavaScript files** for dangerous patterns:
   - Sources: `location.hash`, `location.search`, `document.referrer`, `window.name`, `postMessage`
   - Sinks: `innerHTML`, `document.write`, `eval`, `setTimeout`, `setInterval`, `$.html()`
2. **Trace data flow** from source to sink
3. **Craft payload** that travels through the identified flow

### Step 3: CSRF Testing

1. **Identify state-changing requests**: Change password, change email, transfer funds, create/delete content
2. **Check for CSRF protections**:
   - Anti-CSRF token in form/header? → Try removing it, check if still accepted
   - SameSite cookie attribute? → Lax blocks POST cross-site, but allows GET
   - Referer/Origin validation? → Try `<meta name="referrer" content="no-referrer">`
3. **Build PoC HTML** from `payloads/csrf.md` templates
4. **Test the PoC**: Open in a different browser/session where victim is logged in
5. **For JSON APIs**: Try `enctype="text/plain"` trick or check if Content-Type is validated

### Step 4: Open Redirect Testing

1. **Find redirect parameters**: Check login, logout, callback, and return URLs
2. **Test basic payloads**: `?next=https://evil.com`, `?return=//evil.com`
3. **If blocked, try bypass payloads** from `payloads/open-redirect.md`: encoding, @ symbol, backslash, protocol-relative
4. **Demonstrate impact**: Chain with OAuth token theft or phishing scenario

### Step 5: Update Coverage

Mark WSTG categories:
- WSTG-INPV-01 (Reflected XSS)
- WSTG-INPV-02 (Stored XSS)
- WSTG-CLNT-01 (DOM XSS)
- WSTG-SESS-05 (CSRF)
- WSTG-CLNT-04 (Open Redirect)
