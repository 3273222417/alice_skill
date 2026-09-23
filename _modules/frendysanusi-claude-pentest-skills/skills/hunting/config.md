# Hunting Skill: Configuration & Deployment

Covers: Security Headers, CORS Misconfiguration, TLS Issues, Information Disclosure, Default Credentials

## WSTG References

- WSTG-CONF-01: Network Infrastructure Configuration
- WSTG-CONF-02: Application Platform Configuration
- WSTG-CONF-03: File Extension Handling
- WSTG-CONF-04: Backup and Unreferenced Files
- WSTG-CONF-05: Enumerate Infrastructure and Application Admin Interfaces
- WSTG-CONF-06: HTTP Methods
- WSTG-CONF-07: HTTP Strict Transport Security
- WSTG-CONF-08: RIA Cross Domain Policy
- WSTG-CONF-09: File Permission
- WSTG-CONF-10: Subdomain Takeover
- WSTG-CONF-11: Cloud Storage

## Methodology

### Step 1: Security Headers Audit

Check response headers from the main page and key endpoints:

```bash
curl -sI https://target.com
```

| Header | Expected Value | Risk if Missing |
|--------|---------------|-----------------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | HTTPS downgrade attacks |
| `Content-Security-Policy` | Restrictive policy | XSS impact amplification |
| `X-Content-Type-Options` | `nosniff` | MIME-type sniffing attacks |
| `X-Frame-Options` | `DENY` or `SAMEORIGIN` | Clickjacking |
| `Referrer-Policy` | `strict-origin-when-cross-origin` or stricter | Information leakage via Referer |
| `Permissions-Policy` | Restrict sensitive features | Feature abuse |
| `X-XSS-Protection` | `0` (modern) or absent | Browser XSS auditor issues |

**Note:** Missing security headers alone are typically informational. Only report as a finding if you can demonstrate an exploit path.

### Step 2: CORS Testing

```bash
# Test with arbitrary origin:
curl -sI -H "Origin: https://evil.com" https://target.com/api/data

# Check response for:
# Access-Control-Allow-Origin: https://evil.com  → reflects any origin (CRITICAL)
# Access-Control-Allow-Origin: *                  → wildcard (check if credentials allowed)
# Access-Control-Allow-Credentials: true          → combined with reflection = critical
```

Test variations:
```
Origin: https://evil.com
Origin: https://target.com.evil.com          subdomain of evil
Origin: https://eviltarget.com               partial match
Origin: null                                  null origin (sandboxed iframe)
Origin: https://sub.target.com               legitimate subdomain
```

**Critical finding**: `Access-Control-Allow-Origin: <reflected>` + `Access-Control-Allow-Credentials: true` = any website can read authenticated API responses.

### Step 3: TLS Configuration

```bash
# Check TLS version and cipher suites:
nmap --script ssl-enum-ciphers -p 443 target.com

# Quick check:
echo | openssl s_client -connect target.com:443 -tls1 2>/dev/null  # TLS 1.0 (should fail)
echo | openssl s_client -connect target.com:443 -tls1_1 2>/dev/null # TLS 1.1 (should fail)
echo | openssl s_client -connect target.com:443 -tls1_2 2>/dev/null # TLS 1.2 (should work)
```

### Step 4: Information Disclosure

Check for exposed sensitive information:

```
# Version disclosure in headers
Server: Apache/2.4.41 (Ubuntu)
X-Powered-By: PHP/7.4.3

# Exposed configuration files (from recon)
/.env, /.git/config, /web.config, /phpinfo.php

# Stack traces in error responses
# Debug mode enabled (Django DEBUG=True, Express detailed errors)

# Source code disclosure
/.git/HEAD → if accessible, try git-dumper to extract full repo
```

### Step 5: HTTP Methods

```bash
# Check allowed methods:
curl -sI -X OPTIONS https://target.com/api/endpoint

# Test dangerous methods:
curl -sI -X TRACE https://target.com    # Should be disabled
curl -sI -X PUT https://target.com/test.txt -d "test"  # File creation?
curl -sI -X DELETE https://target.com/resource  # Unauthorized deletion?
```

### Step 6: Default Credentials

Check common admin interfaces found during recon:

```
admin:admin
admin:password
admin:123456
root:root
root:toor
test:test
administrator:administrator
```

### Step 7: CORS + Subdomain Takeover Check

If subdomains are in scope:
1. Check if any subdomains have dangling CNAME records → subdomain takeover
2. Check if CORS trusts *.target.com → if a subdomain can be taken over, it can be used for CORS bypass

### Step 8: Update Coverage

Mark WSTG-CONF-01 through WSTG-CONF-11 in `coverage.md`.
