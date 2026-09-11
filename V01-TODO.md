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
| M0 | Read-only baseline; C freezes contracts, dependencies and API schema | DONE for foundation scope on C branch; final integration pending |
| M1 | AB replay/assessment + C transactional pipeline + D dry-run/ack | Local synthetic E gates PASS; final I pending; real source/phone BLOCKED_EXTERNAL |
| M2 | Revisions, independent evidence, failure recovery, authorization | Local synthetic E gates PASS; full process-kill/load/external scope untested |
| M3 | Daily reports, safe quote imports, five responsive views | E actual browser PASS; AB summary copy correction accepted; final I pending |
| M4 | E regression/security/PostgreSQL/Compose; separate I integration | All four local tracks accepted; separate I READY |
| M5 | Authorized source/phone and >=14 days operation | BLOCKED_EXTERNAL |

Ownership is recursive below; prefixes resolve against each track's actual
worktree. Unlisted files have no owner. C receives the plan's M technical files
because the user requires the coordinator to avoid business code. AB combines A
and B to reduce agent count; independent source and processing modules remain.

| Track | Exclusive write_paths | Initial work / state |
| --- | --- | --- |
| M | AGENTS.md, README.md, V01-TODO.md | decisions, status, acceptance / RUNNING |
| C | src/oil_agent/contracts/, src/oil_agent/storage/, src/oil_agent/runtime/, src/oil_agent/api/, src/oil_agent/__init__.py, src/oil_agent/bootstrap.py, tests/contracts/, tests/conftest.py, tests/unit/storage/, tests/unit/runtime/, tests/unit/api/, pyproject.toml, uv.lock, .python-version, .env.example, .gitignore, alembic.ini, config/ | local runtime accepted; retained for integration fixes |
| AB | src/oil_agent/ingestion/, src/oil_agent/intelligence/, src/oil_agent/reporting/, tests/unit/ingestion/, tests/unit/intelligence/, tests/unit/reporting/ | local increment accepted; integration pending; external source/model gates remain |
| D | src/oil_agent/channels/, web/, tests/unit/channels/ | local increment accepted; real API/phone acceptance pending |
| E | tests/integration/, e2e/, fixtures/, deploy/, scripts/, .github/workflows/, docs/runbook.md | local increment accepted at 06af7997; retained; external gates untested |
| I | future separate worktree; merge commits and minimal bootstrap/import/config/type glue after transfer | final integration / BLOCKED_DEPENDENCY |

## Verified baseline and decisions

- Repository: D:/AI_Workspace_OS/oil-agent. Original HEAD:
  082e4f2417856dc490c5a0844203aec41fe27e1b (Initial commit); only LICENSE.
- Original main clean; one worktree and one coordinator session. Existing origin:
  https://github.com/songconmaisaix31-design/oil-agent, PUBLIC; do not change visibility.
- Coordinator branch: coord/oil-v01-20260912. Commit code only to this authorized
  remote; do not copy private business documents or customer data into public Git.
- Python 3.13.13; uv 0.11.26; Node 24.16.0; npm 11.13.0; Orca 1.4.199.
- Docker CLI installed; engine initially unavailable. Existing Docker Desktop
  started with a hidden window; engine later verified (see dispatch log).
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
| C | C:/Users/DW/orca/workspaces/oil-agent/oil-v01-c / songconmaisaix31-design/oil-v01-c | f5d5face60c160e70a7565498a6da54ed33c15fd; runtime starts at d31d8f9d410375dedb4727a3999ab56442c82df3 / ctx_1248df0f39e2 (task_ccc3fe1d6a12) | local runtime accepted at 41a00ded; RETAINED |
| E | C:/Users/DW/orca/workspaces/oil-agent/oil-v01-e / songconmaisaix31-design/oil-v01-e | initial f5d5face60c160e70a7565498a6da54ed33c15fd; runtime starts at 49a1b9cb29d6d35029bba904a40f733e39580245 / ctx_d1f60fcc77b0 (task_514645bb2c7a) | accepted at 06af7997; all owned containers stopped and retained |
| AB | C:/Users/DW/orca/workspaces/oil-agent/oil-v01-ab / songconmaisaix31-design/oil-v01-ab | dd01ee225ba36c1d7e75acdf5c96cd2d8e0df482; latest same-session ctx_7b2e5fa51a81 (task_d15236706ae5) | copy-only final f3c83579 accepted; RETAINED |
| D | C:/Users/DW/orca/workspaces/oil-agent/oil-v01-d / songconmaisaix31-design/oil-v01-d | dd01ee225ba36c1d7e75acdf5c96cd2d8e0df482; latest same-session follow-up ctx_5e6e04e2d3d2 (task_1f3366c05108) | local upload-limit fix accepted at 0bbdc217; RETAINED |

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
- C published contract baseline dd01ee225ba36c1d7e75acdf5c96cd2d8e0df482
  (previous DTO commit 558010bee164f2161a0928384eb6aac36e001c07). Coordinator
  reviewed UTC/Decimal, fixture isolation, exact evidence references, version
  ownership, preallocated delivery ID and actor-scoped mobile acknowledgement.
  Worker reports 24 contract/API tests and uv build passing; full database
  foundation handoff and independent acceptance remain pending.
