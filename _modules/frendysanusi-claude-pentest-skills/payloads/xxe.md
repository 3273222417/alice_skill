# XXE (XML External Entity) Payloads

## Overview
XXE occurs when an XML parser processes external entity declarations in user-supplied XML input, allowing file reading, SSRF, and potentially RCE.

## Methodology

### 1. Identify XML Input Points
- Endpoints accepting `Content-Type: application/xml` or `text/xml`
- SOAP services
- File upload accepting XML-based formats (SVG, DOCX, XLSX)
- Try changing `Content-Type: application/json` to `application/xml`

### 2. Detection Approach
1. **Internal entity**: Define and reference an entity — confirms XML parsing
2. **External entity (file read)**: Reference `file:///etc/passwd` — confirms XXE
3. **Blind XXE (OOB)**: External entity pointing to Burp Collaborator — confirms when response doesn't reflect

### 3. Exploitation Types

| Type | Use When | Technique |
|------|----------|-----------|
| **Classic XXE** | Response reflects entity value | `<!ENTITY xxe SYSTEM "file:///etc/passwd">` |
| **Blind XXE (OOB)** | Response doesn't reflect | Parameter entity + external DTD + HTTP callback |
| **Error-based XXE** | Errors are displayed | Force file-not-found error with file content in path |
| **XXE via file upload** | App accepts SVG/DOCX | Embed XXE in SVG or DOCX XML files |
| **XInclude** | Can't control full XML document | `<xi:include>` element |
| **PHP filter XXE** | PHP backend | `php://filter/convert.base64-encode/resource=...` |

### 4. Bypass Techniques
- SVG-based XXE for image upload endpoints
- SOAP body injection
- XInclude when you only control a fragment
- Nested parameter entities for blind exfiltration

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - XXE Injection](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/XXE%20Injection)

Key sections:
- [Classic XXE](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/XXE%20Injection/README.md#classic-xxe)
- [Blind XXE](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/XXE%20Injection/README.md#blind-xxe)
- [XXE in file uploads](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/XXE%20Injection/README.md#xxe-inside-svg)
- [XInclude](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/XXE%20Injection/README.md#xinclude-attacks)

For local curated payloads, see `local-payloads/xxe.md`.

## Context Notes
- **Modern parsers** disable external entities by default — XXE is becoming rarer but still found in Java and legacy apps
- **Billion Laughs DoS** — destructive, confirm with user before testing
- **File upload vectors**: SVG, DOCX (unzip and inject XXE into XML), XLSX
