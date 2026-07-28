# 2. JWT auth for single-user web deployment

**Date**: 2026-07-28

**Status**: Accepted

## Context

The app was originally designed as a local single-user tool with no
authentication (per the original spec).  We are now deploying it on a
web-accessible server, so we need to prevent unauthorized access.

Constraints:
- Single user — no multi-account, no registration, no roles.
- No database — data lives in flat `.md` files.
- Stateless backend — no server-side sessions.
- Must work with the existing vanilla-JS SPA frontend with minimal
  changes to the API shape.

## Decision

Use a **single shared password** verified at login, returning a
**signed JWT** that the client sends as a `Bearer` token on subsequent
requests.

- Password is hashed with **bcrypt** via `passlib`; never stored in
  plain text.
- JWT is signed with **HMAC-SHA256** (`HS256`).  The secret key comes
  from `APP_SECRET` env var or is randomly generated on first run.
- Token expires in **7 days**; the frontend stores it in
  `sessionStorage` (cleared on tab close).
- All `/api/*` routes (except `/api/auth/login`) are protected by a
  `Depends(require_auth)` dependency that validates the token on every
  request.
- Login endpoint accepts `POST /api/auth/login` with
  `{"password": "..."}` and returns `{"access_token": "...",
  "token_type": "bearer"}`.

### Why not alternatives

| Option | Rejected because |
|--------|------------------|
| HTTP Basic Auth | Credentials sent on every request; harder to revoke; no expiry. |
| Session cookie | Requires server-side state or a DB; we are stateless. |
| OAuth2 / OIDC | Overkill for a single user; adds external dependency. |
| API key | Same as password-in-header problem; no scoping needed. |
| mTLS | Operational complexity; no benefit for a single user. |

## Consequences

- Login screen added to the SPA; all API calls now include
  `Authorization: Bearer <token>`.
- Existing integration tests needed a `dependency_overrides` entry to
  bypass auth.
- The `.env` file must contain `APP_PASSWORD` (or a random one is
  printed at startup — okay for dev, not for production).
- Security headers (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`) were added as a middleware.
- CORS is locked down (no origins allowed) since frontend and backend
  are served from the same origin.