- Host free memory measured near 1 GiB of 31.3 GiB. Stagger heavy tests/builds;
  never stop unrelated user services. Existing user-requested long-lived track
  sessions may be retained idle while their next dependencies are developed.

## Accepted increments (not full product acceptance)

- C-FOUNDATION: code 5ab55bf47a1cedc23abba981894fcfae13b0ae50; final handoff
  d31d8f9d410375dedb4727a3999ab56442c82df3, pushed and clean. Worker: 42 tests
  without skips, locked sync, Ruff, build, PostgreSQL 16.14 fresh migration,
  Alembic drift check, real Procrastinate task, live HTTP smoke. Coordinator:
  `uv run --locked pytest tests/contracts tests/unit/api -q` -> 32 passed;
  `uv run --locked ruff check src tests` -> PASS; actual DB migration queried as
  `0001_foundation`; scope/diff reviewed. One upstream AnyIO deprecation warning.
  See C `config/foundation-handoff.md`. Business pipeline not yet implemented.
- E-BASELINE: code 62bd7d699bd39e02586d616796f34f6d22dc45f7; final handoff
  49a1b9cb29d6d35029bba904a40f733e39580245, pushed and clean. Coordinator reran
  `python scripts/validate_scenario_corpus.py` -> PASS for 28 synthetic cases;
  all 28 application cases remain NOT EXECUTED. Worker also checked 12 corrupt
  variants, Ruff, links and missing-file failure. Exactly five E-owned files.
  See E `e2e/baseline-checks.md` and `docs/runbook.md`.
- C same-terminal reuse: `worker-start --terminal` returned agent_unconfigured;
  no new Task/Dispatch was created (enumerated). Existing C session and completed
  transcript remained proven. CLI-documented explicit `task-create`, `dispatch
  --return-preamble` and `terminal send --wait-submit 10` reused the same terminal;
  receipt c220f3ff-b9b5-4584-88e6-733938e931d3 confirms input_accepted and
  turn_started. New runtime dispatch is a low-level dispatch, not a newly owned
  supervised process; old C resource is explicitly retained for the user's
  one-session-per-track requirement. No runtime patch or approval change made.

## Active integration decisions and evidence

- C contract increment e09683409550bbe7238396bc2506def3969ad202 adds
  IdentityAdapter, session challenge/CSRF response and quote parser seams.
  Follow-up bb39ece229c32131025b4a4ead7d7502ba471e0b supplies the trusted
  QuoteParseRequest envelope. Coordinator reviewed both. Consumers may merge
  these exact upstream commits normally; no manual edits to producer-owned files.
- IdentityAdapter uses configured authorization_url(state) and authenticate(code).
  C owns browser-bound one-time state, preprovisioned active identity mapping,
  revocable hashed sessions and CSRF. D callback verification uses an injected
  server identity resolver; C rechecks current recipient/version grants on ack.
- C owns quote preview persistence and derives provenance/publisher/time from
  server configuration. AB parses the bounded uploaded CSV/XLSX. A client cannot
  turn fixture data into production data by selecting metadata.
- AB first code increment d6c9e64 is pushed. Worker reports 34 ingestion/contract
  tests, Ruff and build passing. Coordinator reviewed parser/network boundaries;
  no commercial source socket transport or live-source acceptance is included.
- D initially had input_accepted but no working-turn/transcript evidence. The
  existing PTY was preserved. A distinct coordinator follow-up in that same
  terminal produced request 782d62a4-f9fb-46a5-b7ff-078305a9d1ea with
  input_accepted and turn_started; exact provider transcript subsequently shows
  real task work and D acknowledged the contract. No duplicate worker was started.
