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
c1_app_request_permission=approved_app_window,
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

The explicit send command is:

```powershell
.\.venv\Scripts\python.exe -B -m oil_agent.runtime.c1_private send-once
```

It requires noninteractive structured stdin from the explicitly authorized local
foreground caller: one JSON object containing `permission` (the complete existing
C1Permission), `app_request_permission` (the shared C1AppRequestPermission) and
`database_url` (an explicitly approved PostgreSQL URL).
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

For send-once, exit 0 means C1_ACCEPTED only; it is not phone display or acknowledgment. Exit 3
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

## Pre-binding tenant read and shared app window

The accepted `fe4b76c2f8b1f17130bd442812cbc046eed1f325` sender required a complete
tenant/person permission and had no guarded lookup entry. Three initial synthetic
regressions failed: absent pre-binding DTO/entry and acceptance of a send scope
without a shared app owner. A fourth regression reproduced multiple first-message
identities for two full permissions within the same app window.

The required shared owner is `runtime.permissions.C1AppRequestPermission`, derived
from the existing RequestPermission. Fields are `approval_id`, `authorization_ref`,
`budget_ref`, `valid_from`, `expires_at`, `start_trigger` (the existing explicit
user-start literal), `provider` (feishu), `app_id`, `credentials_ref`, `host_binding`,
`max_requests` (1..20), `max_new_fee` (0), and optional `tenant_read_ref`.
There is no tenant or person field. Lookup requires a nonempty, explicitly supplied
`tenant_read_ref`; standalone send-only app scopes can omit it. The existing start
window remains at most 30 minutes and is never constructed or renewed by this code.

`C1Permission.app_request_approval_id` is now required. Its linked app owner must
match provider, app, credential reference, host, exact window/start, budget reference,
request cap and fee. Its own immutable approval ID remains distinct and requires
the exact tenant/person/viewer binding. Omitted or replaced app owners fail closed;
there is no old send-only request bucket fallback. Existing synthetic send fixtures
add the app owner/link; their original assertions remain, except the intentional
PermissionRow count increases from one to two (full recipient scope plus app owner).

All lookup token/query and later delivery token/send operations charge the **same**
app approval's existing BudgetRow scope and ProviderCallRow ledger. Full recipient
permission, stored revision/payload, active user/grant and fenced DeliveryClaim are
additional checks in the send transaction. Three message-send reservations at most
are counted under that same app owner. The unique exercise subject is derived from
the app owner; a different full scope cannot create a second first message for it.
Scopes and host are rechecked at reservation and before commit; immutable scope
revocation remains in PermissionRow. No new tables, migration or registry exist.
Prior rows are not rewritten: old unlinked inputs cannot execute via a legacy path.

The new explicit foreground command (not currently authorized for real execution):

```powershell
.\.venv\Scripts\python.exe -B -m oil_agent.runtime.c1_private tenant-lookup
```

Noninteractive, duplicate-free JSON stdin is limited to 32768 bytes and contains
only `app_request_permission` and `database_url` (`C1TenantLookupInput`). The fixed
private loader/ACL/handle/size checks remain unchanged. App ID, secret and host must
already be configured and match supplied scope; tenant and person are not required.
This command does not populate missing fields or infer host/start/read permission.
Its only child is `python -I -B -m oil_agent.runtime.c1_product tenant-lookup`, using
the existing environment allowlist. It never selects code from private data.

I glue: branch on `Settings.c1_tenant_lookup_only` before ordinary fixture/trial
assembly. C sets `outbound_mode="dry_run"`, `data_provenance="fixture"`,
`fixture_dataset="feishu-c1"`, `c1_host_binding`, `c1_app_request_permission`, and
`c1_permission=None`; all identity, source, model and send approvals stay absent.
Construct Runtime with `RuntimeServices(c1_tenant_lookup=...)` only, injecting D's
`FeishuTenantLookup(settings, authorize_request=runtime.authorize_c1_app_request)`.
The callback is async `(operation: str) -> str`, accepts exactly `tenant_token` /
`tenant_query`, and returns the committed reservation identifier. D's lookup method
is keyword-only `lookup(*, context: CallContext) -> str`; C calls it through bounded
`Runtime.lookup_c1_tenant() -> str`. Runtime installs repository app/read providers
internally. The fixed product factory remains `oil_agent.bootstrap.build_runtime`.
I owns that glue; this C increment imports no missing D implementation.

Query output is only fixed status/known field names. `C1_TENANT_LOOKUP_COMPLETED`
(exit 0) means the injected lookup returned a well-formed tenant in memory; it is
not sending, user authentication, rotation verification or identity/host approval.
The identifier is never output or automatically written to private configuration.
Lost/malformed/ambiguous results are C1_UNKNOWN (exit 3), with no automatic retry.
The engine is disposed after the one bounded foreground flow. Preparation check
and inject-check retain their original behavior and never request a token.

Durable reservations can be counted by the shared approval in ProviderCallRow;
they do not prove actual remote arrivals. The foreground result does not measure
arrival counts; those remain unknown, never zero by inference. Send receipt
`api_requests` remains null. This local development increment makes zero product
calls and reads/writes no real private configuration.

