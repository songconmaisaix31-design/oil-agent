# C1 local preparation receipt and construction contract

Application is NOT_CREATED / NOT_CONFIGURED. Display name 油品预警助手（测试）
and alias oil-agent-feishu-trial are labels only. No live binding, start trigger,
approval period, provider request, message, new paid product cost or phone result
has been generated. Product requests and cost remain zero.

## Actual local private preparation

Authorized directory: `C:/Users/DW/AppData/Local/oil-agent/private/feishu-c1`.
File: `config.json`, created exclusively after validating Windows ancestry and ACLs.
Only the current Windows user and SYSTEM have FullControl; new directories use
protected ACLs before any file is created. Existing unknown files, foreign owners,
reparse ancestors/files, hardlinks or broader access are rejected, not repaired.
No Git marker exists in its ancestors; this is the explicit LocalAppData location,
not an inferred sync folder. No other credential directories were searched.

The strict JSON has schema_version, display_name, alias, application_state and
five blank binding fields: app_id, app_secret, tenant_key, recipient_open_id,
host_binding. After actual app creation, change application_state to CREATED and
enter app_id/app_secret privately; leave unknown tenant_key, recipient_open_id and
host_binding null until their exact approved bindings are established. Keep the
schema and display labels unchanged. Never post the file contents into chat;
host_binding is an exact approved host label, never a command or URL to execute.
No start/approval timestamp is accepted by this preparation file. Blank fields
are JSON null, not invented IDs. A configured file is still unverified/unauthorized.

From the existing locked project environment:

```powershell
uv run --locked python -m oil_agent.runtime.c1_private prepare
uv run --locked python -m oil_agent.runtime.c1_private check
uv run --locked python -m oil_agent.runtime.c1_private inject-check
uv run --locked python -m oil_agent.runtime.c1_private preview
```

The module returns exit 2 while unconfigured or unauthorized; I independently
verified actual check/inject-check exit 2. Actual prepare/check/inject-check returned
WAITING_FOR_APPLICATION_CREATION, NOT_CREATED, NOT_CONFIGURED and field names only.
Prepare never overwrites. Inject-check maps only fixed OIL_C1 fields into one
foreground `python -I -m oil_agent.runtime.c1_product` process, discards ambient
OIL/Python/proxy configuration and never selects a private-supplied factory or
program. That product entry's default preparation mode has no database, sender,
server or worker; the explicit send-once mode below is a separately gated operation.
There is no dotenv loading or global environment change. The ACL subprocess uses
the fixed Windows system PowerShell and its built-in Security module; this avoids
inheriting an incompatible PowerShell 7 parent's module search path.

Actual offline artifacts in the same restricted directory: `c1-preview.html` and
`c1-preview.json`. The preview command uses D's fixed shared card renderer, accepts
no input path or code, and never overwrites existing artifacts. Creation reports
PREVIEW_CREATED_NOT_SENT; reuse reports PREVIEW_EXISTS_NOT_SENT. Its exit 0 means
local artifact preparation only, without any message or authorization. Open the
local HTML in a browser to inspect the exercise; it has no remote assets, actions
or callbacks. Its generated number/time identify a preview, never an approved start.

Checks: 16 focused preparation tests passed, scoped Ruff passed, ACL PowerShell
syntax passed, actual private prepare/check/isolated child injection passed their
expected NOT_CONFIGURED behavior. No Docker or live-service checks were run.

## Reproduced C1 coupling and minimum owner repair

Existing trial settings require identity and first-report/rule permission; normal
notification contracts only represent event/report and have no exercise kind.
EventAssessment requires source evidence and occurred/severity/rule facts.
Thus a standalone phone exercise cannot reuse an event first_report truthfully.
I reproduced forced rules/redirect/callback-secret construction separately, and
D reproduced mandatory detail/callback actions plus absent per-HTTP budget hook.

M authorized the smallest explicit exercise subject/kind through existing durable
Subject/Version/Authorization/Intent/Delivery tables. No generic notification
subsystem or second approval ledger is authorized. The future controlled sender
must retain exact recipient/revision scope, immutable approval, idempotency,
bounded attempts and UNKNOWN handling. Preparation/preview never starts that path.

D's pure `oil_agent.channels.create_c1_preview()` returns test_id, created_at,
msg_type, content and html; these are local preview metadata, not send timestamps
or authorization. D owns the offline `web/c1-preview.html` artifact and shared
card renderer. I owns final fixed assembly; C does not edit I bootstrap, factory
tests, environment example or runtime CLI factory seam.

Future user-triggered limits: first one message, at most three send attempts and
twenty total Feishu API requests (token/identity/send/query/retry included), zero
new fee, thirty minutes from the actual explicit start. All bindings and that
start remain missing. Production, OAuth, callbacks, monitoring, reports and
source/model execution are outside C1 preparation.

## Narrow runtime repair handoff

Internal C1Exercise / NotificationKind.EXERCISE / subject_type="exercise" represent
only the fixed labeled display exercise. HTTP endpoints and checked OpenAPI are
unchanged. C1Permission is a supplied actual start in the existing immutable
PermissionRow ledger, with one exact app/tenant/person/viewer/host, first message
one, <=3 send attempts, <=20 HTTP requests, zero new fee and <=30 minutes.
The private JSON helper cannot create this object or invent its timestamps.

