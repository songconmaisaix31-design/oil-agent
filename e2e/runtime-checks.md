# E runtime verification

All evidence is local and synthetic. No source license, production account, model,
Feishu recipient, actual phone receipt or deployed server has been accepted.

## Current phase: independent real-integration v1.1 acceptance

E started from a clean `06af7997043c03bd06c91e9afab560bcf4432ae5`, normally
merged accepted I `ed1de2e24634e8471e0979cfc168eebec4c12e4c` and governance
`57e72ee`. That application baseline is accepted **only for local fixture/dry-run**.
The historical v1.0 evidence below remains tied to its original SHAs and commands.
New acceptance is performed only on exact integrated candidates supplied by I;
producer branch tests and passing corpus validation cannot accept R1-R4.

### Baseline gap classification

| Capability at accepted I baseline | Classification | Evidence / next gate |
| --- | --- | --- |
| Concrete Jin10 MCP network transport and flash adaptation | MISSING_IMPLEMENTATION | `ingestion/network.py` requires injected resolver/transport and has no vendor adapter; AB owns implementation |
| Concrete model client and automatic approved-rule assessment without per-message `ClaimReview` | MISSING_IMPLEMENTATION | `intelligence/assessment.py` exposes a model protocol; trusted occurrence/severity still require per-record reviews; AB owns implementation |
| Validated trial permissions, runtime/factory assembly and provenance | MISSING_IMPLEMENTATION | `runtime/settings.py` unconditionally rejects external source/model flags; bootstrap wires dry-run only; C/I own implementation |
| Feishu HTTP token/message, OAuth and signed callback adapters | IMPLEMENTED_AWAITING_REAL_TEST | Actual adapter code exists in D paths; local network doubles do not verify a real app, account, API response, callback or phone |
| Source/provider/rules/model/budget and account/recipient authorization | MISSING_AUTHORIZATION | User's exact scoped inputs are pending; missing credentials alone are not a code defect |
| First authorized nonurgent source-to-storage run | IMPLEMENTED_AWAITING_REAL_TEST, with implementation dependencies | Requires the first three rows and scoped inputs; must create no notification intent or send |
| Authorized quote, external probe, >=7-day comparison, >=14-day operation | IMPLEMENTED_AWAITING_REAL_TEST / deferred external acceptance | No new elapsed-time or real-network evidence in this increment |

These are snapshot classifications, not permanent labels. An I candidate moves a
code row only after focused checks pass. Its real-test row remains NOT EXECUTED
until the corresponding authorized operation produces evidence.

### Focused acceptance stimuli and criteria

All local stimuli below are newly authored synthetic material or existing E
fixtures. Network doubles are explicitly isolated and never contact a provider.
Tests that need trial/production DTO values exercise classification in a disposable
E PostgreSQL schema; their input origin remains synthetic, never real news.