Focused tests cover schema/link/window/caps, changed construction scope, disabled
ordinary paths, keyword-only D handoff, strict input, isolated expired subprocesses,
redacted output and no retry. `tests/unit/storage/test_c1_storage.py` adds real-PG
cases for query-to-send shared quota, revoked/replaced scope, reservation rollback,
concurrent cap enforcement and unique first-message scope. In this no-database
turn these PostgreSQL cases are collected only; actual transaction/concurrency
acceptance remains a separate E gate. I factory integration, E acceptance, approved
real bindings and a new explicit unexpired start/read scope remain outstanding;
the prior expired window is not reopened and production is not accepted.

Core increment evidence (`1a699c7713ea4c62b5cd81b4e47e1c6909064042`): the four initial regression failures were repaired;
115 focused runtime/contract/preparation tests passed, scoped Ruff passed, and
21 PostgreSQL cases were collected without execution. No full suite, dependency
installation, database connection/start, container action or real request occurred.

## Explicit selected-result binding

The core read probe discarded its result and could not map a technical tenant
field. The coordinator authorized this separate correction after a regression
confirmed that the explicit binding command returned INVALID_COMMAND:

```powershell
.\.venv\Scripts\python.exe -B -m oil_agent.runtime.c1_private tenant-lookup --bind-if-unset
```

This opt-in uses the identical supplied C1TenantLookupInput and permission/budget
gates. It grants no new API permission, does not create a start, and is not invoked
against any real configuration during development. Without the flag, the original
status-only lookup still makes no local binding change.

Only the captured fixed child receives the internal `--selected-result` switch.
`C1TenantLookupResult` carries the constrained `tenant_key` and original shared
app request permission over that existing captured pipe. It is forbidden on a
terminal stdout, rejected without the parent opt-in, and never forwarded to
ordinary output. The parent validates the exact original app scope, known keys and
success status before considering a local update; malformed/mismatched results
remain UNKNOWN and cannot write anything.

`bind_selected_tenant` revalidates the app/host/window against the initial private
configuration, reruns the existing fixed ACL/path check, and opens only the existing
config with an exclusive Windows handle and OPEN_REPARSE_POINT. Regular-file,
single-link, reparse and 16KB guards apply. The current structured config must still
equal the one loaded before the query; changed app, secret, host or binding fields
fail closed. ACL and expiry checks repeat before writing. A matching existing tenant
is a no-op; a conflicting nonempty tenant is preserved.

Only the blank/missing tenant member is replaced/inserted; all other bytes and
formatting are preserved. The resulting document is validated before writing,
flushed and read back through the same handle, with a final ACL check. No backup,
receipt, permission file, global environment mutation or secondary registry is
created. Ordinary output is only fixed status and known field names:

- C1_TENANT_BOUND / C1_TENANT_ALREADY_BOUND (exit 0): selected local mapping succeeded;
  these are not recipient authentication, platform sending or phone observation.
- C1_LOOKUP_COMPLETED_BINDING_FAILED (exit 2): the read completed but local binding
  failed or is unconfirmed. Never blindly requery. Check the local file offline
  first: an I/O or final-validation failure after writing does not prove unchanged
  bytes. In-place writes without new files cannot guarantee crash-atomic replacement.
- C1_UNKNOWN (exit 3): the child result cannot establish a trusted completed lookup.
  No automatic retry or field update follows.

Delta evidence: one initial binding regression failed then passed; 75 focused
entry/preparation tests passed, including 19 Windows-only temporary synthetic-file
binding cases. Tests cover exact field preservation, missing member, same-value
no-op, changed config, nonempty conflict, scope mismatch, expiry, hardlinks, file
size, exclusive access, I/O uncertainty, selected-result validation and no requery.
The ACL verifier is doubled in those file tests: this is not real private ACL or
credential/tenant acceptance. Scoped Ruff passes. Real private values were never
read or changed and real product requests remain zero. I assembly, E independent
acceptance, actual PostgreSQL tests and a new explicitly authorized real window
remain required before any real use of this implemented path.

## Dedicated Windows C1 database entry

`python -I -B -m oil_agent.runtime.c1_database ACTION` is a project-local
foreground helper. Run from the reviewed source worktree's existing editable
locked environment, for example with `uv run --offline --locked --no-sync`.
It uses only that source tree's `deploy/compose.c1-db.yaml`, supplied by E;
the general controlled-trial Compose files and validator remain unchanged.
This implementation does not authorize deployment or a phone-test start.

All actions require one noninteractive JSON object on stdin (maximum 8192 UTF-8
bytes); duplicate/unknown keys, malformed values and control characters in the
password are rejected. An authorized caller supplies values transiently, never
through command-line secrets, an executed dotenv file, a new private file or
the global environment. Do not paste credential-bearing JSON into a terminal
command or public handoff. Field names and fixed scope are:

