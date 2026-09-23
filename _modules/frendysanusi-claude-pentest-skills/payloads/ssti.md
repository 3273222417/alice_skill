# SSTI (Server-Side Template Injection) Payloads

## Overview
SSTI occurs when user input is embedded into a server-side template engine and evaluated, potentially leading to remote code execution.

## Methodology

### 1. Detection
Inject mathematical expressions to see if the template engine evaluates them:

| Probe | Engine if Evaluated |
|-------|-------------------|
| `{{7*7}}` → `49` | Jinja2 or Twig |
| `{{7*'7'}}` → `7777777` | Jinja2 (Python string multiplication) |
| `{{7*'7'}}` → `49` | Twig (PHP arithmetic) |
| `${7*7}` → `49` | Freemarker, Velocity, Thymeleaf |
| `<%= 7*7 %>` → `49` | ERB (Ruby), EJS (Node.js) |
| `#{7*7}` → `49` | Pebble, Thymeleaf |
| `@(1+2)` → `3` | Razor (.NET) |

Universal polyglot for triggering errors: `${{<%[%'"}}%\.`

### 2. Engine Identification Decision Tree
1. Try `{{7*7}}` — if `49` appears, it's a `{{` engine (Jinja2, Twig, or similar)
2. Try `{{7*'7'}}` — `7777777` = Jinja2, `49` = Twig
3. If `{{` doesn't work, try `${7*7}` (Java engines), `<%= %>` (Ruby/Node), `#{` (Pebble)
4. Check error messages — they often reveal the engine name

### 3. Exploitation by Engine

| Engine | Language | RCE Approach |
|--------|----------|-------------|
| Jinja2 | Python (Flask) | MRO chain to access `os.popen()` via `__subclasses__()` |
| Twig | PHP (Symfony) | `filter('system')` on arrays |
| Freemarker | Java (Spring) | `Execute` utility class |
| Pebble | Java | `ScriptEngineManager` reflection |
| Mako | Python | Direct `os.system()` via module cache |
| ERB | Ruby | `<%= system() %>` or `File.open().read` |
| Spring EL | Java | `T(java.lang.Runtime).getRuntime().exec()` |

### 4. Bypass Techniques
- Hex/unicode escapes for blocked characters (`_`, `.`, `[`, `]`)
- `attr()` filter and `join` filter for string construction in Jinja2
- Character-by-character construction for Spring EL

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - SSTI](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Server%20Side%20Template%20Injection)

Key sections:
- [Detection](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Server%20Side%20Template%20Injection/README.md#detection)
- [Jinja2](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Server%20Side%20Template%20Injection/README.md#jinja2)
- [Twig](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Server%20Side%20Template%20Injection/README.md#twig)
- [Java engines](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Server%20Side%20Template%20Injection/README.md#java)
- [Intruder wordlist](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Server%20Side%20Template%20Injection/Intruders/ssti.fuzz)

For local curated payloads with full RCE chains, see `local-payloads/ssti.md`.

## Context Notes
- **SSTI often leads to RCE** — typically Critical severity
- **Check error messages** — they reveal the template engine name and version
- **Jinja2 sandbox escapes** change between Python versions — `__subclasses__()` indexes shift
