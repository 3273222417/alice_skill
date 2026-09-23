# HTTP Request Smuggling Payloads

## Overview
Request smuggling exploits disagreements between front-end and back-end servers about where one HTTP request ends and the next begins, using conflicting Content-Length and Transfer-Encoding headers.

## Methodology

### 1. Identify Architecture
Most common with reverse proxy + backend: Nginx/HAProxy/CloudFlare → Apache/Node.js

### 2. Detection Types

| Type | Front-End Uses | Back-End Uses | Detection Method |
|------|---------------|---------------|-----------------|
| CL.TE | Content-Length | Transfer-Encoding | Send conflicting headers, observe poisoned next request |
| TE.CL | Transfer-Encoding | Content-Length | Reverse of above |
| TE.TE | Transfer-Encoding | Transfer-Encoding | Obfuscate one TE header so only one server parses it |

### 3. Detection Approach
- **Timing-based**: Send ambiguous request — timeout indicates desync
- **Response-based**: Poison next request and observe unexpected error (405, different response)
- **Transfer-Encoding obfuscation**: Tab, space, capitalization, extra headers

### 4. Exploitation Scenarios
- Bypass front-end access controls
- Capture other users' requests
- Reflected XSS via request poisoning
- Cache poisoning

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - Request Smuggling](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/HTTP%20Request%20Smuggling)

For local curated payloads, see `local-payloads/request-smuggling.md`.

## Context Notes
- **High-risk testing** — can affect other users. Get explicit permission and test during low-traffic windows
- **Impact is typically Critical**: Cache poisoning, credential theft, bypassing all front-end security
- **Burp Suite** has a built-in HTTP Request Smuggler extension
- **HTTP/2** mitigates classic smuggling but introduces new variants
