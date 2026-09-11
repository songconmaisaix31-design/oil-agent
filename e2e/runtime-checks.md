# E runtime verification

All evidence is local and synthetic. No source license, production account, model,
Feishu recipient, actual phone receipt or deployed server has been accepted.

## Verified checkpoint, 2026-09-11 UTC

- Dependencies: reviewed C `41a00ded1f949aee8099b549d5d419f0487dd0f9`,
  AB `026490a4558ffc50dba03a28c14b2e03dcfa32e9`,
  D `0bbdc217b43aec94e66ead9863a734f7902d20f2`.
- Windows Python 3.13.13, uv 0.11.26, Node 24.16.0, actual PostgreSQL 16.14
  (Alpine Docker), Docker Engine 29.5.3 / Compose 5.1.4. Linux app Python 3.13.15.
- `uv run --locked pytest tests/integration -q --tb=short --junitxml=e2e/runtime-artifacts/local-integration.xml`:
  **69 passed** (31 PostgreSQL cases, 38 local cases), one upstream Starlette/AnyIO
  deprecation warning, 24.40 seconds, no skips. The explicitly
  injected `OIL_E_TEST_DATABASE_URL` targets only E loopback 55434 / `oil_e_test`.
  Each PostgreSQL case applies real Alembic migrations in a unique test schema.
- `uv run --locked ruff check tests/integration fixtures/runtime_factory.py deploy/worker_health.py`:
  PASS. No SQLite or dependency-overridden API authorization used.
- `uv run --locked pytest tests/contracts tests/unit -m 'not postgres' -q --tb=short`:
  **167 passed, 28 deselected** in 1.93 seconds. Those C PostgreSQL tests require
  C's exact scope; they are run in their own fresh remote CI service, not E's local DB.
- `npm test` initially passed 11 tests locally; the final D cap revision adds two
  tests. Remote CI passed all **13 frontend tests**. Final Linux web image ran
  locked install, authoritative schema check, TypeScript check and Vite build: PASS.
- Actual Procrastinate normal/report worker blocked by a synthetic channel while
  urgent/event worker completed both recipient dry-runs: PASS.
- Signed callback receiver tests use explicit synthetic accepted-message input
  rows; these are **not** proof of a sender, provider acceptance or phone receipt.
- Three further cases connect the actual D FeishuChannel to C's recipient authorizer
  and an in-memory HTTP transport: synthetic accepted response, lost response and
  revocation during token acquisition. No real request leaves the test.
- `node e2e/browser-runtime.mjs`: **8 passed**, no page errors, actual Linux gateway,
  API and PostgreSQL with original synthetic data; no local API response mocks.
  Initial run created an actual API acknowledgement; reruns observe that persisted
  acknowledgement and submit feedback. Real OAuth and phones NOT EXECUTED.
- `uv run --locked python e2e/gateway-upload.py`: **1,976,096 raw bytes -> 200**;
  **2,000,001 raw bytes -> 422**, actual gateway/API with no-store responses.
- Corpus consistency, Ruff check/format, shell syntax, Node syntax and Compose
  configuration validation passed; these are separate from application execution.

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
4. Real browser: D advertised 5 MiB versus C raw upload limit 2,000,000 bytes.
   Reviewed D `0bbdc217` aligns both preflights and UI; final browser/limit checks pass.
5. Real browser: default `field_mapping={}` is advertised as standard columns but
   AB requires `value`/`as_of` mappings; actual POST returns 422. Six prior browser
   flows passed, quote preview failed. Reviewed AB `026490a` supports exact present
   canonical headers. Original default-user-flow browser now passes without response
   mocks or hidden field-map substitution.

## Linux runtime and restore

Both final Linux images built serially from the reviewed dependencies above:

- `oil-agent-app:e-final`: `sha256:5bfd3691acbfaf4a8985f8eb5e4dd1a0e76496a05f12d07a5df85dfcd1f1765f`.
- `oil-agent-web:e-final`: `sha256:98b807f133d7e3400cf3583ec3472446e2bc10e0be944003a67bbb7a1f02425b`.