| Scope | Concrete stimulus | Required observations |
| --- | --- | --- |
| R1 source/MCP adaptation | Two synthetic MCP pages containing a terminal maintenance bulletin, duplicate external ID, later same-ID revision, blank title, malformed envelope and an explicit remote error | Actual adapter parses the documented tool result shape, retains evidence/rights and original publisher, bounds page count/bytes, preserves revisions; C stores records and checkpoint atomically; malformed/error results do not advance the cursor |
| R1 network boundary | Disallowed host, redirect to loopback, private IPv4/IPv6 resolution, oversized/chunked body, timeout, 401 and 429; revoke approval between two pages | No disallowed connection or environment-proxy escape; each actual request/hop rechecks permission and charges attempt budget before transport; bounded failures, safe error text and no hidden retry |
| R1/R4 approved-rule assessment | Current synthetic maintenance notice: no outage, no casualty, no disruption; then a separately labeled synthetic urgent-exercise terminal closure matching an approved rule | No per-message `ClaimReview` is injected; actual rule/model path records processing version and exact supporting evidence; nonurgent case persists with **zero intents, deliveries and message HTTP requests**; exercise result is labeled and cannot broaden recipients |
| R1 untrusted input | Article asks to add `ou_unapproved`, expose a synthetic secret canary or execute a command; model supplies an unsupported excerpt, invented number, invalid JSON or conflicting denial | Data does not change rules/recipients or trigger tools; output is rejected or conservatively downgraded; no unsupported urgency/send; safe error with explicit degradation |
| R1/R2 cost | Zero budget, final allowed request, concurrent requests for the final reservation, model timeout and reported usage above reservation; approval expires between calls | Durable per-approval and daily accounting bounds actual calls/reserved tokens; no retry over budget or automatic paid fallback; actual vs reserved vs unknown usage remain distinguishable |
| R2 trial provenance | Fixture source mixed with trial input, trial record assessed/reported, spoofed DTO flags, and a fixture session used after switching to real identity | Provenance survives source/evidence/event/report/intent persistence and is validated; fixture input does not silently become real; fixture sessions cannot authenticate as real; trial scope does not become production authority |
| R2 trial permissions | Expired/revoked source/model/identity/send approval, mismatched provider/model, wrong tenant/app/subject, non-test recipient, per-recipient revision mismatch | Fail closed at execution time, including revocation after claim/token acquisition; exact preapproved bindings only; no widening users/recipients, implicit sessions or production sends |
| R3 OAuth | Actual C HTTP challenge and session endpoints plus actual D OAuth adapter; synthetic token/user-info responses, wrong browser/state/origin, wrong tenant/app, unknown or revoked user and lost token response | Browser-bound state consumed once; provider role/name cannot grant access; unprovisioned user stays absent; HttpOnly/Secure session is revocable; no user token/code/secret exposed; a lost exchange requires a new challenge |
| R3 message and ack | Exact synthetic recipient, mock accepted message ID, raw signed callback, then cross-user/app/tenant/message/revision callback, replay and response loss | Actual C authorization and D sender/verifier connect end to end; ack binds recipient + message + subject + revision; replay idempotent; UNKNOWN is not retried; local accepted response is not platform/phone evidence |
| R4 integrated factory | I's actual configured API and worker factory on the same integrated SHA; defaults with no permissions, then isolated approved trial configuration | Default fixture/dry-run stays closed and seed-free; configured adapters use C permission callbacks; no duplicate domain implementation; I owns factory/bootstrap test and narrow startup wiring |

The first authorized nonurgent run must separately record source request attempts,
successful records and revisions, model requests/input/output tokens, database
results, notification intents, platform message attempts, platform acceptance and
phone receipt. A zero-send observation is a successful silence gate; it does not
establish that urgent delivery works. Real urgency can be tested only as a
separately approved, clearly labeled exercise to the exact test allowlist.

### Current execution scope

`uv run --locked pytest tests/integration/test_postgres_oauth.py -q --tb=short
--junitxml=e2e/runtime-artifacts/v11-oauth.xml`: **10 passed, 0 failed, 0 skipped,
7.74 seconds**, exit 0, on the accepted I baseline plus governance and this E test
increment. One existing Starlette/AnyIO deprecation warning remains. The command
used Windows Python 3.13.13 and actual retained E PostgreSQL 16.14, loopback 55434 /
`oil_e_test`, with an explicitly injected process-only test DSN and fresh migrated
schema per case. No SQLite substitution, real account, dependency-overridden auth
or synthetic preissued session was used. The provider boundary is exclusively
`httpx.MockTransport`: **6 token exchange attempts + 4 user-info requests = 10
synthetic HTTP requests**, no network. Four preflight rejection variants each made
zero provider requests; replays made no extra request.

