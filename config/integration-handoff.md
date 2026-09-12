# I integration handoff

## Current phase: real integration v1.1

Accepted starting point: `ed1de2e24634e8471e0979cfc168eebec4c12e4c`, local
fixture/dry-run only. The original I branch/worktree/session were clean and reused.
Governance `57e72ee` was ordinary-merged at
`7c55e6add97de8170f43652f8b356abae1e914b8`. The current phase in V01-TODO.md
supersedes the historical delivery timing and external-gap labels below.
The initial design below is now assembled and locally verified. Independent E
acceptance and complete CI on the assembly commit remain pending at this receipt.

### Assembled code increment

All integrations used ordinary merges on the original branch. Intermediate
candidates were pushed and sent to M/E as each producer increment arrived:
`26e3391` (C construction), `0be5ab7` (D identity), `85fdcff` (AB source),
`05231c5` (AB model/rules), `54b9c1d` (request receipt guard), `bf9c467`
(C operations), `5fd432c` (rule regression repair), and `bf4629b` (D schema).
Assembly parent is `21b28fa948280e319bf21edd9aab3264f9364177`, including C
`11ab06f0712d5bde0ff5d408cbf807d5989a8db9`, AB
`651c11428642b8a3ac5549c7d40cc6edff3fe0f7`, D
`ea2c3abbc84321f230d5ac3c63140af837d594ab` and E
`6be21de982fd33c92c497701db21e82cb7d28604` with their reviewed ancestors.
No producer implementation was edited by I. The commit/push receipt supplies the
exact assembly SHA and Actions URL; earlier candidate CI is not final acceptance.

The shared executable factory is `oil_agent.bootstrap:build_runtime`; API
`oil_agent.bootstrap:create_app` and every CLI worker select it consistently.
Its explicit fixture/trial branches construct existing services only. Production
assembly rejects startup. Default fixture/dry-run remains empty, with no source,
model, identity, user, recipient, session or sample-data seeding. First-report
policy remains unset. Nonfixture process startup uses `OIL_DATA_PROVENANCE=trial`
and `OIL_FIXTURE_DATASET=null`, as supported by C's Settings parser.

Jin10 source identity/rights and OpenAI model identity come from the exact C
permission objects. Every provider request binds C's durable reservation callback;
model usage binds the returned reservation ID, including unknown usage. Assessment
uses its urgent client/budget; deterministic normal-lane reports have no model
client. Loaded AB rules must match `authorization_ref@version` against each
model/send permission, contain no ambiguous `@` component, cover the permission
validity/provenance, and match enabled source IDs. This M-approved configuration
convention is not business-rule approval. Feishu login/sending/callback use one
approved tenant/app/subject mapping and C's authorization functions. No factory
provisions principals; tests invoke the distinct C approved-provisioning action.

I edits in this increment: `src/oil_agent/bootstrap.py`, `.env.example`,
`deploy/compose.yaml` (shared environment only), `docs/runbook.md` (startup only),
`tests/integration/test_bootstrap_factory.py`, and this handoff. Existing CLI
factory loading required no additional edit. Compose remains internal-only;
environment wiring does not enable network egress or deployment.

Local checks on the assembled tree:

- `uv sync --locked`, full `ruff check src tests`, `git diff --check`, and
  `uv build --out-dir <I-private-temp>` passed. Corpus checker passed consistency
  for 28 fixed cases; it does not execute application acceptance.
- Explicit contracts, ingestion, intelligence, reporting, channels, runtime,
  API and E rule-regression paths: 313 passed, zero skips/deselections. C's
  database-scoped unit tests were not invoked by this local command; full CI
  must run them against its separate C PostgreSQL service. One existing
  Starlette/AnyIO deprecation warning remains.
- Frontend: 23 tests passed; generated-schema check, TypeScript and Vite passed.
  Linux application and frontend images built serially, with no deployment.
- I-only PostgreSQL smoke: 18 bounded checks passed, including fresh migration
  `0003_trial`, queue schema/recovery, exact source history, durable source budget,
  expired approval rejection, actual source/model/rules/PostgreSQL with routine
  silence and persisted token usage, five rule-binding denials, approved OAuth
  through actual D adapters into C session/outbox/signed acknowledgement, revoked
  session rejection, and actual loopback HTTP health/readiness/401/501 checks.
  No principals were seeded by construction. This invokes the new I test routines
  on I's own isolated schemas; it is not an E pytest-suite acceptance claim.
- The final smoke uses 20 synthetic source HTTP exchanges, two synthetic model
  responses and four synthetic platform responses. Product provider calls,
  tokens and paid cost remain zero. Loopback HTTP is local testing only.

