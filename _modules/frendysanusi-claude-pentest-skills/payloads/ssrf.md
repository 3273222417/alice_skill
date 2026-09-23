# SSRF (Server-Side Request Forgery) Payloads

## Overview
SSRF occurs when an application fetches a URL or resource based on user-supplied input, allowing attackers to make the server send requests to internal/unintended destinations.

## Methodology

### 1. Identify URL Input Points
Parameters named: `url=`, `src=`, `href=`, `path=`, `dest=`, `redirect=`, `uri=`, `feed=`, `callback=`
Features: Webhooks, URL previews, PDF generation, image import, RSS feeds, file download by URL

### 2. Detection Approach
- **Basic**: Supply `http://127.0.0.1` or `http://localhost` and observe response
- **OOB (Blind)**: Use Burp Collaborator or similar callback service to confirm the server made the request
- **Timing**: Internal ports that are open respond faster than closed ones

### 3. Target Categories

| Target | Purpose | Key URLs |
|--------|---------|----------|
| Localhost | Access internal services | `http://127.0.0.1`, `http://[::1]`, `http://0.0.0.0` |
| Cloud metadata | Steal IAM credentials | AWS `169.254.169.254`, GCP `metadata.google.internal` |
| Internal network | Scan internal services | `http://10.x.x.x`, `http://172.16.x.x`, `http://192.168.x.x` |
| Protocol abuse | Read files, interact with services | `file://`, `gopher://`, `dict://` |

### 4. Bypass Techniques
- IP encoding: decimal, hex, octal representations of internal IPs
- URL parser confusion: `@` symbol, backslash, double encoding
- DNS rebinding: Domain that resolves to internal IP
- Redirect-based: Open redirect on allowed domain chains to internal target

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - SSRF](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Server%20Side%20Request%20Forgery)

Key sections:
- [Localhost bypass](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Server%20Side%20Request%20Forgery/README.md#bypassing-filters)
- [Cloud metadata](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Server%20Side%20Request%20Forgery/README.md#ssrf-url-for-cloud-instances)
- [Protocol smuggling](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Server%20Side%20Request%20Forgery/README.md#ssrf-exploiting-other-protocols)

For local curated payloads, see `local-payloads/ssrf.md`.

## Context Notes
- **Most impactful in cloud environments** — AWS/GCP/Azure metadata can leak IAM credentials
- **IMDSv2 (AWS)** requires a token — basic SSRF may be blocked on newer instances
- **GCP metadata** requires `Metadata-Flavor: Google` header
- **Blind SSRF**: Use OOB callbacks when responses aren't returned to you