I constructs Settings(c1_display_only=True, c1_permission=approved_start,
c1_host_binding=approved_host, data_provenance="fixture",
fixture_dataset="feishu-c1", outbound_mode="trial") and Runtime with only D's
C1 channel. It must not install identity/ack/source/assessment/report services or
start a queue/monitor for this path. D uses authorize=runtime.authorize_recipient
and authorize_request=runtime.authorize_c1_request. Its token and message HTTP
operations each reserve before the request; all share the same existing approval
budget, and message resends during token refresh also consume the three-send cap.

Only an explicitly initiated future foreground operation calls
await runtime.prepare_c1_exercise() then await runtime.send_c1_once(). Preparation
uses exact approved user provisioning without issuing a session; repeated
preparation creates one stable exercise/version/grant/intent/delivery per approval.
Every HTTP reservation rechecks the current user, immutable permission, exact
stored payload and active fenced attempt in the same short transaction as budget
reservation. ACCEPTED remains separate from phone observation and ACKED; callbacks
for exercises are rejected. UNKNOWN and expired in-flight rows never auto-requeue.
No source evidence, event assessment, first-report rules or OAuth approval is faked.

Focused database regressions: tests/unit/storage/test_c1_storage.py exercises
atomic rollback, concurrent idempotency, total/send budgets, revocation, expiry,
host/recipient changes, fencing, UNKNOWN and callback rejection. These require the
unchanged C PostgreSQL guard and were collected only in this no-Docker turn;
transaction acceptance remains unverified pending E's focused authorized run.
Runtime/control-flow and contract checks use synthetic in-memory doubles only.

## Explicit foreground execution connection

The integrated `41cfed431d8c8ac882d4cee88267cc20299b3c83` baseline had a working
C1 factory and durable runtime methods but no command connecting private loading
to them. A synthetic reproduction rejected both generic CLI `c1-send-once` and
private `send-once`, while fully configured `c1_product` still returned preparation
NOT_AUTHORIZED. Two initial entry regressions failed before the repair; the
original preparation assertions are preserved.

The only new command is:

```powershell
.\.venv\Scripts\python.exe -B -m oil_agent.runtime.c1_private send-once
```

It requires noninteractive structured stdin from the explicitly authorized local
foreground caller: one JSON object containing `permission` (the complete existing
C1Permission) and `database_url` (an explicitly approved PostgreSQL URL).
The transport is bounded to 32768 bytes, rejects duplicate/unknown fields and
creates no approval file or registry. Do not put credentials or this object in
command-line arguments, chat, Git or logs. The command never prompts for, invents
or renews a start. There is no currently authorized real invocation.

The caller must supply the already approved start trigger, immutable approval ID,
actual UTC valid_from/expires_at, existing budget/reference fields and exact
app/tenant/personal recipient/host binding. `CREATED` alone grants nothing. The
private configuration must match every supplied binding before any child or
database construction. Missing/expired/future/mismatched inputs fail closed.
The same approval ID and window must be reused on a permitted manual retry;
creating another ID to evade a limit or UNKNOWN outcome is not authorized.

The fixed child command is `python -I -B -m oil_agent.runtime.c1_product send-once`.
It receives only the existing fixed C1 environment allowlist and the same bounded
stdin data. It revalidates inputs and calls I's existing fixed
`oil_agent.bootstrap.build_runtime`, then the existing
`prepare_c1_exercise()` and `send_c1_once()` once, and disposes the engine.
No arbitrary factory, worker, recovery scan, queue setup, migrations, polling,
assessment, report, OAuth or callback work is started. Preparation commands and
their exit/status meanings are unchanged. I owns independent factory acceptance;
no I-owned file was edited by C.

Output is restricted to `status` and known `fields`, with only C1_ACCEPTED adding
`receipt`: actual `platform_message_id`, UTC `accepted_at`, actual Delivery
`attempt`, and `api_requests: null` (explicitly UNKNOWN). No entire Delivery,
permission, recipient or configuration is serialized. A missing/malformed child
receipt or timeout is C1_UNKNOWN, with no automatic retry. Actual request counts
are not measured by this entry: the existing durable request ledger must be
examined during approved execution, and reservations must not be equated with
received HTTP requests. Unknown usage is never reported as zero.

Exit 0 means C1_ACCEPTED only; it is not phone display or acknowledgment. Exit 3
means C1_UNKNOWN. Exit 2 covers denied/invalid/incomplete execution, safe failed
attempts and C1_NO_DELIVERY_CLAIMED. The latter cannot distinguish an existing
terminal delivery from an unavailable claim and does not assert a new send.
UNKNOWN/ACCEPTED re-entry uses the same existing outbox and cannot reset it.

Focused verification: 47 tests passed across `tests/unit/runtime/test_c1_execution.py`,
`test_c1_preparation.py` and `test_c1_runtime.py`, including the original preparation
tests and an actual isolated child with an expired synthetic permission.
No real private values, database or provider were used. I assembly/E acceptance,
the 11 previously collected PostgreSQL transaction regressions, real approved
bindings/start and platform/phone receipt remain separate pending gates.