Smoke artifacts are task-private outside Git at
`C:/Users/DW/AppData/Local/Temp/oil-agent-i-v11/`. Two earlier smoke harness/test
assembly failures were corrected; their redacted failure artifacts remain. The
final receipt has 18 passing checks. No existing password was read: a new role
and database were created inside the verified retained `oil-agent-i` PostgreSQL
container on loopback 55435 for each attempt, with process-only throwaway
passwords. All I test databases and the container are retained, container stopped;
C/E resources were not operated on. No credential or session artifact is in Git.

Ten new factory PostgreSQL cases join the three baseline cases. They use E's
existing migrated fixture in normal pytest/CI, with no authorization mocks,
database guard changes or skipped-PostgreSQL acceptance. Full CI must retain its
two explicit services, `OIL_TEST_DATABASE_URL`, `OIL_E_TEST_DATABASE_URL` and
`OIL_AB_PACKAGE_ROOT=${{ github.workspace }}/src/oil_agent`.

Prior failures remain recorded by E: the initial three fixture/production sender
cases, stale app-identity fixture, and two false-urgent rule cases. E supplied
scoped fixture-trial sender/identity repairs without relabeling data; AB supplied
the rule repair and E's unchanged 15 rule cases now pass locally. Remote full-suite
success and E's independent assembled-factory acceptance still need confirmation.

### Minimal assembly design and owner contracts

- Keep `build_runtime`'s ordinary default fixture/dry-run behavior. Introduce a
  separately selectable trial assembly only after adopting C's authoritative
  classification/permission configuration. Production remains separately gated;
  never change provenance by rewriting all fixture flags.
- Construct the repository and C Runtime first, then attach AB source/model/rules
  and D channels through their existing service protocols. Constructors must not
  issue network requests or provision users, sessions or recipients.
- C owns permission validation, durable budgets, transaction/checkpoint/outbox
  writes, identity provisioning and per-recipient/version decisions. I forwards
  typed configuration and callbacks, without duplicating those domain rules.
- AB owns concrete Jin10 and model transport/parsing plus configured approved
  assessment rules. I will use the exact exported constructor/DTO signatures in
  each reviewed handoff, without inventing endpoints, models or rules.
- D's existing FeishuChannel, FeishuIdentityAdapter and FeishuAckVerifier are
  reused. Channel authorization binds Runtime.authorize_recipient; verifier
  bindings remain Runtime.resolve_identity and Runtime.verify_delivery_message.
  Proposed identity subject `tenant:app:open_id` requires coordinated C/D/E
  adoption; old fixture sessions must not acquire real-identity authority.
- Environment/Compose changes only expose the owner-defined explicit project
  injection fields. No unrelated credential lookup, implicit dotenv loading,
  default recipient injection or product network call is part of assembly.

C supplied these exact async hooks through the coordinator; implementation SHA
and exported permission models must be adopted before wiring them:

```python
latest_source_record(source_id, external_id) -> SourceRecord | None
authorize_source_request(source_id, provider) -> str
authorize_model_request(provider, model, reserved_tokens, *, urgent=True) -> str
record_model_usage(reservation_id, input_tokens: int | None, output_tokens: int | None) -> None
```

The source history hook reads only the latest committed immutable version.
AB proposes stable IDs/revisions; C validates and commits them atomically with
the cursor. Source/model authorization occurs before every provider request,
including explicitly permitted retries. The returned model reservation ID is
used for actual usage evidence; unknown usage stays unknown. C permission types
are SourcePermission, ModelPermission, IdentityPermission and TrialSendPermission
with approval identity, authorization reference, validity interval and exact
provider/model/recipient/budget scope. These are owner contracts, not grants.

### Incremental verification and classified gaps

For each exact producer commit: ordinary merge, resolve only I-owned glue, run
relevant locked checks, commit/push, and hand the exact candidate to M for E's
independent acceptance. Domain defects go back to their original owner. Keep the
current dispatch open for subsequent increments and repairs until M concludes it.

Assembly verification will use actual services with deterministic provider HTTP
responses and real PostgreSQL authorization. Required behaviors include unchanged
fixture defaults, explicit trial classification, missing/expired/wrong-scope
denials, callbacks bound to current identity/message/version, durable provider
request budgets/usage, and non-urgent source/model/storage output with no alert.
Labeled urgent exercises are separate from actual emergencies and require their
own exact test-recipient permission. No test principal is seeded by a factory.

