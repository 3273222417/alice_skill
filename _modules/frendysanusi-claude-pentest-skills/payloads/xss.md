# XSS (Cross-Site Scripting) Payloads

## Overview
XSS occurs when user-controlled input is reflected or stored in a web page without proper sanitization, allowing execution of arbitrary JavaScript in a victim's browser context.

## Methodology

### 1. Identify Reflection Context
Before selecting payloads, determine where user input appears in the response:
- **HTML body** — inject HTML tags
- **HTML attribute** — break out of attribute with `"` or `'`
- **JavaScript string** — break out of string and inject code
- **URL context** — use `javascript:` protocol
- **CSS context** — use `expression()` or `url()`

### 2. Detection Approach
- Inject a unique marker string (e.g., `xss123test`) and search for it in the response
- Identify which characters are filtered or encoded (`<`, `>`, `"`, `'`, `/`)
- Select payloads that match the reflection context and bypass observed filters

### 3. Payload Categories

| Category | Use When | Examples |
|----------|----------|---------|
| **Basic detection** | First test — confirm reflection | `<script>alert(1)</script>`, `<img src=x onerror=alert(1)>` |
| **Event handlers** | `<script>` is blocked | `<svg/onload=...>`, `<details/ontoggle=...>`, `<input autofocus onfocus=...>` |
| **Protocol handlers** | Input appears in `href` or `src` | `javascript:alert(1)`, `data:text/html,...` |
| **Encoding bypass** | WAF or filter blocks keywords | HTML entities, URL encoding, Unicode escapes, base conversion |
| **DOM-based** | Input consumed by JavaScript | Check `innerHTML`, `document.write`, `eval` sinks fed by `location.hash`, `document.referrer` sources |
| **Polyglots** | Unknown context | Multi-context payloads that work in HTML, attribute, and JS contexts |

### 4. Stored vs Reflected vs DOM
- **Reflected**: Input in request is reflected in immediate response
- **Stored**: Input is saved and rendered to other users later (higher impact)
- **DOM**: Input consumed client-side by JavaScript, never touches the server

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - XSS Injection](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/XSS%20Injection)

Key sections to reference:
- [Basic payloads](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/XSS%20Injection/README.md#exploit-code-or-poc)
- [Filter bypass](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/XSS%20Injection/README.md#filter-bypass-and-exotic-payloads)
- [CSP bypass](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/XSS%20Injection/README.md#csp-bypass)
- [Polyglots](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/XSS%20Injection/Intruders/polyglot.txt)

For local curated payloads with full exploit code, see `local-payloads/xss.md`.

## Context Notes
- **Check for CSP**: Content-Security-Policy blocking inline scripts requires bypass techniques
- **No CSP = easier XSS**: Payloads execute without restriction
- **Stored XSS > Reflected XSS** in severity — affects all users viewing the page
- **DOM XSS** requires JavaScript source code analysis, not just response inspection
