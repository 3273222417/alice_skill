# Source and Sink Pattern Reference

The dataflow stage is a proximity-based review aid. It records request-controlled source families near risky sink families so a reviewer can trace the path manually.

## Source Families

- `request_body`: body, JSON, form, POST data, `@RequestBody`
- `request_query`: query strings, path parameters, request params, `@RequestParam`, `@PathVariable`
- `headers_cookies`: headers, cookies, session cookies
- `file_upload`: upload middleware, multipart files, framework upload types
- `url_input`: callback, redirect, webhook, proxy, target, remote, or fetch URL fields

## Sink Families

- `sql_query`: raw SQL and query builders with raw query escape hatches
- `nosql_query`: document query and aggregation families
- `shell_command`: process execution and shell helpers
- `server_request`: outbound HTTP clients and fetchers
- `file_path`: filesystem reads, writes, streams, and path joins
- `redirect`: server-side redirect helpers
- `template_render`: raw template rendering or unsafe HTML helpers
- `deserialization`: native object deserialization helpers

## Severity Notes

High severity means the family deserves priority review. It does not mean the issue is exploitable without confirming actual data flow, validation, authorization, deployment context, and reachable route behavior.
