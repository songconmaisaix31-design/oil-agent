# C runtime handoff

Status: local runtime increment ready for independent E review and final I integration.
Verified 2026-09-12 Asia/Shanghai. No production, commercial source, model, identity
account, customer message or deployment operation was performed.

## Branch, scope and commits

- Branch: `songconmaisaix31-design/oil-v01-c`.
- Clean runtime start: `d31d8f9d410375dedb4727a3999ab56442c82df3`.
- Original track base: `f5d5face60c160e70a7565498a6da54ed33c15fd`.
- Identity/session/quote seams: `e09683409550bbe7238396bc2506def3969ad202`,
  `bb39ece229c32131025b4a4ead7d7502ba471e0b`.
- Channel/challenge contract: `4ee3700048383aa6e85aa33bdf6397796b6e6fab`.
- Initial business runtime: `88338fafc7f8be55ce0fe7e0e7edf62758b5f3de`.
- Queue isolation/recovery fixes: `ffb62d282c3b65a742f303eeab7a61ade0e28643`.
- T04 durable history and event-head fencing: `16d064e15fecf846226ae1989bca7d662a920308`.
- Authoritative notification body: `ad19dce62819273765d67897d0fcfd392e17887b`.
- Final tested runtime code: `571a4af958754899c3cf8903d52075e9b8a616ff`.
- This report is a subsequent documentation commit; resolve its SHA with `git rev-parse HEAD`.
- Existing public origin: `https://github.com/songconmaisaix31-design/oil-agent`.
  Every code increment was pushed using process-scoped
  `git -c http.proxy=http://127.0.0.1:7890 -c http.version=HTTP/1.1 push origin
  songconmaisaix31-design/oil-v01-c`. No persistent Git/network setting changed.

Only C paths changed. No AB/D/E or governance files were edited or dependency
branches merged into C. The AB handoff test imports its explicitly supplied package
path read-only with bytecode writing disabled. The inspected AB worktree tip was
`f3b726d1a194f192f7fc4dc5908882190b416b96`; its assessment implementation is unchanged
from `25cceea0bfb78930879060417054e4675d84956d`.

## Implemented behavior

`Repository(engine, clock=...)` owns short PostgreSQL transactions. Source records,
pending processing state and checkpoint advance commit together with source-level
serialization and checkpoint compare-and-swap. Exact source revisions are immutable;
changed revisions preserve record identity. Unreliable/future records are quarantined.

Explicit candidate family + provenance + fixture dataset maps to a persisted stable
event ID. Revision allocation, exact evidence associations, authorization grants and
notification outbox commit together. An unchanged decision creates no new version.
The source/external-ID candidate is not a place/time similarity match. AB retains
responsibility for deciding candidate grouping and conservative splitting.

Assessment first receives claimed records. For a previously persisted exact candidate
family, C reloads only evidence cited by its current version and may call AB once more.
Both calls share a 50-second deadline; the processing lease is 90 seconds. Total input
is bounded to 64 records/100,000 title+excerpt characters. Each final family's references
must belong to its server-selected family input. Captured event heads are rechecked
under locks before commit, and only actual claimed rows are completed. A changed head
causes a finite safe retry; an unexpected family change or oversized history fails
closed. No broad historical scan or process-local event history cache is used.

Corrections/withdrawals target prior intent recipients who remain configured and active.
Loss of an occurred assertion routes as a correction. Fixture content is available only
to provisioned test recipients, even for dry-run. Missing first-report policy suppresses
first/update notification intents. Chinese notification bodies carry separate assertion,
severity and evidence labels, original publishers and known publication times; reports
include stored source-backed metrics, cutoff and gaps without recomputing numbers.

Record/delivery claims use PostgreSQL `FOR UPDATE SKIP LOCKED`, bounded leases and unique
attempt tokens. Stale workers cannot write results. Expired processing work can retry
at most three times; expired `IN_FLIGHT` delivery becomes `UNKNOWN` and never automatically
returns to pending. Only classified known-safe delivery failures retry finitely.
`ACCEPTED`, `ACKED` and `DRY_RUN` remain different states. Callback uniqueness is durable;
current user/recipient/version authorization is checked again after D verification.
Replaying the same valid callback is idempotent; reusing it for another actor/delivery
is rejected. An old revision acknowledgement cannot suppress a newer revision.

