# Backend Framework Coverage

The backend stages use conservative static heuristics. They are designed to create a review queue, not to declare exploitability.

## Framework and Route Families

- Node.js: Express, Fastify, Koa-like route calls, NestJS decorators, Next.js route handlers, Remix/tRPC/GraphQL dependency hints.
- Python: FastAPI, Flask, Django URL patterns, Pydantic/serializer validation signals.
- Java/Kotlin: Spring MVC annotations and Spring Security-style authorization hints.
- Go: Gin, Echo/Gorilla-style method routes, `http.HandleFunc`.
- Ruby: Rails/Sinatra route patterns.
- PHP: Laravel `Route::` patterns.
- .NET: minimal API `MapGet`/`MapPost` route patterns.

## Scope Control

JavaScript and TypeScript files are treated as backend candidates only when their path or content strongly suggests server code, such as:

- `server/`, `backend/`, `routes/`, `controllers/`, `middleware/`, `handlers/`, `functions/`, `lambda/`
- `pages/api/` and Next.js `app/**/route.ts`
- Server framework imports or decorators such as Express, Fastify, NestJS, NextRequest, or NextResponse

This avoids treating ordinary frontend API clients as server-side SSRF or route evidence.

## Output Files

- `state/backend_fingerprint.json`
- `state/server_route_map.json`
- `state/authz_map.json`
- `state/validation_coverage.json`
- `evidence/backend_fingerprint.md`
- `evidence/server_route_map.md`
- `evidence/authz_map.md`
- `evidence/validation_coverage.md`
