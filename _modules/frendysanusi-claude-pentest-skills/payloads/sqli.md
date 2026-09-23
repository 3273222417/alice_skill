# SQL Injection Payloads

## Overview
SQL injection occurs when user-controlled input is incorporated into SQL queries without proper parameterization, allowing attackers to manipulate database queries.

## Methodology

### 1. Identify Injection Points
- URL parameters used in search, filter, sort, ID lookups
- POST body parameters (login forms, registration, comments)
- HTTP headers (Cookie, Referer, X-Forwarded-For)
- JSON/XML API body parameters

### 2. Detection Approach
- **Error-based**: Inject `'` or `"` and look for database error messages (SQLITE_ERROR, MySQL syntax error, PG error)
- **Boolean-based**: Compare responses for `' AND 1=1--` (true) vs `' AND 1=2--` (false)
- **Time-based**: Inject `' AND SLEEP(5)--` and measure response delay (>5s = vulnerable)
- **UNION-based**: `' UNION SELECT NULL,NULL,...--` to extract data directly

### 3. Database Fingerprinting

| DBMS | Detection | Comment Syntax |
|------|-----------|---------------|
| MySQL | `connection_id()`, `@@version` | `-- -`, `#` |
| PostgreSQL | `pg_client_encoding()`, `::int` cast | `--` |
| MSSQL | `@@CONNECTIONS`, `BINARY_CHECKSUM()` | `--` |
| SQLite | `sqlite_version()`, `last_insert_rowid()` | `--` |

### 4. Exploitation Progression
1. Confirm injection exists (error or behavioral difference)
2. Determine column count (`ORDER BY N` or `UNION SELECT NULL,...`)
3. Extract database version and schema
4. Extract target data (users, credentials, etc.)
5. Delegate to `sqlmap` for automated extraction after manual confirmation

### 5. Auth Bypass
Test login forms with tautology payloads in the email/username field:
- `' OR '1'='1'--`
- `admin'--`
- `' OR 1=1#`

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - SQL Injection](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/SQL%20Injection)

Key sections:
- [Entry point detection](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/README.md#entry-point-detection)
- [DBMS identification](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/README.md#dbms-identification)
- [Authentication bypass](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/README.md#authentication-bypass)
- [UNION-based](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/README.md#union-based-injection)
- [WAF bypass](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/README.md#waf-bypass)
- DB-specific: [MySQL](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/MySQL%20Injection.md), [PostgreSQL](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/PostgreSQL%20Injection.md), [MSSQL](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/MSSQL%20Injection.md), [SQLite](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/SQLite%20Injection.md)

For local curated payloads, see `local-payloads/sqli.md`.

## Context Notes
- **Always URL-encode** payloads when injecting via HTTP parameters
- **Time-based blind**: Use delays of 5+ seconds to distinguish from network latency
- **After manual confirmation**, delegate to `sqlmap`: `sqlmap -u "<url>" --batch --level=3 --risk=2`