Sessions are opaque random tokens stored as hashes, with current user role/active state,
expiry and revocation checked in the database. Login requires a consumed one-time state
bound to an HttpOnly browser cookie plus a trusted identity adapter. No arbitrary
code/header/user ID grants authentication. Mutations require a session CSRF token and
same-origin checks. Config/quote management is admin-only; config and feedback are audited.
Errors do not echo submitted credentials, raw callback/provider payloads or SQL values.

Quote previews are actor-bound, expire after 15 minutes, and persist validated AB parser
results. Import is transactional and idempotent for the same preview and repeated files,
including uploads rediscovered later. Binary float prices are rejected; PostgreSQL stores
Decimal values as `NUMERIC(20,6)`. Upload metadata/provenance comes from C; this local
runtime intentionally labels uploads as fixtures and cannot promote them to production.

Reports are unique by local date/timezone/provenance/dataset. Startup catches up only
today's due report, never all historical days. AB receives a cutoff snapshot and supplies
facts/metrics/stale-data gaps; C adds source coverage gaps and delayed-generation status.
The snapshot rejects overflow beyond 5,000 source revisions, 1,000 events or 5,000 quotes.
The current daily builder is fixture-only. Reminders are opt-in through audited business
config, snapshotted per revision, and limited to one after 30 minutes; acknowledgement,
revocation, a newer revision or disabling reminders suppresses them. SMS/phone remain off.

Daily runtime failure handling now records `report=degraded` with a stable error code
after a reservation fails, including timeouts and exhausted normal/model quota. Unexpected
exceptions become safe `invalid_output` errors without persisting their text. The existing
90-second lease remains in place; a busy/already-committed reservation is a no-op and does
not clear failure health or charge processing budget. Successful commit restores `ok`;
the existing status API exposes `degraded` and `stale` without promoting them to healthy.
Focused offline fault tests cover these runtime responses and current-business-day/UTC
cutoff selection; lease expiry, commit fencing and outbox uniqueness require E's independent
PostgreSQL checks. No storage transaction, scheduler, send gate or budget reserve changed.

Daily UTC request ledgers survive process restart: source buckets, processing calls,
model calls and production delivery units. Normal work cannot spend the urgent reserve.
Empty/no-op ticks do not charge processing/model budgets. If the optional history pass
exhausts quota after a claim, C clears its lease, restores the attempt count and defers
until the next UTC budget day. There is no immediate quota retry or unbudgeted call.
These are request counters, not verified provider token billing; real model/source calls
are disabled. Runtime health timestamps and durable state/budget counters are exposed.

## Constructor and entrypoint wiring for I

The C package imports no missing AB/D implementation. The following factory pattern
belongs to final integration; `records` must be explicitly supplied synthetic replay
records whose hashes satisfy AB's canonical record contract:

```python
from oil_agent.channels import DryRunChannel
from oil_agent.ingestion import ReplaySource, SafeQuoteParser
from oil_agent.intelligence import ConservativeAssessmentService
from oil_agent.reporting import SnapshotReportService
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.storage.database import create_db_engine
from oil_agent.storage.repository import Repository

def build_runtime(settings):
    repo = Repository(create_db_engine(settings))
    services = RuntimeServices(
        sources={"replay": ReplaySource(records, source_id="replay", clock=repo.clock)},
        assessment=ConservativeAssessmentService(clock=repo.clock),
        reports=SnapshotReportService(clock=repo.clock),
        quote_parser=SafeQuoteParser(),
        channels={"dry_run": DryRunChannel()},
        source_poll_seconds={"replay": 60},
    )
    return Runtime(repo, services, settings=settings)
```

Default conservative assessment has no reviewed urgent claims. Explicit reviewed claims,
trusted publisher policy and `matched_event_ids={(source_id, external_id): candidate_id}`
are trusted integration inputs, never decoded from source/model/client fields.
Inject the same services/settings into API and all worker processes. Set
`OIL_RUNTIME_FACTORY=your_integration_module:build_runtime`; the factory takes one
`Settings` argument and returns `Runtime`. Without it, C creates a database repository
with no external services; missing operations return explicit `not_implemented`.

After real identity verification and separate operator authorization, D's seams are:

```python
from oil_agent.channels import FeishuAckVerifier, FeishuChannel, FeishuIdentityAdapter

services.identity = FeishuIdentityAdapter(feishu_settings)
services.ack_verifier = FeishuAckVerifier(
    feishu_settings,
    identity_resolver=runtime.resolve_identity,
    delivery_matches=runtime.verify_delivery_message,
)
services.channels["feishu"] = FeishuChannel(
    feishu_settings,
    recipients=server_owned_recipient_mapping,
    authorize=runtime.authorize_recipient,
    public_base_url=settings.public_origin,
)
```

