# Hunting Skill: Server-Side Vulnerabilities

Covers: SSRF, Path Traversal, File Upload, Insecure Deserialization, HTTP Request Smuggling

## Sub-Class Resolution

| Sub-Class | Payload File | WSTG Reference |
|-----------|-------------|----------------|
| `ssrf` | `payloads/ssrf.md` | WSTG-INPV-19 |
| `path-traversal` | `payloads/path-traversal.md` | WSTG-INPV-09 |
| `file-upload` | `payloads/file-upload.md` | WSTG-INPV-12 |
| `deserialization` | `payloads/deserialization.md` | WSTG-INPV-16 |
| `request-smuggling` | `payloads/request-smuggling.md` | WSTG-INPV-15 |

## Methodology

### Step 1: Identify Server-Side Attack Surface

From recon data, prioritize:
- **URL-fetching features**: Webhooks, URL previews, PDF generation, image import, RSS feeds → SSRF
- **File path parameters**: Download endpoints, include parameters, template selection → Path Traversal
- **File upload forms**: Profile pictures, document uploads, import features → File Upload
- **Serialized data**: Base64 blobs in cookies/parameters, `Content-Type: application/x-java-serialized-object` → Deserialization
- **Reverse proxy + backend architecture**: Multiple servers processing requests → Request Smuggling

### Step 2: SSRF Testing

1. **Identify URL input parameters**: `url=`, `src=`, `href=`, `path=`, `dest=`, `redirect=`, `uri=`, `feed=`
2. **Test internal access**: `http://127.0.0.1`, `http://localhost`, `http://[::1]`
3. **Test cloud metadata**: `http://169.254.169.254/latest/meta-data/` (AWS)
4. **If blocked, try bypass payloads**: IP encoding tricks (decimal, hex, octal), URL parser confusion, DNS rebinding
5. **For blind SSRF**: Use Burp Collaborator or similar OOB callback
6. **Test protocol handlers**: `file://`, `gopher://`, `dict://`

### Step 3: Path Traversal Testing

1. **Identify file path parameters**: `file=`, `path=`, `page=`, `template=`, `include=`, `doc=`
2. **Test basic traversal**: `../../../etc/passwd` (Linux), `..\..\..\..\windows\win.ini` (Windows)
3. **Test encoding bypasses**: URL encoding, double encoding, overlong UTF-8
4. **Test null byte truncation**: `../../../etc/passwd%00.jpg` (old PHP)
5. **Check for LFI**: If the app includes/executes the file, it's more severe than just reading

### Step 4: File Upload Testing

1. **Map upload functionality**: What types accepted? Size limits? Where stored?
2. **Test extension bypass**: Double extension, null byte, case manipulation
3. **Test MIME type bypass**: Change Content-Type header to image type
4. **Test magic byte bypass**: Prepend GIF87a to PHP code (polyglot)
5. **Test .htaccess upload**: If Apache, upload .htaccess to enable PHP execution on custom extensions
6. **Check stored location**: Can you access the uploaded file via web? If yes, test webshell execution
7. **Test filename injection**: SQLi, XSS, path traversal via filename

### Step 5: Deserialization Testing

1. **Identify serialized data**: Look for base64 blobs, magic bytes (rO0AB for Java, O: for PHP)
2. **Test Java deserialization**: Use ysoserial URLDNS gadget for safe detection (DNS-only)
3. **Test PHP object injection**: Modify serialized object properties
4. **Test Python pickle**: If base64-encoded data in cookies/parameters on a Python app
5. **Check .NET ViewState**: Is `__VIEWSTATE` MAC-protected? If not, it's a deserialization target

### Step 6: Request Smuggling Testing

**Caution: Can affect other users. Get explicit permission.**

1. **Identify proxy architecture**: Reverse proxy (Nginx, HAProxy, CloudFlare) + backend server
2. **Test CL.TE**: Send conflicting Content-Length and Transfer-Encoding headers
3. **Test TE.CL**: Reverse of above
4. **Use timing-based detection**: Observe timeouts vs immediate responses
5. **Test Transfer-Encoding obfuscation**: Tab, space, capitalization variants

### Step 7: Update Coverage

Mark WSTG categories tested in `coverage.md`.