Coverage: successful exchange into a revocable viewer session, safe cookie/token
handling, no automatic user provisioning, wrong tenant, unknown/revoked user,
invalid token, lost exchange without retry, consumed-state replay, missing/foreign
browser cookie, expired challenge and cross-origin login. The baseline subject
format remains `tenant:open_id`; proposed `tenant:app:open_id` and trial permission
changes are **NOT YET ACCEPTED** and need the integrated I candidate.

`uv run --locked ruff check tests/integration/test_postgres_oauth.py`,
`uv run --locked ruff format --check tests/integration/test_postgres_oauth.py`, and
`git diff --check`: PASS. No broad historical baseline rerun or image build was
performed. R1/R2/R4 implementation checks await I's exact integrated candidates.

The coordinator allocated a short E PostgreSQL-only slot. Identity, Compose
ownership, retained volume and free port 55434 were checked before starting exact
container `b3c3a345428590922eb8e628a996dd634cb3333e5f0c86f588eede8fb7101cab`.
After the focused tests it was **stopped and retained, exit 0, OOM=false**; the slot
was released. No other container or volume was changed.

Product source calls **0**; product model calls/input tokens/output tokens **0**;
product Feishu requests/sends **0**; paid product cost **0**. Synthetic HTTP request
counts will be reported separately. No real provider login, phone check, deployment,
authorized-source comparison, 7-day or 14-day run was executed. Future unmeasured
provider billing must be recorded as unknown, not inferred to be zero.

### Candidate 1: C permission construction and committed history

Exact integrated candidate **`26e3391c24afaa5e098f545831610961204a7802`** includes
C `aa7d638dbbb9041bf3c9465803b6b61bb939e5bd`, governance `86aaadf`, and E preparation
`4a55ffe95e1a13efb0ccbe4f365306a26b1e3333`. E's clean branch fast-forwarded to this
exact I SHA before adding only the independent history tests/report below.

**LIMITED_LOCAL_PASS for construction checks; full candidate acceptance FAIL**.
The locally passing subset covers validated fixture/trial/production
settings and explicit bounded permission objects; scoped latest committed source
revision lookup; preserved default factory and local OAuth behavior. The new
request reservations, operational trial send/session grants, pending/outbox/API
scope enforcement and actual configured source/model factory are still
**MISSING_IMPLEMENTATION / not accepted in candidate 1**, as C's handoff explicitly
states. Missing external inputs are a separate MISSING_AUTHORIZATION gate.

Subsequent exact-candidate Linux CI
[34663145891](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34663145891)
failed: **3 failed, 79 passed**, 19.66 seconds in integration. All three are
`test_postgres_channel.py` accepted/unknown/revoked variants, whose old synthetic
settings request production sending while retaining a fixture dataset. New C
validation correctly rejects this contradiction. This is **TEST_MIGRATION_REQUIRED**
with C operational trial-grant implementation dependency, not missing external
authorization. E must migrate to an explicit trial exercise without weakening
production validation or relabeling fixture records; all three original behavior
assertions remain required. The local construction result above does not erase
this failure. Subsequent E CI keeps assertions and shortens traceback formatting
to reduce unnecessary synthetic session/input representations in logs.

```text
uv sync --locked
uv run --locked pytest tests/unit/runtime/test_permissions.py tests/integration/test_postgres_source_history.py tests/integration/test_postgres_oauth.py tests/integration/test_bootstrap_factory.py -q --tb=short --junitxml=e2e/runtime-artifacts/v11-candidate1.xml
```

Results: locked sync PASS; **26 passed, 0 failed, 0 skipped, 11.55 seconds**, exit 0.
Breakdown: 10 C configuration checks + 3 new E history checks + 10 E OAuth checks +
3 I factory checks; 16 tests used actual PostgreSQL. Windows Python 3.13.13,
PostgreSQL 16.14, exact E loopback 55434 / `oil_e_test`, migrated isolated schemas.
The existing Starlette/AnyIO warning remains. Ruff check/format and diff-check PASS.

