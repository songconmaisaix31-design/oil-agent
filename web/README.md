# Oil Agent mobile web

React/Vite Chinese mobile UI. The application contains no seeded market data,
fixture login, local access tokens or API DTO copies. `src/generated/api.d.ts`
comes directly from C's authoritative `src/oil_agent/contracts/openapi.json`.
Fixture payloads live only under `src/test` and the standalone browser check.

## Local commands

Use Node 24 and the committed npm lockfile, from `web/`:

```text
npm ci
npm run generate
npm run generate:check
npm run typecheck
npm test
npm run build
npm run dev
```

The dev server binds only `127.0.0.1:5174` with strict port selection; check that
the port is free first. API calls use `/api/v1` on the same origin, including the
HttpOnly session cookie. A production reverse proxy must serve the built UI and
route `/api/v1` to C's FastAPI application. No proxy destination or credential is
guessed here. Without a backend at this origin, the UI reports unavailable service.

The server produces the configured Feishu authorization URL. OAuth returns to a
registered HTTPS application URL; the SPA strips code/state from browser history
before exchanging them via `POST /api/v1/session`. C owns the one-time browser
binding, preprovisioned users, revocation, HttpOnly cookies and CSRF validation.
Only the CSRF value is kept in page memory. No localStorage/sessionStorage is used.

## Views

- Home: urgent event ordering, fact/evidence status, daily report, cutoff and health.
- Detail: explicit historical revisions, origin groups, source record links,
  current-version delivery acknowledgement and useful/irrelevant/error feedback.
- Reports: paginated history, source-linked facts, metrics as decimal strings,
  formula, impact analysis and gaps. No fabricated zero price change.
- Quotes: administrator-only bounded file upload, rights reference, server preview,
  row issues, duplicate rows, exact preview import and like-for-like dimension check.
- Configuration: administrator-only editing, visible health for authenticated users,
  source timing and gaps. Production/reminder/SMS/phone switches are informational.

Loading, empty, error, fixture, expired-preview, unauthenticated and role-denied
states are explicit. A successful button requires a successful API response.

## Browser check

With the dev server running on the reserved port and Chrome installed:

```text
npm run browser:check
```

This launches an isolated **headless Chrome** process through Playwright's pipe,
intercepts `/api/**` with labeled synthetic fixtures and closes the browser after
the check. It does not use the signed-in Chrome profile, call Feishu or connect to
PostgreSQL. Results and screenshots go to ignored `.browser-artifacts/`.

Verified on 2026-09-12: six checks at 390x844 and 320x740, no page exceptions,
no horizontal overflow, fixture labels, unconfigured login, rejected ack feedback,
report empty state and role-restricted configuration/import.

## Remaining external gates

Real Feishu SSO, application-bot acceptance, callback registration, recipient phone
receipt, logout/revocation across real devices and background/locked/offline phone
behavior remain **BLOCKED_EXTERNAL**. Cross-track PostgreSQL/API integration is
owned by C/E/I and is not proven by these mocked UI checks. This branch performs
no production deployment, commercial requests, customer sends or secret discovery.