Current gaps: the bounded source/model/rule/runtime/channel assembly is implemented
and locally checked, awaiting E and complete CI confirmation. Actual provider,
rules, budget and exact-recipient inputs are **missing authorization**; all real
source/model/identity/send behavior is **implemented, awaiting real testing**.
Production factory/deployment remains **missing implementation** outside this
local increment. Prior local evidence does not settle any real chain. Product
source calls 0, model calls/tokens 0, Feishu sends 0 and paid product cost 0.
Public documentation,
dependency, Git and Orca traffic are excluded from product call counts.

## Historical local integration evidence

This is local synthetic integration evidence, not production acceptance. The
user-supplied Markdown plan is the business source; original PRD/source-report
documents and real source, identity, recipient and deployment authorization remain
unavailable. I changed only the explicitly transferred glue paths.

## Candidate and preserved ancestry

- Branch: `songconmaisaix31-design/oil-v01-i`.
- Actual starting base: `a187197f273a0abfcf84f84f241e7f4bac335b9d`.
- Exact producer commits merged normally in C, AB, D, E order, without conflicts:
  C `41a00ded1f949aee8099b549d5d419f0487dd0f9`,
  AB `f3c835793da03a0b0f1b8fb130c6312db2094d80`,
  D `0bbdc217b43aec94e66ead9863a734f7902d20f2`,
  E `06af7997043c03bd06c91e9afab560bcf4432ae5`.
- Producer merge checkpoint: `35217f41016c83fa76bda624cb3a31be67a3befc`.
- I factory code: `a4617e9528177c536c1768297f1ff5783ee1f9ec`, pushed to the existing
  origin; `git ls-remote` matched exactly. No cherry-picks, resets or force pushes.
- PRELIMINARY evidence commit: `8feb61b8778ca847f3fd1be53124b89203024cb9`, accepted
  by the coordinator after independent code, smoke and CI review.
- Final governance `7839b316dad94296857c4b901fe11333a8d24644` was ordinary-merged
  without conflicts. Only README.md and V01-TODO.md arrived from the coordinator;
  I made no governance edits. All four producer commits and this governance
  commit remain ancestors. This final report adoption update changes no code.
- The completion receipt records the final pushed SHA, exact matching origin,
  clean status and its own completed Actions run. The earlier code-run success
  below is historical evidence and does not substitute for that final check.

## Shared factory and scope

`oil_agent.bootstrap:build_runtime` returns C Runtime using SafeQuoteParser,
ConservativeAssessmentService, SnapshotReportService and DryRunChannel. CLI
`load_runtime` uses that path if its explicit argument and OIL_RUNTIME_FACTORY are
absent or empty. The API's `oil_agent.bootstrap:create_app`, `.env.example` and
Compose use the same path. The CLI change is limited to that default loader seam.
Explicit trusted overrides retain precedence and the Runtime return-type check.

The factory creates no sources, polling schedules, users, recipients, sessions,
product records or business configuration. C's unset first-report policy, fixture
lineage, revocable database sessions/CSRF/roles, recipient/version grants, UNKNOWN
hold policy, budgets and ingest/urgent/normal lanes remain intact. No external
source, model, identity, Feishu, SMS or phone service is enabled. E's separately
labeled opt-in factory and exact database guard are unchanged.

Changed files: `src/oil_agent/bootstrap.py`, `src/oil_agent/runtime/cli.py`,
`.env.example`, `deploy/compose.yaml` (factory default only), `docs/runbook.md`
(integrated startup notes only), `tests/integration/test_bootstrap_factory.py`,
and this report. No governance or other producer implementation was edited.

The three added PostgreSQL tests use E's existing migrated schema and actor
fixtures. Only database allocation/clock injection is used; the actual factory
constructs all services and authentication is checked against PostgreSQL without
FastAPI dependency overrides. Tests cover empty defaults and denied access,
conservative persistence/current summary, actual HTTP default-column quote
preview/import/idempotency, Decimal report reconciliation, normal-lane dry-run,
test-recipient isolation and revoked-session denial.

## Local verification

Windows, Python 3.13.13, uv 0.11.26, Node 24.16.0; checks/builds ran serially.