- AB final local increment: 25cceea0bfb78930879060417054e4675d84956d. Code
  includes d6c9e64 (ingestion), 8a359497520ee12a46dc94fbffa579ece110f209
  (assessment/reports), and the final parser/handoff commit. Main verified exact
  remote SHA, clean status, exclusive 18-file AB diff against bb39ece and ran
  `uv run --frozen pytest tests/unit/ingestion tests/unit/intelligence tests/unit/reporting tests/contracts -q`
  -> 74 passed. Worker full non-PostgreSQL selection -> 85 passed, 3 PostgreSQL
  tests deselected; Ruff and wheel/sdist build passed. No live transport/model,
  PostgreSQL, phone or continuous-operation claim. See AB-HANDOFF.md in reporting/.
- E resumed using the same documented low-level path as C after worker-start
  returned agent_unconfigured without a task. Exact live preamble delivered once;
  request 4ff12822-4293-4050-af2f-3a4fe856e825 proves turn_started on original
  process incarnation 790338b3-5161-4cbb-8046-abb0df1b37fd. Current dispatch is
  unsupervised in resource accounting; original retained terminal remains live.
  E may adopt exact reviewed C/AB commits for its tests, preserving producer files.
- Runtime review returned concrete fixes to C: loss of occurred assertion routes
  as a correction; empty/duplicate ticks must not consume processing/model budget;
  a second quote preview after time advances must remain import-idempotent. E will
  test these across real modules. Notification policy and channel readiness remain
  closed by default; configuration references do not constitute live acceptance.
- C runtime 88338fafc7f8be55ce0fe7e0e7edf62758b5f3de is available for dependency
  testing: worker 55 tests with PostgreSQL, Ruff/build/Alembic and real named tick
  jobs passed. Main ran non-PostgreSQL tests -> 39 passed, 16 deselected, one
  upstream warning; both C and E databases queried as migration 0002_runtime.
  Empty configured worker ticks do not establish a business pipeline result.
- C follow-up ffb62d282c3b65a742f303eeab7a61ade0e28643 is reviewed for dependency
  adoption. Report delivery now runs on normal, event delivery on urgent with
  filtered database claims. Runtime.authorize_recipient accepts D's actual
  RecipientAuthorization type. Worker reports 61 tests. Full C acceptance pending.
- D local increment accepted at 38a065e1a3f71631e4a8af915069982fe02303e6:
  exact remote SHA and 32 exclusive D paths verified. Main ran locked channel and
  contract tests -> 81 passed; frontend tests -> 11 passed; npm run build -> schema
  consistency, TypeScript and Vite PASS. Main inspected the labeled 390px screenshot.
  Worker reports six isolated Chrome checks, all using mocked HTTP; no real API or
  phone acceptance. See web/HANDOFF.md. D stopped its dev server and retained session.
- E deployment scaffold 5047d8bb78f8d092ece2e7398d0be3e568175881 is pushed;
  worker reports Compose configuration, shell syntax and four boundary checks.
  Local replay integration increment 4730819 has 35 passing checks. E's isolated
  PostgreSQL is live at loopback 55434; application/container acceptance is ongoing.
  E owns fixes for migrate command spelling, base64 upload proxy allowance and
  copying authoritative OpenAPI into the frontend image build context.

## Latest reviewed fixes and acceptance

- C runtime final 41a00ded1f949aee8099b549d5d419f0487dd0f9, code
  571a4af958754899c3cf8903d52075e9b8a616ff: exact remote verified and handoff
  reviewed. Worker reports 69 tests without skips on real PostgreSQL, fresh
  migration/drift, locked sync, Ruff, build and HTTP smoke. Its isolated database
  container was stopped and retained. See config/runtime-handoff.md on C.
- Original E T04 failed on C88338fa because late independent evidence was assessed
  without durable same-family history. C16d064e adds bounded history and captured
  head checks; E reran the original assertion with actual AB and PostgreSQL -> PASS.
  C ad19dce adds authoritative Chinese notification content; 571a4af fixes
  second-pass quota exhaustion deferral without hot retries or consumed attempts.