`authorize_recipient` accepts D's `RecipientAuthorization`; do not wire
`authorize_intent`, which is C's internal full-intent check. D identity is provider
`feishu`, subject `tenant_key:open_id`; C accepts only an active preprovisioned mapping.
Provisioning creates no session. Synthetic identity exists only in explicit tests.
Session challenge sets `oil_login`; session creation sets HttpOnly `oil_session` and
returns a CSRF token; use `X-CSRF-Token` for mutations. D callback verification and URL
challenge share a two-second service deadline. Accepted callbacks return `{}`, challenges
return `{"challenge": "..."}`. Provider response timing still needs real integration testing.

## Schema and operator commands

The sole mobile schema is `src/oil_agent/contracts/openapi.json`, OpenAPI 3.1.0,
API version 0.2.0, 16 paths. Regenerate with
`uv run --locked python -m oil_agent.api.export_openapi`; equality with the Python app
is tested. D must regenerate TypeScript after adopting C's contract changes.
Changes from foundation were coordinated: identity/session challenge, CSRF response,
trusted quote parse envelope, callback response, notification channel and runtime status.
No DTO/schema change was needed for T04, card body or quota deferral.

Routes under `/api/v1`: events/list/detail/ack/feedback, reports/list/detail,
quotes/preview/import, records/{id}/revisions/{revision}, config, status, session,
session/challenge and callbacks/ack. Health endpoints are `/healthz` and `/readyz`.
All business views require sessions; callback authenticity is delegated to D and then
validated against C state. Health proves liveness/readiness, not provider functionality.

Application migration head: `0002_runtime`. Run migrations explicitly before services;
API startup does not migrate or start workers. Queue schema is Procrastinate-owned and
installed explicitly, never duplicated as a custom queue.

```sh
uv sync --locked
uv run --locked python -m oil_agent.runtime.cli migrate
uv run --locked python -m oil_agent.runtime.cli queue-schema
uv run --locked python -m oil_agent.runtime.cli recover
uv run --locked python -m oil_agent.runtime.cli worker --queue ingest
uv run --locked python -m oil_agent.runtime.cli worker --queue urgent
uv run --locked python -m oil_agent.runtime.cli worker --queue normal
uv run --locked uvicorn oil_agent.bootstrap:create_app --factory --host 0.0.0.0 --port 8000
```

Inject `OIL_DATABASE_URL` as a secret using the `postgresql+psycopg` driver. `.env` files
are not loaded automatically. Each queue process runs concurrency one; `--once` drains
available jobs for local smoke. Jobs: `oil.ingest` on ingest, `oil.assess`/`oil.deliver`
on urgent, `oil.report`/`oil.deliver_report` on normal. Upstream one-minute periodic
ticks and explicit startup ticks recover business records/outbox even if enqueueing
was interrupted. Network/graphs never execute inside a long database transaction.

`provision-user --actor-id ... --recipient-id ... --provider ... --subject ... --role
viewer|admin [--test-recipient]` is an explicit trusted operator command. Revocation
and role maintenance are repository methods `revoke_user`/`set_role`, not public
self-service endpoints. No account is seeded. Secure cookies default on; an HTTP-only
local test needs explicit test settings. Production requires HTTPS and explicit gate
references for license, recipients, identity, credentials, policy, retention and budget;
those operator references do not establish real-world acceptance.

## Exact validation evidence

Environment: Python 3.13.13; uv 0.11.26; Docker Engine 29.5.3; PostgreSQL 16.14.
Locked installed distributions were rechecked in the runtime environment:

| Package | Version | Package | Version |
| --- | --- | --- | --- |
| fastapi | 0.141.1 | pydantic | 2.13.5 |
| pydantic-settings | 2.15.0 | uvicorn | 0.52.4 |
| sqlalchemy | 2.0.52 | alembic | 1.19.2 |
| psycopg | 3.3.5 | psycopg-pool | 3.3.1 |
| procrastinate | 3.9.0 | langgraph | 1.2.11 |
| httpx | 0.28.1 | openpyxl | 3.1.5 |
| cryptography | 49.0.0 | pytest | 9.1.1 |
| pytest-asyncio | 1.4.0 | ruff | 0.16.7 |