| Field | Required value / meaning |
| --- | --- |
| `host_binding` | Already confirmed `LAPTOP-BS46UHBR`, matching the actual Windows host |
| `worktree` | Exact reviewed source worktree containing this helper and Compose file |
| `project`, `service` | `oil-agent-feishu-trial`, `postgres` |
| `database`, `username` | Both `oil_c1_trial` |
| `volume`, `network` | Compose keys `c1-data`, `backend` |
| `port` | Integer `55436`; the only binding is `127.0.0.1:55436:5432` |
| `password` | Explicitly supplied database password, 1–512 characters, no control characters |
| `container_id` | Null/omitted for `check` or `start`; exact full inspected ID for retained actions |

The proposed resource names are not evidence that these resources exist or are
approved for activation. This database is distinct from E's synthetic test
database and its disposable schemas. The same persistent C1 database must later
serve tenant lookup and sending, preserving their shared budget ledger.

| Action | Behavior |
| --- | --- |
| `check` | Bounded safe YAML read and captured fixed Compose config rendering; no resource mutations or database connection |
| `start` | Requires candidate project/container/volume/network scope absent; runs only `postgres` with no dependencies, build, pull or recreation, then verifies the result |
| `status` | Checks the supplied full container ID, project/service/worktree/image/volume/network/port and current state; read-only |
| `migrate` | Requires the exact running healthy container; invokes only the existing isolated `runtime.cli migrate` child |
| `stop` | Stops only the verified full container ID, retaining its volume, network and container; an already exited container is a no-op |
| `resume` | Starts only that verified retained ID without Compose recreation; an already running container is a no-op |

Resource operations target the fixed local Docker Desktop Linux named pipe,
not an ambient remote Docker context. The Compose child receives only necessary
Windows process fields, `COMPOSE_DISABLE_ENV_FILE=1` and `OIL_C1_DB_PASSWORD`.
Docker also receives only `ProgramFiles` for its installed Windows Compose
plugin discovery; no user-profile, PATH, Docker context or credential environment
is inherited. The migration child does not need that additional field.
The source must use the literal placeholder
`${OIL_C1_DB_PASSWORD:?Explicit C1 database password required}`. The bounded YAML
reader uses PyYAML already present in the locked dependency graph and rejects
includes, env files, builds, hooks and additional services before Compose runs.
Rendered configuration must retain the pinned PostgreSQL 16 image and resource
bounds, sole named volume and internal backend network.

Inspect/start/stop children do not inherit provider credentials, proxy settings,
Python injection or other product flags. The separate migration child receives
the fixed loopback DSN through `OIL_DATABASE_URL`, with `environment=test`,
`data_provenance=fixture`, `fixture_dataset=feishu-c1`, and `outbound_mode=dry_run`;
other capabilities retain safe defaults. The password is URL-encoded when
constructing the DSN. Migration applies only application Alembic head: no queue
schema, recovery, worker, API, OAuth session or sender is started. Later C1
execution takes the same DSN through its existing bounded structured stdin,
not through changes to the app/host/recipient private configuration.

Existing resources require both the supplied full container ID and fresh exact
scope checks, repeated before effects. Foreign/partial scopes, password
conflicts, extra consumers or altered bindings fail closed. No resource is
adopted, removed, recreated or repaired; no volume data or password is reset.
Normal Docker inspection by the authorized owner supplies the retained ID;
the helper's ordinary output never dumps IDs, environment, passwords or DSNs.

Output contains only `status` and `fields`. Exit 0 covers config verification,
observed running/exited states, start or migration completion; it does not prove
application/phone acceptance. A running result with `fields=["health"]` is not
yet ready for migration. Exit 2 means invalid input or failed pre-effect checks;
exit 3 / `C1_DB_EFFECT_UNKNOWN` means a failed command or post-effect verification
may have left changed persistent state. Do not retry blindly or infer rollback.
Compose is not an atomic compare-and-create API: out-of-band Docker changes and
partial starts require exact independent inspection, not automatic cleanup.

Preparation evidence is bounded unit testing with synthetic subprocess/inspect
doubles, including allowed commands, isolated child environments, redaction,
foreign/changed scopes, missing retained IDs, no-effect checks and preserved
resources after failure. No real C1 Docker resource, password, database or phone
window was used. E's Compose integration and actual Windows loopback reachability
remain separate acceptance gates; internal-only networking must not be silently
expanded to obtain a passing check.

The exact E candidate `1ab32ce5fe774a434d3a63254124723fc77f02bc` was compared
with its Git blob and passed actual captured Compose rendering plus this helper's
`check` at 2026-09-12T12:55:29Z using a synthetic password only. No resource
inspection/mutation command was run. The actual renderer revealed the required
Windows `ProgramFiles` discovery field and generated null `entrypoint` / empty
`ipam` metadata; these default representations are accepted without permitting
an entrypoint override or custom IPAM. Fixed fixture labels, IPv6-disabled
internal networking, restart `no` and bounded local logs match that E candidate.
This is configuration-only evidence, not running Docker/Windows DB reachability.
I must declare the already locked `PyYAML>=6.0.3,<7` as a direct runtime
dependency; the current resolved version is 6.0.3 and no package upgrade is needed.
