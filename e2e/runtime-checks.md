# E runtime verification (in progress)

All evidence is local and synthetic. No source license, production account, model,
Feishu recipient, actual phone receipt or deployed server has been accepted.

## Verified checkpoint, 2026-09-11 UTC

- Dependencies: reviewed C `571a4af958754899c3cf8903d52075e9b8a616ff`,
  AB `f3b726d1a194f192f7fc4dc5908882190b416b96`,
  D `38a065e1a3f71631e4a8af915069982fe02303e6`.
- Windows Python 3.13.13, uv 0.11.26, actual PostgreSQL 16.14 (Alpine Docker).
- `uv run --locked pytest tests/integration -q --tb=short`: **60 passed**, one
  upstream Starlette/AnyIO deprecation warning, 19.10 seconds. The explicitly
  injected `OIL_E_TEST_DATABASE_URL` targets only E loopback 55434 / `oil_e_test`.
  Each PostgreSQL case applies real Alembic migrations in a unique test schema.
- `uv run --locked ruff check tests/integration fixtures/runtime_factory.py deploy/worker_health.py`:
  PASS. No SQLite or dependency-overridden API authorization used.
- `npm test` in `web`: **11 passed**. Linux web image independently ran locked
  install, authoritative schema check, TypeScript check and Vite build: PASS.
- Actual Procrastinate normal/report worker blocked by a synthetic channel while
  urgent/event worker completed both recipient dry-runs: PASS.
- Signed callback receiver tests use explicit synthetic accepted-message input
  rows; these are **not** proof of a sender, provider acceptance or phone receipt.

## Regressions found and returned to owners

1. T04: independent publisher evidence arriving in a second committed batch left
   the event at `credible_single_source`. Preserved assertion failed on C
   `88338fa`; reviewed C `16d064e` adds bounded family history/fences. Original E
   regression now passes with `independent_multi_source`, same event, revision 2.
2. T09/T05: stable record ID plus multiple revisions conflicted with AB's
   record-only replay uniqueness. Reviewed AB `f3b726d` fixes composite identity.
   E continuous append-only ReplaySource/checkpoint tests now pass unchanged.
3. T14: report delivery shared the urgent task/outbox. Reviewed C `ffb62d` separates
   subject claims and normal delivery; E tested real independent queue workers.
4. Real browser: D advertises 5 MiB versus C raw upload limit 2,000,000 bytes.
   Returned to D; pending reviewed fix and rerun.
5. Real browser: default `field_mapping={}` is advertised as standard columns but
   AB requires `value`/`as_of` mappings; actual POST returns 422. Six prior browser
   flows passed, quote preview failed. Returned to coordinator; no response mocks
   or hidden field-map substitution used to pass this workflow.

## Runtime status at this checkpoint

Both Linux images built. Existing E PostgreSQL container/volume retained. E-created
API, ingest, urgent, normal and gateway started; API and all worker heartbeat
checks passed. The API image currently contains C `16d064e`, so final-image
replay is pending. Coordinator explicitly authorized replacement of only our six
stateless E containers, preserving PostgreSQL, volumes, networks and other projects.

Backup/isolated restore, final candidate browser rerun and final runtime matrix
remain in progress. Linux CI is authored; remote execution is not yet established.
External source/identity/phone gates, >=7-day comparison and >=14-day operation are
**BLOCKED_EXTERNAL / NOT EXECUTED**.