API/init/ingest/urgent/normal share the same app image. All live health checks passed
including persisted queue tick heartbeats; init exited 0 after migrate/queue-schema/
recover. Actual `docker restart --timeout 20 oil-agent-e-urgent-1` succeeded on the
final image, and the API remained ready (200). This is graceful Linux restart,
not a SIGKILL-at-every-transaction-boundary claim.

Coordinator authorized replacement only of six E-created stateless containers.
Their exact before/after identities and mount scope are retained in
[before](runtime-artifacts/containers-before.txt) and
[after](runtime-artifacts/containers-after.txt). PostgreSQL container ID
`b3c3a345428590922eb8e628a996dd634cb3333e5f0c86f588eede8fb7101cab` and volume
`oil-agent-e_postgres-data` remained unchanged. No unrelated containers or volumes
were changed. No Compose down, prune or volume removal was used.

The actual backup and isolated restore scripts both exited 0. Source snapshot and
restored database each contained **1 source record, 2 versions and 1 acknowledgement**
(before later browser quote imports). Repeating with the same backup/target failed
with exit 1 without overwrite. In `oil_e_restore_20260912` only, an explicitly seeded
expired in-flight lease was recovered by the actual CLI to UNKNOWN; the result was
`deliveries_unknown=1`, `records_recovered=0`, `reminders_created=0`, and final states
3 dry_run / 1 unknown. No restored worker was started and no item was resent.

The public browser evidence is [results](runtime-artifacts/browser-results.json),
[home](runtime-artifacts/home-390.png), [event](runtime-artifacts/event-390.png), and
[quotes](runtime-artifacts/quotes-390.png). Images contain synthetic content only.
Session and dump files remain outside Git; private path references were handed to
the coordinator separately. There is no reusable private environment/DSN file.

At handoff, all seven E containers are **stopped and retained**, exit code 0,
OOM=false: [final states](runtime-artifacts/containers-final-state.txt). E's
PostgreSQL volume, the isolated restored database and the named networks remain.
Only E services were stopped, after API/workers/gateway shutdown completed.

## CI and limits

The workflow provisions independent fresh C (55431 / oil_c_test) and E
(5432 / oil_e_ci) PostgreSQL services, preserves their exact existing allowlists,
migrates C, supplies the accepted AB package path, and runs full core and E suites
without deselection. It also runs locked frontend checks and serial Linux builds.
[Run 34638262292](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34638262292)
on **`3bafd0ba63cbd62fd2c904d70633fbf1c5720ec4` completed SUCCESS**:

| Remote Linux check | Actual result |
| --- | --- |
| Full `tests/contracts tests/unit` with C PostgreSQL and AB package | 195 passed, 0 skipped, 18.93 seconds |
| E `tests/integration` with separate E PostgreSQL | 69 passed, 0 skipped, 19.15 seconds |
| Frontend tests | 13 passed |
| Frontend generated-schema/TypeScript/Vite build | PASS |
| Both Linux image builds | PASS |
| Shell syntax / corpus / Ruff | PASS |

The previous narrower run was superseded/cancelled, not reported as completed
PASS. The subsequent E evidence commit includes this report, settled screenshots
and browser capture synchronization; any new run it triggers is distinct from
the successful code/CI SHA above. I must verify the final integrated HEAD.

E code increments are `5047d8b` (deployment scaffolding), `4730819` (corpus replay),
`368a511` (PostgreSQL/callback/queue acceptance), `c48bea1` (Linux/runtime/CI), and
`3bafd0b` (complete C+E CI scopes). The final handoff SHA is supplied through the
Orca completion message; this document does not use a self-referential commit ID.

External source/identity/phone gates, >=7-day comparison and >=14-day operation are
**BLOCKED_EXTERNAL / NOT EXECUTED**.

## T01-T28 evidence map

All rows refer to original synthetic corpus inputs or the explicitly described
local runtime fixture. A passed automated subset never passes an external gate.
Test names identify cases and variants; the corpus itself remains frozen.