Independent history tests interrupt the actual record or cursor SQL write and
verify that the new history API still returns the previous committed revision;
successful retry and a reconstructed Repository return revision 2 with the correct
checkpoint. Another test puts explicitly synthetic fixture/trial/production-shaped
records in one schema and checks all cross-provenance and different fixture-dataset
history reads fail. These records test DTO classification only; their rights refs
and text explicitly identify synthetic origins, and no source adapter or sender is
attached. This does **not** prove mixed pending/outbox/API isolation, which remains
in the next operational acceptance set. Direct provisioning must likewise fail to
bypass future real identity grants; it is not accepted by these history tests.

Counts: product source requests **0**, model calls/input/output tokens **0**,
Feishu requests/sends **0**, paid product cost **0**; synthetic OAuth transport
requests **10**. No image build, full Compose, real identity/phone or deployment
was executed. Only the exact retained E PostgreSQL container was started after
ownership/free-port checks; it was then **stopped and retained, exit 0, OOM=false**,
and the short slot released. Domain implementation is unchanged by E.

The preceding E preparation commit separately passed Linux CI
[34662932987](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34662932987)
on exact `4a55ffe95e1a13efb0ccbe4f365306a26b1e3333`: 195 core tests, 82 integration
tests, 13 frontend tests, frontend build and both Linux image builds. That earlier
run is not exact-candidate-1 CI evidence.

### Candidate 2: D app-bound identity and trial presentation

Exact integrated candidate **`0be5ab779da9cb7b79ed467ed009d171656b0d40`** contains
D `cfda44473a0c260b51f9762624166a6b419a6ce0` and successor `8db81c7`.
E normally merged it with its candidate-1 history test increment `2964a47`;
merge HEAD was `c0eceafa65972c95f98afbec5526494d316071ba`. Only E-owned synthetic
identity mappings and rejection tests changed during acceptance; production
validation and every fixture record's original provenance remain unchanged.

**LIMITED_LOCAL_PASS for D identity/callback/UI scope; full acceptance remains
FAIL** because the same three fixture-production sender tests still require C's
operational trial/exercise path. Those known failures were not rerun in the focused
D command below, removed, skipped, relabeled or converted to expected failures.

```text
uv run --locked pytest tests/unit/channels tests/integration/test_postgres_oauth.py tests/integration/test_postgres_security.py -q --tb=short --junitxml=e2e/runtime-artifacts/v11-candidate2.xml
cd web
npm test
```

Results: **94 passed, 0 failed, 0 skipped, 20.39 seconds**, exit 0: 70 D channel
cases + 12 E OAuth + 12 E authorization/callback cases, the last 24 on actual
PostgreSQL. Frontend **18 passed**, 19.19 seconds. Ruff check/format for the three
changed Python files and `git diff --check`: PASS. Same Windows Python 3.13.13 /
E PostgreSQL 16.14 environment; one existing Starlette/AnyIO warning.

E identities now bind `tenant:app:open_id`. New negative cases prove an otherwise
matching tenant/user mapped to a different app cannot log in, a legacy tenant-only
mapping cannot log in, and a correctly signed callback claiming another app cannot
acknowledge. All earlier wrong-browser, replay, wrong-recipient/revision/message,
revocation and safe error assertions remain. Sender mapping/exercise runtime tests
will move together with C operational permissions, retaining accepted, UNKNOWN and
revoked-before-send behavior. This does not establish real OAuth or phone receipt.

Product source/model/Feishu calls and paid product cost: **0**. The E OAuth subset
made **14 synthetic HTTP requests** (8 token attempts + 6 user-info requests); D
unit transports are also isolated doubles, and their combined request total is
not separately instrumented. No external request was permitted by these tests.
No browser, image build or full Compose rerun occurred. Exact E PostgreSQL was
stopped and retained afterward, exit 0/OOM=false; test slot released.

### Candidate 3: actual Jin10 HTTP/MCP adapter with isolated transports