Only the existing isolated `oil-agent-c` container was started/used, bound to
`127.0.0.1:55431`, database/user `oil_c_test`, with synthetic throwaway credentials.
Tests create and remove uniquely named schemas within that database; other Docker
containers/databases were not changed. The container is stopped and retained at handoff.

| Command/check | Result |
| --- | --- |
| `uv sync --locked` | PASS, 74 resolved / 73 installed |
| `uv run --locked pytest tests/contracts tests/unit -q` | 69 passed, no skips, 19.94 seconds |
| `uv run --locked ruff check src tests` | PASS |
| `uv run --locked ruff format --check src tests` | PASS |
| `uv run --locked python -m oil_agent.api.export_openapi` | PASS, no final schema drift |
| `uv run --locked alembic current` | `0002_runtime (head)` |
| `uv run --locked alembic check` | PASS, no new operations |
| Runtime CLI migrate / queue-schema / recover | PASS; queue schema already installed; no pending recovery in base schema |
| Runtime CLI worker --queue ingest / urgent / normal --once | Each exited successfully |
| `uv build` | PASS, wheel and source archive |
| Actual Uvicorn factory, loopback 18081 | health/ready/OpenAPI 200; anonymous events 401; unconfigured identity challenge 501 |
| `git diff --check` | PASS |

The full test command explicitly sets `OIL_TEST_DATABASE_URL` to the C-only database
and `OIL_AB_PACKAGE_ROOT` to the accepted AB worktree's `src/oil_agent`, with
`PYTHONDONTWRITEBYTECODE=1`. Without the AB path, only its explicit handoff test skips;
without the database URL, PostgreSQL tests skip. Do not report such a run as the 69-test
acceptance above. The actual migration test starts from zero tables in a fresh schema
and runs both revisions plus Alembic drift checking; runtime tests use real PostgreSQL,
not SQLite. No heavy test suites ran in parallel.

Meaningful cases include rollback of checkpoint/outbox writes; concurrent SKIP LOCKED
claims; stale-worker fencing; expired send to UNKNOWN without retry; finite known-safe
failure retries; current role/revocation/CSRF and callback replay; correction recipient
scope; old ack isolation; actor-bound quote idempotency; per-revision reminders; durable
budget reserve/next-day deferral; report uniqueness; actual Procrastinate ingest ->
assess -> dry-run tasks; and urgent delivery while a normal report worker is blocked.
Each worker in that queue-isolation test has concurrency one. Actual AB LangGraph T04
upgrades the same persisted event from credible single source revision 1 to independent
multi-source revision 2 with both original publishers. It invokes no model.

One upstream Starlette/AnyIO deprecated alias warning remains; it was not suppressed.
The short-lived Uvicorn smoke process was stopped after the five endpoint checks.

## Remaining gates and limits

- E independently verifies scenario coverage, real API browser integration, Linux
  process death/restart behavior, full Compose build, backup/restore and remote CI.
  Windows selector-loop queue tests do not establish Linux shutdown acceptance.
- I owns the final branch merges and minimal factory/config/frontend glue. C provides
  injectable seams, not a hidden import of another worker's unmerged modules.
- Real source license/limits/transport, model/token billing, recipients, first-report
  policy, retention enforcement, provider credentials, Feishu SSO/app/tenant verification,
  authorized quote samples, deployment host, phone receipt, seven-day comparison and
  fourteen-day operation remain external gates. No such result is claimed here.
- Source/model enable flags stay closed; production references alone are not verified
  permission or a successful provider test. No SMS/phone implementation exists.
- Local daily reporting and quote upload intentionally remain fixture-only. Oversized
  assessment/report snapshots fail closed and require operator review; there is no
  silent truncation or automatic fuzzy family merging.
- UNKNOWN deliveries require explicit reconciliation; no reconciliation UI or unsafe
  automatic resend is supplied. Record failures after finite retries require review.
- Polling/recovery uses upstream one-minute ticks; no end-to-end latency SLA is claimed.
  Actual provider callback deadlines and network receipt must be independently checked.
- Procrastinate's upstream maintenance/Windows limitations recorded in the foundation
  handoff remain applicable; the pinned version and local tests do not remove them.

Modified path groups: `.env.example`; `src/oil_agent/{contracts,api,runtime,storage}/`;
`src/oil_agent/bootstrap.py`; `tests/unit/storage/`; and this `config/runtime-handoff.md`.
Run `git diff --name-only d31d8f9d410375dedb4727a3999ab56442c82df3 HEAD` for exact files.
