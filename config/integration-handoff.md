# I integration handoff

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
- This report is a later evidence commit and is the PRELIMINARY handoff. Final
  governance adoption and its exact final Actions HEAD will be reported through
  the coordinator lifecycle receipt after the required governance merge.

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