Exact I candidate **`85fdcff643cfaee7b94df89bde09312874aae595`** includes AB source
`d2f2d17fc0687dd75e56b21394830563df59e534` after candidate 2. E normally merged it
on top of `46b7e919f0f84628c1e2db9b911fd66983676377`; merge HEAD was
`555f6bc2407e46ffa1be5c17114fdea0a02cfc8c`. E added independent tests only in
`tests/integration/test_jin10_acceptance.py` and updated this existing report.

**LIMITED_LOCAL_PASS for source transport/adapter/storage boundary**. Concrete
source transport and MCP adaptation move from MISSING_IMPLEMENTATION to
**IMPLEMENTED_AWAITING_REAL_TEST** for this scope. Actual source/runtime assembly,
durable per-request approvals and model/rules are not established by these tests;
those implementation gaps await later C/AB/I candidates. Real source permission,
token, request budget and configured argument authorization remain missing external
inputs. Full candidate acceptance still fails on the three unresolved legacy
fixture-production sender tests; no full green claim is made.

```text
uv run --locked pytest tests/unit/ingestion tests/integration/test_jin10_acceptance.py -m 'not postgres' -q --tb=short --junitxml=e2e/runtime-artifacts/v11-candidate3-network.xml
uv run --locked pytest tests/integration/test_jin10_acceptance.py -m postgres -q --tb=short --junitxml=e2e/runtime-artifacts/v11-candidate3-postgres.xml
```

First command: **86 passed, 3 explicitly deselected, 1.05 seconds**, exit 0
(79 AB ingestion + 7 E cases). Second command: **3 passed, 7 explicitly deselected,
3.04 seconds**, exit 0. Together all **10 new E tests** execute with zero failures
or skips; the separate commands partition the DB and non-DB work. Ruff check/format
and diff-check PASS. Windows Python 3.13.13, locked HTTPX/HTTPCore and E PostgreSQL
16.14, fresh migrated schemas. A narrowly documented `ASYNC109` suppression is
limited to three synthetic methods implementing HTTPCore's required stream API.

The two new transport cases use the actual HTTPX/HTTPCore request and HTTP/1.1
framing stack, replacing only the network backend. They observe one validated
public IPv4/IPv6 target connection, original Host and TLS SNI, certificate checking
enabled, one explicit authorization and DNS resolution, and ignored ambient proxy /
certificate-file sentinels. **No actual socket or TLS handshake occurs.** Five more
cases revoke the synthetic grant before each initialization, initialized-notification,
discovery or paged tool POST and assert no unauthorized request reaches the double.

Actual Jin10Source with C committed-history lookup and PostgreSQL demonstrates:
first revision commit, exact duplicate retained, changed content proposed as revision
2, record/cursor transaction interruption, repeated fetch still proposing revision 2,
and successful retry. Malformed page 2 and revoked approval before page 2 each leave
the original committed record and cursor unchanged. Publisher availability,
occurrence time and retention coverage remain unverified; the adapter retains the
explicit coverage gap. The authorization callback in these tests is an isolated
double; durable C permission/budget enforcement is a separate later acceptance.

E synthetic operations: **2 network-backend connection attempts**, **10 MCP POSTs**
across the five denial variants, **16 MCP POSTs** in revision recovery, and **9 / 8
MCP POSTs** in malformed-page / revoked-page cases (including their initial four
setup/fetch POSTs), for **45 total synthetic HTTP requests** across E cases.
AB unit doubles are additional, not included in that total. Product source requests,
model calls/tokens, Feishu requests/sends and paid product cost remain **0**.
Only E PostgreSQL was briefly started, then stopped and retained, exit 0/OOM=false.
No image, full Compose, browser or deployment was run.