| Case | Executed automated evidence | Remaining scope |
| --- | --- | --- |
| T01 | AB old/reposted news assessment | Live source timing/coverage NOT EXECUTED |
| T02 | Planned, denied and trusted occurrence remain distinct | Real source review/first-report policy BLOCKED_EXTERNAL |
| T03 | Same original publisher across two domains stays one evidence group | Real syndication authorization/metadata BLOCKED_EXTERNAL |
| T04 | Actual AB + PostgreSQL late independent evidence upgrades same event to revision 2 | Live evidence policy BLOCKED_EXTERNAL |
| T05 | Lower-severity denial corrects still-authorized original recipients, preserves versions | Actual recipient receipt NOT EXECUTED |
| T06 | Nearby facility records stay separate absent explicit family match | Business facility matching policy BLOCKED_EXTERNAL |
| T07 | UTC-aware conversion and future quarantine | Real market calendar/closed-day feed behavior NOT EXECUTED |
| T08 | Bounded paging, late data and empty title replay | Live retention/paging comparison BLOCKED_EXTERNAL |
| T09 | Continuous stable-ID revision replay and restart/lease fencing in PostgreSQL | Live provider revision semantics BLOCKED_EXTERNAL |
| T10 | Model stub timeout, malformed/unsupported results fail conservatively | Product model calls/token billing NOT EXECUTED |
| T11 | Decimal 50.20 delta, ten incompatible bases excluded; persisted preview/import/report | Authorized customer quote sample BLOCKED_EXTERNAL |
| T12 | Stale quote and offline US weekly inventory keep source periods/gaps | Live inventory or commercial feed NOT EXECUTED |
| T13 | Real insert/checkpoint rollback; pending records survive runtime reconstruction | Physical process kill at every transaction/enqueue boundary NOT EXECUTED |
| T14 | Actual normal queue send blocked while urgent queue completes synthetic deliveries | Load target/P95 SLA and actual model contention NOT EXECUTED |
| T15 | Parallel PostgreSQL claim is unique; accepted mock response is not resent | Actual provider idempotency/known-success reconciliation NOT EXECUTED |
| T16 | Lost response and expired delivery lease remain UNKNOWN, stale worker fenced | Real ambiguous provider result reconciliation NOT EXECUTED |
| T17 | D raw signature verifier plus C storage reject forgery/stale/cross-user/revision/tenant/message; replay idempotent | Real Feishu callback setup/deadline/phone NOT EXECUTED |
| T18 | Recipient/version-specific ack; finite reminders; old ack cannot acknowledge revision 2 | Actual reminder receipt NOT EXECUTED |
| T19 | No-data report, cutoff isolation, date uniqueness/restart and browser report | Real morning delivery/operator acceptance NOT EXECUTED |
| T20 | Injected rate/auth/quota errors retain cursor, count requests and mark source degraded | Licensed endpoint/limits/maintenance notification NOT EXECUTED |
| T21 | Malicious article text cannot redirect recipients or run tools | No external article/model execution authorized |
| T22 | URL target restrictions and malicious CSV/XLSX cases; gateway upload boundary | Authorized real document sampling BLOCKED_EXTERNAL |
| T23 | Actual API session/CSRF/role/revocation/forwarded link plus browser access checks | Real SSO identity and tenant account login NOT EXECUTED |
| T24 | Actual 390px Chrome rendering against local API and PostgreSQL | iOS/Android foreground/locked/background/DND/offline/logged-out matrix BLOCKED_EXTERNAL |
| T25 | Custom dump, isolated restore, counts and recovery to UNKNOWN; overwrite refusal | Production RPO/RTO, image/schema rollback and off-host backup NOT EXECUTED |
| T26 | Actual queue heartbeat/restart; API failure canary not exported | Off-host detection, maintenance notification and full operational-log audit NOT EXECUTED |
| T27 | Stored fixture lineage, test-only grants, dry-run states and UI labels; D mock sender verifies fixture label | No real recipient or production fixture sending |
| T28 | Evidence-linked deterministic reports, durable budgets/reserve/UTC reset and distinct runtime delivery counters | >=7-day comparison, >=14-day operation, real cost/coverage/receipt BLOCKED_EXTERNAL |
