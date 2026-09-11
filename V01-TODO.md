# V01 delivery board

## One-page execution plan

Build the independent refined-oil alert workflow described in the user-supplied
`C:\Users\DW\Downloads\成品油预警Agent_多Agent协作开发规划_v1.0.md` (2026-09-12).
First evidence: labeled replay -> PostgreSQL -> versioned event -> durable outbox ->
dry-run delivery -> authenticated acknowledgement. Then reliability, daily reports,
quote import, mobile views and deployment checks. Real source, Feishu, phone and
14-day operation are separate external gates. No production delivery is claimed.

| Stage | Work | Gate/status |
| --- | --- | --- |
| M0 | Read-only baseline; C freezes contracts, dependencies and API schema | RUNNING |
| M1 | AB replay/assessment + C transactional pipeline + D dry-run/ack | BLOCKED_DEPENDENCY: foundation |
| M2 | Revisions, independent evidence, failure recovery, authorization | BLOCKED_DEPENDENCY: M1 |
| M3 | Daily reports, safe quote imports, five responsive views | BLOCKED_DEPENDENCY: contracts |
| M4 | E regression/security/PostgreSQL/Compose; separate I integration | BLOCKED_DEPENDENCY: tracks |
| M5 | Authorized source/phone and >=14 days operation | BLOCKED_EXTERNAL |

Ownership is recursive below; prefixes resolve against each track's actual
worktree. Unlisted files have no owner. C receives the plan's M technical files
because the user requires the coordinator to avoid business code. AB combines A
and B to reduce agent count; independent source and processing modules remain.

| Track | Exclusive write_paths | Initial work / state |
| --- | --- | --- |
| M | AGENTS.md, README.md, V01-TODO.md | decisions, status, acceptance / RUNNING |
| C | src/oil_agent/contracts/, src/oil_agent/storage/, src/oil_agent/runtime/, src/oil_agent/api/, src/oil_agent/__init__.py, src/oil_agent/bootstrap.py, tests/contracts/, tests/conftest.py, tests/unit/storage/, tests/unit/runtime/, tests/unit/api/, pyproject.toml, uv.lock, .python-version, .env.example, .gitignore, alembic.ini, config/ | M-02 then C-01..04 / READY |
| AB | src/oil_agent/ingestion/, src/oil_agent/intelligence/, src/oil_agent/reporting/, tests/unit/ingestion/, tests/unit/intelligence/, tests/unit/reporting/ | A-01..04 and B-01..04 / BLOCKED_DEPENDENCY |
| D | src/oil_agent/channels/, web/, tests/unit/channels/ | D-01..04 local scope / BLOCKED_DEPENDENCY |
| E | tests/integration/, e2e/, fixtures/, deploy/, scripts/, .github/workflows/, docs/runbook.md | E-01..03 and explicit E-04 manual gates / BLOCKED_DEPENDENCY |
| I | future separate worktree; merge commits and minimal bootstrap/import/config/type glue after transfer | final integration / BLOCKED_DEPENDENCY |

## Verified baseline and decisions

- Repository: D:/AI_Workspace_OS/oil-agent. Original HEAD:
  082e4f2417856dc490c5a0844203aec41fe27e1b (Initial commit); only LICENSE.
- Original main clean; one worktree and one coordinator session. Existing origin:
  https://github.com/songconmaisaix31-design/oil-agent, PUBLIC; do not change visibility.
- Coordinator branch: coord/oil-v01-20260912. Commit code only to this authorized
  remote; do not copy private business documents or customer data into public Git.
- Python 3.13.13; uv 0.11.26; Node 24.16.0; npm 11.13.0; Orca 1.4.199.
- Docker CLI installed; engine initially unavailable. Existing Docker Desktop start
  requested with a hidden window; service readiness still to verify.
- Ports 5432, 8000, 5173, 55432 and 18080 were unoccupied at baseline. Per-track
  PostgreSQL databases, test ports and Compose project names must be distinct.
- No reusable project implementation. Referenced PRD/source-report DOCX not found
  in repository or the inspected user document locations; Markdown is provisional
  scope, never evidence that blank business permissions/configuration were approved.
- Official Procrastinate docs checked 2026-09-12: Python >=3.10/PostgreSQL >=13,
  async tasks, named queues and retries available; project requests maintainers.
  Pin the tested version and record the maintenance risk; do not invent a queue.
  https://procrastinate.readthedocs.io/en/stable/index.html
- LangGraph may perform bounded extraction/reporting only; database state owns
  side-effect idempotency. No product model calls until explicitly configured.
  https://docs.langchain.com/oss/python/langgraph/functional-api

## Public contract decisions for C to implement before fan-out

Use the plan's SourceRecord/Checkpoint, MarketObservation, EventAssessment,
NotificationIntent, Delivery/Ack, Report/Feedback DTOs and five service protocols.
Define concrete input/output/errors/timeouts, evidence IDs, UTC-aware times and
Decimal serialization; expose generated OpenAPI from one authoritative Python
schema. Frontend must generate types from it. Add explicit fixture provenance,
authenticated actor/role, recipient and event-version fields. Source fetch does
not commit cursors; graph nodes never send. Default first-report policy unset,
repeated reminders disabled, SMS/phone disabled, outbound dry-run.

## External gates and usage

BLOCKED_EXTERNAL: commercial source license/credentials/limits; actual business
scope and recipients; Feishu app/tenant/identity credentials; approved first-report
policy/budget/retention; authorized quote sample; deployment host and external
probe; phone tests; >=7-day live source comparison and >=14-day operation.
Do not inspect unrelated stored credentials. Public docs/dependency downloads are
allowed; no commercial source requests, product model calls or customer sends yet.

## Dispatch and acceptance log

Run: run_64e3991f76b9. Coordinator handle:
term_e5fa35a2-1d49-4a2c-8300-4fe6b1754ec9. Only M updates this board.
Worker success enters REVIEW until integration checks.

| Track | Worktree / branch | Base / dispatch | State |
| --- | --- | --- | --- |
| C | C:/Users/DW/orca/workspaces/oil-agent/oil-v01-c / songconmaisaix31-design/oil-v01-c | f5d5face60c160e70a7565498a6da54ed33c15fd / ctx_d958a55ca5fa (task_326ffc251dc0) | RUNNING foundation |
| E | C:/Users/DW/orca/workspaces/oil-agent/oil-v01-e / songconmaisaix31-design/oil-v01-e | f5d5face60c160e70a7565498a6da54ed33c15fd / ctx_9c35869d31f1 (task_75d768b10019) | RUNNING acceptance corpus independent of contracts |

- Governance commit f5d5face60c160e70a7565498a6da54ed33c15fd pushed to origin.
  Initial direct pushes failed with connection reset/timeout; a process-scoped
  existing local proxy restored push. No persistent network settings changed.
- Docker engine verified 29.5.3 after startup. Existing unrelated containers are
  running; do not touch them. Reserve C test port 55431, E test port 55434 and
  integration test port 55435; verify availability before use.
- Orca `worker-start --worktree new-child` returned selector_not_found before any
  task/worker creation (confirmed empty run). Explicit Orca worktree creation and
  exact path placement succeeded. Calls use the verified coordinator handle.
- Windows is development-only for Procrastinate; official docs warn of abrupt
  signal shutdown and no automated Windows test coverage. Production and worker
  recovery acceptance will use Linux containers; do not infer graceful recovery
  from a Windows-only smoke test.
  https://procrastinate.readthedocs.io/en/stable/howto/basics/windows.html
