# File Upload Payloads

## Overview
File upload vulnerabilities occur when an application allows users to upload files without properly validating file type, content, and storage location, potentially leading to RCE, XSS, or other attacks.

## Methodology

### 1. Map Upload Functionality
- What file types are accepted?
- What is the maximum file size?
- Where are uploaded files stored? Are they accessible via web?
- Is the original filename preserved or renamed?

### 2. Test Categories

| Category | Technique | Goal |
|----------|-----------|------|
| **Extension bypass** | Double extension, null byte, case manipulation | Get server to execute uploaded file |
| **MIME type bypass** | Change Content-Type header to image type | Bypass content-type validation |
| **Magic bytes bypass** | Prepend file signature bytes to payload | Bypass file signature validation |
| **Content validation** | Polyglot files (valid image + code) | Pass both signature and extension checks |
| **Config overwrite** | Upload .htaccess, web.config, .pth | Change server behavior to execute custom extensions |
| **Filename injection** | SQLi, XSS, path traversal via filename | Exploit filename processing |

### 3. Extension Bypass Matrix

| Server | Extensions to Try |
|--------|------------------|
| PHP/Apache | `.php`, `.php3`, `.php5`, `.phtml`, `.phar`, `.pht`, `.inc` |
| ASP/IIS | `.asp`, `.aspx`, `.config`, `.cer`, `.asa` |
| JSP/Tomcat | `.jsp`, `.jspx`, `.jsw`, `.jspf` |

### 4. Bypass Techniques
- Double extension: `shell.jpg.php`
- Case manipulation: `shell.pHp`
- Trailing chars: `shell.php.`, `shell.php%20`, `shell.php%00.jpg`
- MIME spoofing: Set `Content-Type: image/gif` with code body
- Magic bytes: Prepend `GIF87a` or PNG/JPEG signature to code
- RTLO unicode: Visually disguise extension

### 5. Filename-Based Attacks
- Path traversal: `../../../etc/cron.d/backdoor`
- XSS: `"><img src=x onerror=alert(1)>.jpg`
- SQLi: `' OR 1=1--.jpg`

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - Upload Insecure Files](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Upload%20Insecure%20Files)

Key sections:
- [Extension bypass](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Upload%20Insecure%20Files/README.md#defaults-extensions)
- [Magic bytes](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Upload%20Insecure%20Files/README.md#magic-bytes)
- [Configuration overwrite](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Upload%20Insecure%20Files/README.md#configuration-files)
- [Picture metadata](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Upload%20Insecure%20Files/README.md#picture-metadata)

For local curated payloads with full exploit code, see `local-payloads/file-upload.md`.

## Context Notes
- **Check where files are stored**: If accessible via web root, RCE is likely possible
- **If filename is renamed to hash**: Extension tricks won't work — focus on content-based attacks
- **SVG uploads** can contain XSS payloads
- **DOCX/XLSX uploads** can contain XXE payloads (ZIP archives with XML inside)