- AB replay fix f3b726d1a194f192f7fc4dc5908882190b416b96 supports stable
  record IDs with immutable revisions and arrival-order cursors. Main reviewed the
  diff/remote and ran ingestion tests -> 25 passed. Original E T09/T05 regression
  rerun remains required; the failing assertions were preserved.
- D final 0bbdc217b43aec94e66ead9863a734f7902d20f2, code
  b35e5a3945157a0c74a4f06410b822dd06c6bef8 aligns both browser preflights and
  wording with AB's 2,000,000-byte upload limit. Exact remote/diff verified;
  main frontend tests -> 13 passed, including exact-limit and limit-plus-one.
- E actual API/PostgreSQL/browser exposed default field_mapping={} rejection.
  AB final 026490a4558ffc50dba03a28c14b2e03dcfa32e9 now derives exact canonical
  fields from validated CSV/XLSX headers and preserves strict explicit mappings,
  optional basis fields, provenance and stable identities. Main reviewed the three
  owned files and matching remote, then ran ingestion tests -> 42 passed. E is
  authorized to merge this exact commit and rerun the original browser flow.
- E has built both Linux images and reports five real PostgreSQL operations cases
  including blocked-normal/urgent Procrastinate isolation, plus nine signed
  callback/HTTP permission cases. Platform-accepted rows in these tests are
  explicit fixtures, not evidence of Feishu delivery. Six real API browser flows
  passed before the default quote failure; full browser acceptance remains pending.
- E may rebuild/recreate only its own stateless init/api/ingest/urgent/normal/
  gateway services after verifying Compose project/service identity. Preserve
  oil-agent-e-postgres-1, its volume and networks, and all unrelated resources.
  No compose down, volume deletion or prune. Final image identities must be recorded.

## E acceptance and final integration boundary

- E final 06af7997043c03bd06c91e9afab560bcf4432ae5 is clean and matches origin.
  Main reviewed e2e/runtime-checks.md, settled screenshots and exact dependency
  SHAs. The original T04/T05/T09 assertions and default quote flow now pass.
- E local integration: 69 passed without skips, including 31 actual PostgreSQL
  cases. Actual Linux gateway/API/PostgreSQL Chrome checks: 8 passed, no page
  errors. Gateway accepts 1,976,096 raw bytes and rejects 2,000,001 bytes. This
  uses synthetic sessions, not real OAuth or phone delivery.
- Main independently queried successful Actions 34638262292 on E code/CI SHA
  3bafd0ba63cbd62fd2c904d70633fbf1c5720ec4 and read its result lines: core 195,
  integration 69 and frontend 13 passed, with no skips; frontend and both Linux
  builds passed. E's successor evidence-commit run is separate; I must verify
  its own final integrated HEAD.
- Final E images, PostgreSQL identity and before/after/final service states are
  recorded in e2e/runtime-checks.md and runtime-artifacts/. All seven E containers
  stopped normally and were retained. Backup and isolated restore passed with
  matching 1 record / 2 versions / 1 ack; repeated target refused overwrite.
  Restored expired in-flight delivery became UNKNOWN without resend. Graceful
  Linux urgent restart passed; exhaustive SIGKILL/SLA/production rollback did not run.
- Visual review found AB's developer coordination placeholder in change_summary.
  AB final f3c835793da03a0b0f1b8fb130c6312db2094d80 replaces only that visible
  copy and its handoff; main reviewed the two-file diff, clean state and remote.
  Worker intelligence tests: 14 passed; scoped Ruff passed. No decision/hash/model/
  status changes. E evidence remains tied to AB026490a4 until final I checks.

After that copy-only handoff, I receives these exclusive glue write paths:
src/oil_agent/bootstrap.py; .env.example; deploy/compose.yaml (factory default only);
docs/runbook.md (integrated factory/startup notes only);
tests/integration/test_bootstrap_factory.py; config/integration-handoff.md.
src/oil_agent/runtime/cli.py is permitted only if a minimal factory seam is needed.
These are explicit transfers from completed owners, not permission to change their
other files. Main continues to own AGENTS.md, README.md and this board.

I must merge exact C/AB/D/E commits, wire existing safe AB/D services, test the
factory against a fresh I-only database at loopback 55435, push and verify complete
final-head Linux CI. Existing C/E credential values are not to be discovered or
their test guards broadened; CI supplies new isolated scopes for all PG tests.
No new domain implementation or production activation. Real source, platform,
phone and continuous-operation gates remain BLOCKED_EXTERNAL.
