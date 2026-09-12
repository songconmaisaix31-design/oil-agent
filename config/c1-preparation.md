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
program. That product preparation entry has no database, sender, server or worker.
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