| Command/check | Actual result |
| --- | --- |
| `uv sync --locked` | PASS; 74 resolved, 73 installed; lockfile unchanged |
| `uv run --locked ruff check src tests` | PASS |
| `uv run --locked ruff format --check src/oil_agent/bootstrap.py src/oil_agent/runtime/cli.py tests/integration/test_bootstrap_factory.py` | PASS |
| `uv run --locked python scripts/validate_scenario_corpus.py` | PASS; 28 fixed synthetic cases; consistency only |
| `uv run --locked pytest tests/contracts tests/unit/api tests/unit/runtime tests/unit/ingestion tests/unit/intelligence tests/unit/reporting tests/unit/channels tests/integration/test_deploy_safety.py -q` | 169 passed, 0 skips; 2.86 seconds; explicitly scoped local suite, not full PG acceptance |
| `uv build` | PASS; wheel and source distribution |
| `npm ci --ignore-scripts` in web | PASS |
| `npm test` in web | 13 passed |
| `npm run generate:check`, `npm run typecheck`, `npm run build` in web | PASS |
| `docker build -f deploy/app.Dockerfile -t oil-agent-app:i-local .` | PASS |
| `docker build -f deploy/web.Dockerfile -t oil-agent-web:i-local .` | PASS; unchanged frontend build layers reused |
| `git diff --check` | PASS |

One existing Starlette/AnyIO deprecated alias warning remains. No PostgreSQL test
guard was broadened, no C/E DSN discovered and no PostgreSQL acceptance inferred
from the explicitly scoped local suite. The complete suites run in remote CI.

Built image identities:

- App: `sha256:766819aa87c53879ba88737a43ec7192aa50b1a043c4a60b6ee33188715944ef`.
- Web: `sha256:2cbacc22c556e9caf5e5d38e84e44ce36c0f750ae95915b33a9abc8ebbff91b8`.

## Fresh I database and real HTTP smoke

Immediately before allocation, loopback ports 55435/18085, the exact container
name and I project resources were free. Created only `oil-agent-i`, labeled
project `oil-agent-i` / service `postgres`, database/user `oil_i_test`, with a
new process-scoped random password passed by environment name, never printed or
saved in a DSN file. No existing C/E or unrelated resource was changed.

Container ID: `b8948128e9cbe1504ba250eab07e0948a531c4193bfda1181ed7b11009ec93e1`.
PostgreSQL image: `postgres:16-alpine@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb`.

Executed the task-private `factory_smoke.py` with `uv run --locked python` from
the checkout. It ran actual CLI `migrate`, `queue-schema`, `recover`, verified
`0002_runtime` and an initially empty queue, then exercised the actual factory.
Construction left user/version/intent tables empty. Explicit synthetic evidence
was persisted separately through ReplaySource/Repository and assessed without a
model: unknown/routine/unverified, current Chinese summary persisted, no intent.
Default-column CSV parsing and an evidence-linked fixture report also passed.
No synthetic login, session or recipient was created for this I smoke.

Actual Uvicorn `oil_agent.bootstrap:create_app --factory` at loopback 18085:
health/ready/OpenAPI 200, anonymous events 401, unconfigured identity challenge
501. Actual CLI `worker --queue ingest|urgent|normal --once` each exited 0 using
the same default factory. No Windows shutdown/concurrency claim is inferred.

Smoke completed at `2026-09-11T19:33:28.479725+00:00`; Uvicorn was stopped, and
I PostgreSQL was stopped and retained. Task-private script/results remain outside
Git at `C:/Users/DW/AppData/Local/Temp/oil-agent-i-ctx-12b1d40a4d65/`.

## CI and remaining gates

Code Actions run: <https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34639549516>.
**SUCCESS** on exact code HEAD `a4617e9528177c536c1768297f1ff5783ee1f9ec`.
Downloaded JUnit artifacts confirm 195 core and 72 integration tests, each with
zero errors, failures or skips; log times are 13.90 and 16.53 seconds respectively.
All three new factory tests passed. Frontend tests: 13 passed. Locked sync, corpus,
Ruff, schema/TypeScript/Vite, shell syntax and both Linux image builds passed.
This later report commit and final governance merge trigger separate runs; the
successful code run does not stand in for their exact-HEAD checks.

The unchanged workflow supplies
two explicit ephemeral PostgreSQL services, OIL_TEST_DATABASE_URL,
OIL_E_TEST_DATABASE_URL and OIL_AB_PACKAGE_ROOT=${{ github.workspace }}/src/oil_agent.
No deselection or hidden skip counts as final acceptance.

E's historical 69 integration tests, eight actual Chrome/gateway/API/PG flows,
backup/isolated restore, queue isolation and restart evidence remain exactly in
`e2e/runtime-checks.md`, tied to AB026490a and E's documented candidate. Those
screenshots/events were not rewritten or rerun with revoked sessions. E's seven
containers and C's container remain stopped and retained.

Real source/model, Feishu/phone, actual customer quote, production deployment,
TLS/off-host probe, seven-day source comparison and fourteen-day operation remain
BLOCKED_EXTERNAL / NOT EXECUTED. The source list is deliberately empty; factory
startup and dry-run are not live monitoring or platform/phone acceptance.
