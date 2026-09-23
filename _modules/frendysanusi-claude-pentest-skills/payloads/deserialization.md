# Insecure Deserialization Payloads

## Overview
Insecure deserialization occurs when an application deserializes untrusted data, allowing attackers to manipulate serialized objects to achieve RCE, privilege escalation, or data tampering.

## Methodology

### 1. Identify Serialized Data

| Language | Magic Bytes / Indicators | Common Locations |
|----------|------------------------|-----------------|
| Java | `AC ED 00 05` (hex) / `rO0AB` (base64) | Cookies, parameters, message queues |
| PHP | `O:4:"User":2:{...}` | Cookies, hidden form fields |
| Python | `\x80` (pickle protocol 2+) | Cookies, API parameters |
| .NET | `AAEAAAD/////` (base64) | ViewState, cookies |
| Ruby | `\x04\x08` (hex) | Sessions, API parameters |

Also check `Content-Type: application/x-java-serialized-object`.

### 2. Detection Approach
1. Look for base64-encoded blobs in cookies, parameters, or hidden fields
2. Decode and check for serialization magic bytes
3. For Java: Use URLDNS gadget (DNS-only, no dependencies) as safe detection
4. For PHP: Modify serialized object properties and observe behavior changes
5. For .NET: Check if `__VIEWSTATE` is MAC-protected

### 3. Exploitation by Language

| Language | Tool / Approach | Key Gadgets |
|----------|----------------|-------------|
| Java | ysoserial | CommonsCollections, Spring, Hibernate, Groovy |
| PHP | Manual / phpggc | `__wakeup()`, `__destruct()` abuse, `phar://` wrapper |
| Python | pickle payload | `__reduce__()` method calls `os.system()` |
| .NET | ysoserial.net | TypeConfuseDelegate, PSObject |
| Ruby | Marshal gadgets | ERB::Util chain |
| YAML | Unsafe load | Python `!!python/object/apply`, Ruby `!ruby/object` |

### 4. Safe Detection (Java)
The URLDNS gadget chain requires no library dependencies and only triggers a DNS lookup — no code execution. Use this for initial detection before escalating to RCE gadgets.

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - Insecure Deserialization](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Insecure%20Deserialization)

Key sections:
- [Java deserialization](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Insecure%20Deserialization/Java.md)
- [PHP object injection](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Insecure%20Deserialization/PHP.md)
- [Python pickle](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Insecure%20Deserialization/Python.md)
- [.NET deserialization](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Insecure%20Deserialization/DotNET.md)
- [YAML deserialization](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Insecure%20Deserialization/YAML.md)

For local curated payloads with full exploit code, see `local-payloads/deserialization.md`.

## Context Notes
- **Java deserialization** is the most common — look for base64 starting with `rO0AB`
- **Check ViewState** in ASP.NET — if not MAC-protected, it's a deserialization target
- **RCE payloads execute on the server** — confirm with user before testing