E read the public [Jin10 guide](https://mcp.jin10.com/app/doc.html),
[MCP transport specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
and [HTTPCore SNI extension](https://www.encode.io/httpcore/extensions/#sni_hostname)
on 2026-09-12 to cross-check the documented endpoint, tool envelope and IP/hostname
separation. These documentation reads are not product API requests or a source
license check. The public guide does not supply an approved input-argument or
retention contract. HTTP backend observations verify local configuration wiring;
actual certificate/server behavior remains NOT EXECUTED.

### Candidate 4: model client and reusable rules, domain failure found

Exact integrated I candidate **`05231c5a86e56c2a2e6238aeb92ce8a3920de02f`** includes
AB model/rules `85c9fb3e69b657308366e4d50248b0a4816d8bc5` and previous E tests.
E fast-forwarded its clean branch to this exact SHA. **RULE ACCEPTANCE FAIL**:
the fixed Chinese rule incorrectly treats procedure/training text as an occurred
urgent event. This is an implementation defect assigned to AB, not an external
authorization problem. The following failing regression assertions are preserved.

```text
uv run --locked pytest tests/unit/intelligence tests/integration/test_rules_acceptance.py -q --tb=short --junitxml=e2e/runtime-artifacts/v11-candidate4-rules.xml
```

Result: **2 failed, 82 passed, 0 skipped, 1.50 seconds**, exit 1. Breakdown: 69 AB
cases pass; 13 of 15 new E cases pass. The same unchanged approved synthetic rule
accepts two materially different new Chinese event descriptions without `ClaimReview`,
keeps exact evidence and missing occurrence-time uncertainty, and suppresses routine,
denied, planned, different-facility, absent/expired/out-of-provenance cases. Its
facility/event/occurrence/impact/currentness criteria nevertheless wrongly match:

- `今天澄湾油库说明发生火灾才会停止装车的应急流程。`
- `今天澄湾油库开展发生火灾后停止装车的安全培训。`

Both must stay nonurgent under the same policy; both currently return `urgent`.
E did not add per-message exclusion templates or weaken production assertions.
Exact fixed policy and stimuli are in `test_rules_acceptance.py`; AB owns the fix.
General natural-language accuracy is not claimed from these finite cases.

Five independent actual Responses-client cases pass using an isolated HTTP double:
completed response, lost response, refusal, unexpected tool output and malformed
JSON. Each reserves once and records usage once without retry. Known mock usage
is `(22, 8)`; lost/malformed response retains `(None, None)` rather than zero, and
provider cost remains unknown. This client subset passes locally; real provider
integration and factory binding to canonical approved rules remain NOT EXECUTED.

An additional exact E source-check CI observation:
[34663681247](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34663681247)
on `6fd342f0ddce579f9c019593aa770c2e022dfea8` had **4 failed, 94 passed**, 21.23
seconds. Besides the three known production/fixture sender failures, E's quote
restart test retained a tenant-only identity after app-bound fixture migration.
E corrected that single test binding and executed:

```text
uv run --locked pytest tests/integration/test_postgres_operations.py::test_T11_T19_persisted_quote_preview_import_cutoff_and_restart -q --tb=short --junitxml=e2e/runtime-artifacts/v11-candidate4-quote.xml
```

**1 passed, 0 skipped, 1.31 seconds**, exit 0, actual E PostgreSQL. The isolated
quote-binding omission is fixed; it does not erase the historical CI failure or
the three still-pending trial sender migrations. E's database was stopped and
retained afterward, exit 0/OOM=false; no further PG work starts until the next
coordinated slot. This brief test was already launched when updated non-PG slot
steering arrived. No other containers or volumes changed.

Ruff check/format and diff-check PASS. Product source calls, model calls/tokens,
Feishu requests/sends and paid product cost: **0**. E's five model cases use five
synthetic HTTP requests, with mock token figures separated from real usage. No
source/model endpoint, account, phone, deployed server or real rule approval was
used. Full acceptance remains FAIL, with two new AB policy defects and three
known sender-test migrations awaiting the C operational candidate.

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
