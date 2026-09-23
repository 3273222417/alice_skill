# Path Traversal Payloads

## Overview
Path traversal occurs when user-controlled input is used to construct file paths without proper validation, allowing access to files outside the intended directory.

## Methodology

### 1. Identify File Path Parameters
Parameters named: `file=`, `path=`, `page=`, `template=`, `include=`, `doc=`, `download=`

### 2. Detection Approach
- Inject `../../../etc/passwd` (Linux) or `..\..\..\..\windows\win.ini` (Windows)
- Compare response with normal request — file content in response confirms vulnerability
- Try increasing traversal depth (3 to 8+ levels)

### 3. Target Files

| OS | High-Value Files |
|----|-----------------|
| Linux | `/etc/passwd`, `/etc/shadow`, `/proc/self/environ`, `~/.ssh/id_rsa`, `~/.bash_history` |
| Windows | `\windows\win.ini`, `\windows\repair\sam`, `\inetpub\wwwroot\web.config` |
| Application | `.env`, `config.php`, `wp-config.php`, `.git/config`, `application.properties` |

### 4. Bypass Techniques

| Technique | Use When |
|-----------|----------|
| URL encoding (`%2e%2e%2f`) | Basic `../` filter |
| Double encoding (`%252e%252e%252f`) | Server decodes twice |
| Overlong UTF-8 (`%c0%ae`) | Unicode normalization bypass |
| `..././` | Server strips `../` once (recursive bypass) |
| `..;/` | Tomcat/Java URL normalization |
| Null byte (`%00`) | PHP < 5.3.4 extension truncation |
| Slash flooding (`..//////..`) | Regex-based filters |

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - Directory Traversal](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Directory%20Traversal)

For local curated payloads, see `local-payloads/path-traversal.md`.

## Context Notes
- **LFI vs path traversal**: If the app includes/executes the file (PHP `include()`), it's Local File Inclusion with potential RCE
- **Null byte truncation** only works on PHP < 5.3.4 and older Java
- **Tomcat**: `..;/` bypass is specific to Tomcat's URL normalization
