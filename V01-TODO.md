# V01 delivery board

## Current phase: controlled real integration

### Active bounded development: C1 PostgreSQL test adapter

The user's new multi-agent development instruction resumes the existing C/E/I
sessions on the accepted delivery `f04f64f55cc12e7fea4cfa5d56ee768816bad561`.
It does not start a phone window or authorize provider calls. The concrete
implementation gap was the recorded mismatch between C's database-only fixture
and E's isolated migrated PostgreSQL fixture. E has implemented the adapter;
21 current C1 SQL cases still remain unexecuted through the E harness.

| Owner | Bounded work and exclusive edits | Acceptance / next owner |
| --- | --- | --- |
| E | Reproduce the fixture-selection blocker and add the smallest adapter under `tests/integration/`, reusing the original C1 assertions and E's existing migrated fixture. Record evidence only in existing `e2e/runtime-checks.md`. | Exact collection and fixture routing, applicable lint and targeted tests. Actual SQL only on independently confirmed E-owned resources; missing engine remains a separate execution gap. |
| C | Read-only review of the 21 existing storage assertions, clock/config initialization and database ownership requirements; return a precise contract handoff to E through M. Domain fixes require a reproduced failure and a separate owner assignment. | Preserve original assertions and C database guards; no repository or private-configuration edits in this task. |
| I | After the E commit, integrate only this adapter/evidence and M governance on the existing integration branch. | Check exact source changes and applicable targeted checks; hand the final candidate to E for independent delivery review. |
| M | Maintain this board and dispatch/acceptance records only. | Retain all sessions; AB/D have no task in this increment. |

The existing Run is `run_64e3991f76b9`. E is executing
`task_7c47961827c9` / `ctx_6e13f25bb2a2` in `oil-v01-e`; C completed
`task_505e05b63fc7` / `ctx_a1ab0dd1210a` in `oil-v01-c`. Both original
terminals were reused and actual task activity was observed. I remains retained
until the owner commit is ready; no new worker, branch or worktree was created.
C's read-only handoff confirmed 12 original functions expanding to 21 cases,
shared function-scoped repository routing, assignable frozen UTC clock and
independent transactional sessions. E's real migrations already insert the
default configuration; the adapter must not insert it twice or create sessions
through `e_actors`. No domain defect or SQL execution was claimed. C is retained.

E's implementation commit is `a76571dcf2f8b2b276d72e527a06c78d08fc4a18`.
It adds only `tests/integration/test_postgres_c1.py` and updates the existing
runtime evidence. Before repair the original C fixture rejected E scope with
one setup error and zero engine constructions. The adapter now collects all
21 cases, preserves original callable/fixture/parameter identities, and routes
only its module to E's existing migrated repository. Ruff and the effective
fixture-routing audit passed. Missing E configuration produced 21 explicit
skips, not SQL passes; wrong database scope still failed before connecting.
Original tests, both existing fixtures, product sources and locks are unchanged.
One exact E container inspection failed because `dockerDesktopLinuxEngine` is
absent. No retry or resource mutation followed. This resolves the missing
adapter implementation only; actual SQL, live C1 database permission and all
Feishu/phone acceptance remain unexecuted. I integration and E final delivery
review are the next steps for this exact increment.

Do not rerun full synthetic acceptance, change product code or production flags,
read private credentials, start Docker, restart shared services or clean old
resources. E may make one bounded read-only check of its previously identified
container to determine whether the targeted SQL tests can run; a mismatch or
unavailable engine ends that environment action without retry or substitution.
Any SQL execution must retain fixture provenance and use only newly created
E-owned disposable schemas, never the future live C1 database. Commit/push only
verified changes to the existing origin; use `[skip ci]` to avoid an unrelated
full-suite replay. Report harness checks separately from actual PostgreSQL and
Feishu evidence. Production factory work remains outside this increment.

### Active C1: local code accepted; phone test not executed

The user reopened the official API Explorer and supplied one exact `open_id`
for the self-binding step. At 11:26 UTC on 2026-09-12, D reverified the Explorer
application against the protected local configuration, selected `open_id` in
the existing member picker and copied the sole candidate through its UI.
The copied value matched the user's exact input in memory and passed the ID
format check; the native clipboard sequence was stable during the bounded
read. No identity value or comparison digest is recorded in repository files.
This resolves the earlier browser and candidate-identity prerequisites below.
It proves a user-confirmed local binding input, not product login, a signed
identity receipt, token authentication, message acceptance or phone display.
At 11:29:39 UTC, C completed the existing private configuration's null-only
`recipient_open_id` mapping using source
`e690b61358e4216dfca574a6d58b9c9251edaf0d`, whose relevant executable inputs
match integrated `3c7ee50383235587063fe938fc7d27fe50d90783`. C reported real
path/owner/ACL, exclusive handle, single-link/non-reparse, bounded strict schema,
approved host and exact copied-identity checks passed. Only the recipient field
changed; other field bytes, formatting, file identity and owner/group/DACL were
preserved according to C's before/after checks. No repository code changed.
The existing `check` and `inject-check` each returned expected exit 2 with empty
stderr, `CREATED`, `NOT_CONFIGURED`, missing only `tenant_key`, and
`NOT_AUTHORIZED`. Actual isolated child injection succeeded.
At 11:34 UTC, E independently verified the actual protected file, strict schema,
approved host, nonempty application fields and exact recipient match. Effective
directory/file access is limited to the current user and SYSTEM; the directory
has inheritance disabled, and the file inherits that restricted access. E ran
each existing helper mode once with the real isolated child and obtained the
same expected exit 2, missing-only-`tenant_key` and `NOT_AUTHORIZED` result.
The configuration bytes and file identity were unchanged across E's own checks.
C's preservation of the original pre-write bytes remains C-reported evidence.
Acceptance is **REAL LOCAL RECIPIENT CONFIGURATION / LOADING ONLY**; no phone
window, token acquisition or product call was started. UI background counts
remain unknown, and no platform/phone/login/callback acceptance is implied.

At 10:59 UTC on 2026-09-12, D's computer-use self-binding attempt ended
without copying an identity or modifying private configuration. After the Orca
runtime restarted, M rebound the existing Run and resumed the same D Task in
its original worktree. D's fresh desktop discovery found no external browser;
`orca computer list-windows --app Tabbit --json` returned `app_not_found`.
The explicitly authorized attempt to open the official API Explorer with the
existing Windows HTTPS handler was rejected before execution by automatic
approval review, with only `blocked by policy` as its reason. This is a local
execution restriction, not missing application credentials or a product-code
defect. No alternate shell or browser API was used to evade the rejection.

The prior browser URL/application match is historical and was not reverified
after the restart. Exact self selection, clipboard copy and C's recipient
mapping remain **NOT EXECUTED**. The immediate manual prerequisite is to open
the existing browser at `https://open.feishu.cn/api-explorer`; D can then resume
the approved current-application/self-only UI step. Existing bot/self-only
availability and host confirmations remain accepted, without another scope
question. No message, token acquisition, source/model call or new phone window
was initiated. Browser background request counts remain **UNKNOWN**; these
observations do not establish compliance with the twenty-request live budget.
No paid service was added; development-session cost is not available from the
product ledger. D's source remains `da65fb1f2f80a455c058e3107a3df3964c22fbd5`;
the integrated product source remains `9dfd0a54063b1b9c909d6dd322bbfb23567e27a3`.
This increment records the attempted real setup and its limitation only;
no code fix, repeated mock acceptance, database/service change or container
operation is warranted by this observation. D's session and work are retained.

At 10:31 UTC on 2026-09-12, the user confirmed that the existing application's
bot is enabled and its availability is restricted to the user alone. Record
both facts as **USER CONFIRMED**; do not ask for that scope again. This is not
independent platform verification, an exact application-scoped `recipient_open_id`
binding, verification of the send API permission/version release, or a new phone
test start. D owns guidance for the next exact self-binding step; private values
remain local, and tenant/database technical mapping stays with the agents.

On 2026-09-12, the user confirmed the current `LAPTOP-BS46UHBR` computer as
the test host. M recorded that confirmation at 10:12 UTC. C completed the
existing protected configuration's null-only `host_binding` maintenance and
reported it at 10:14:56 UTC, using accepted source
`e690b61358e4216dfca574a6d58b9c9251edaf0d` without repository code changes.
The confirmation answered a host-only question that explicitly excluded
sending; it does not renew the expired phone window. C reported real path/owner/
ACL, exclusive-handle, bounded schema and readback checks passed; only
`host_binding` changed, with all other field bytes, formatting and ACL preserved.
The existing `check` and `inject-check` each returned exit 2 as intended, with
`CREATED`, `NOT_CONFIGURED`, missing `tenant_key` and `recipient_open_id`, and
`NOT_AUTHORIZED`. Actual isolated process injection succeeded. E independently
verified the real post-state, schema, approved host match and both helper modes;
its checks preserved the configuration bytes and emitted no stderr. Effective
file access is limited to the current user and SYSTEM. The file inherits from
the restricted project-private directory, whose ACL inheritance is disabled.
Unchanged pre-state across C's maintenance remains C's reported evidence.
E's independent local evidence is committed in
`d35a7fc192db05fb134a1459ce13d6748732f3c6` (`e2e/runtime-checks.md`).

E's final independent disposition is **LOCAL CODE / TEST / SELECTED PACKAGE
EVIDENCE ONLY**, recorded in `d4d1225811fd44f6fc7c39259beaabc85ab0e144`.
Tested I delivery is `bfe0209f882f2ffb92fcfc4ab1f651e4541a36cd`; exact clean
code/test/build source is `e98d4a69a2e317b8f573f1c868571dd66fccd1e3`.
I and E independently passed the 65 entry/offline-factory cases and 19 Windows
temporary-file binding cases. Thirteen PostgreSQL factory cases were
deliberately unselected, no selected case was skipped, and the existing AnyIO
deprecation warning remains. The binding cases mock ACL verification and are
not real protected-file write evidence. No original assertion was weakened.

Verified commands (existing dependencies, no network installation):

```powershell
uv run --offline --locked --no-sync pytest tests/integration/test_c1_entry.py tests/integration/test_bootstrap_factory.py -k 'c1_entry or offline_factory' -q --tb=short
uv run --offline --locked --no-sync pytest tests/unit/runtime/test_c1_tenant_binding.py -q --tb=short
uv build --offline --out-dir C:/Users/DW/AppData/Local/Temp/oil-agent-i-ctx-8394797ac280/dist
```

I performed the build once, from the exact source above. E read eight selected
runtime/channel/factory members in each existing wheel and source archive,
without extraction or modification: 16/16 matched after LF normalization,
0/16 matched raw Git bytes because the archived files use CRLF. This is selected
source/package correspondence, not raw-byte identity or installed acceptance.
Post-build delivery changes are evidence/handoff documentation only. All
verified increments were pushed to the original branches; sessions are retained.

The implemented path now includes fixed app-only tenant transport, one shared
window request budget for lookup and later sending, one first-message subject,
an isolated fixed product entry, and explicit null-only private tenant mapping.
The earlier code-acceptance round changed no private configuration. The new
host-only maintenance above supersedes that local observation; no token
authentication or platform/phone effect is inferred.

Remaining gaps stay separate:

- **NOT IMPLEMENTED:** the production factory before formal delivery.
  Production is not a C1 prerequisite. The narrow E-owned C1 SQL adapter is now
  implemented in the bounded increment above; its actual SQL execution remains
  a separate unverified item.
- **IMPLEMENTED, VERIFICATION NOT EXECUTED:** 21 C1 SQL cases, real tenant-result
  mapping, platform acceptance and phone display. The exact Docker engine pipe
  is unavailable; no shared service restart or unknown-resource action occurred.
- **MISSING CONFIRMED SCOPE / CONFIGURATION:** tenant binding,
  required platform permissions and an approved isolated database. The current
  test host is now explicitly confirmed, locally mapped by C and checked by E.
  Bot enablement and self-only application availability are user-confirmed;
  the exact recipient is now user-confirmed, UI-copied and locally mapped by C.
  E has independently verified the actual recipient post-state and loading;
  platform API permission remains unverified.
  The prior phone window expired; a new explicit start is still required.
- **EVIDENCE LIMIT:** the receipt's live API count remains `null` / unknown;
  durable reservations are not proof of remote arrival. Report these separately.
  In-place write failure may leave modified/unconfirmed bytes, without automatic
  requery or a crash-atomicity claim.

Actual product source/model/Feishu calls, sends and model tokens this round are
zero; no paid service was added. Development-session billing is not available
from the product ledger. No source record, platform message ID, phone observation,
web login, callback or signed confirmation receipt exists for this round.
No business service, continuous monitoring or new test window was started.

The user reports having obtained application credentials and has edited the
project-private configuration locally. C's earlier read-only check on
2026-09-12 at 09:31 UTC, against integrated
`fe4b76c2f8b1f17130bd442812cbc046eed1f325`, passed JSON/schema, path/ACL and actual
isolated process injection checks. The existing `app_id` already matches the
user-supplied identifier: no private file was written or created. Its redacted
state is `CREATED`, `NOT_CONFIGURED`, missing `tenant_key`,
`recipient_open_id` and `host_binding`, with start `NOT_AUTHORIZED`.
Both helper commands returned exit 2
as designed for incomplete preparation. This proves local loading only, not
platform authentication, credential rotation, application ownership or binding.
No private value is recorded here. The display name remains
`油品预警助手（测试）`; local alias remains `oil-agent-feishu-trial`. These are
labels, not platform identities. Unconfirmed bindings must not be inferred.

C1 covers one approved personal test recipient, platform acceptance and physical
phone display only. Web login, interactive callback, real news/model and
production acceptance are excluded. This turn explicitly authorizes local
preparation, not messages or provider requests. No application creation or
existing host/identity is inferred from the labels.

C owns reuse/check of the existing project-private mechanism. If none exists,
the user permits a new no-overwrite blank configuration under the resolved
`C:\Users\DW\AppData\Local\oil-agent\private\feishu-c1` path, outside Git.
Check Windows access controls; do not scan other projects or credentials, expose
file contents, invent identifiers or modify global environment. Reuse structured
loading; if missing, implement only a project-local helper in C runtime paths
which parses data without executing it and injects allowlisted fields into the
one intended process. Missing-field output contains field names and unconfigured
status only. Blank readiness must say waiting for application creation.

D prepares a local, non-sending preview using the approved Chinese text below,
with system-generated test number/time and prominent exercise/non-real-market
label. No login/confirmation buttons or inactive links. Reproduce any C1 blocker
in the existing channel/runtime path, then return domain fixes to D/C and factory
glue to I. Preserve exact authorization, durable delivery/deduplication/budgets;
never add a raw-provider sender which bypasses the product path.

> 【油品预警 Agent｜演练消息】
> 本条消息用于验证飞书推送与手机显示，
> 不代表真实市场事件，不构成采购或交易建议。
> 测试编号和发送时间由系统生成。
> 本阶段只验证消息到达。

Future execution additionally requires local confirmation of the exact app,
personal identity and existing test host, then the user's explicit
`开始手机测试` trigger. Record that start; authorization ends after 30 minutes.
First send is one message; at most three send attempts and twenty total Feishu
API requests, including token/identity/send/query/retry, in that one window.
New paid cost ceiling is zero; unknown coverage stops execution. UNKNOWN sends
require investigation before any resend. No automatic next window, ongoing
monitoring, source/model calls, reports, repeat alerts, purchases, public ingress,
shared Docker restart or unknown-resource cleanup. Phone feedback is not a
signed callback. Record actual version, aliases, counts, message ID/time and
phone observation separately; login/interaction receipts remain NOT EXECUTED.

The user subsequently sent `开始手机测试` directly to the retained D session.
M verified the exact user message in Orca's structured transcript (message
`01a094c8-fd4d-78a3-9c36-3fab5186f263`): its timestamp is
2026-09-12T08:43:15.149Z, so the conservative thirty-minute limit is
2026-09-12T09:13:15.149Z (17:13:15 Asia/Shanghai). D's later processing observation
at 08:43:24Z does not extend that limit. This trigger supplies no missing app,
person, host or database binding and created no executable permission record.
D's redacted check through the committed C helper still reported `CREATED` /
`NOT_CONFIGURED`, missing `app_id`, `tenant_key`, `recipient_open_id` and
`host_binding`, with zero product requests. An earlier path/ACL denial from D's
older helper context did not reproduce with C's helper; no ACL or private file
was changed. No message was attempted and the window must not renew silently.
M checked the clock at 09:25 UTC: that window has expired. The user's subsequent
instruction to continue development does not authorize a replacement window.

The current bounded increment addresses the reproduced pre-binding tenant-query
gap, not new product features. C task `task_9f68896111b5` / `ctx_1e8f29b67faa`
completed the App ID comparison and two redacted checks without writes or calls.
D task `task_1633a8eef6b0` / `ctx_e8b25d459470` reproduced the missing fixed tenant
lookup transport; C confirmed that the full C1 permission and active delivery
claim currently require bindings which this lookup must obtain first. D owns the
fixed token/query transport, C the existing permission and request-ledger seam,
and I task `task_d068a6cef6c0` / `ctx_9fd45f0998ab` the narrow assembly review.
One immutable app-window request budget must cover lookup and later sending;
tenant discovery never supplies recipient authorization or resets twenty calls.
E task `task_14da0342346c` / `ctx_c02dde905576` checks only exact previously
identified E-owned PostgreSQL test resources before proposing targeted execution
of the eleven pending C1 storage regressions. No shared service restart, unknown
resource operation or live test-host approval is inferred.

C continues the bounded owner repair in task `task_8d50445f6a5e` /
`ctx_14b98dc95b3f`. The immutable app request owner must be explicitly linked to
the complete send permission; omitting or replacing it after lookup must not
reset the request or three-send counters. Existing recipient/revision/lease
checks remain in the same send-reservation transaction. I's read-only design
review is complete and its session is retained pending exact owner commits.

E recorded its actual resource observation in
`a9264158e5ec64983f700d8c0a68373fff7f5be8`: the configured local Docker endpoint
was readable, but one exact E container inspection failed because
`dockerDesktopLinuxEngine` was absent. No current container/volume/cleanup state
was verified and no service was started, restarted or cleaned up. The eleven
C1 SQL cases remain **IMPLEMENTED, VERIFICATION NOT EXECUTED**. Their existing C
fixture rejects E's database; reusing those assertions on E's own database needs
a narrow E-owned fixture adapter, **NOT IMPLEMENTED**. That harness gap and the
unavailable engine are separate from missing live provider authorization.

D delivered `da65fb1f2f80a455c058e3107a3df3964c22fbd5` on its existing branch:
fixed app-only `FeishuTenantLookup` reuses the token/HTTP implementation, requires
a nonempty reservation before each token/query wire request, validates the
response-derived tenant identity and never retries automatically. The initial
missing-export assertion failed; the new lookup selection passed 34 and related
existing channel checks passed 36, with original assertions retained. These are
synthetic transport checks, not platform authentication. I task
`task_8fb163cd7182` / `ctx_98d0b0ec61f9` integrates that exact increment and the
governance/E evidence first; C's shared-budget and entry repair remains separate
work in progress. No current provider request, send or added product cost exists.

E independently accepted D transport only at I
`d4414f9a3b24dc104e2f622ee0391f4ac811811a`, recorded in
`5aa4219fd09473e7ab6f645289e00de0fde3ec85`. The same 34 new and 36 related original
checks passed offline, with 56 deliberately unselected and no skips; these
repeat checks are not an additive test total. E verified original channel test
files and ordinary guards unchanged. Shared C runtime, SQL and live platform
acceptance are outside that result.

During the C repair, a focused regression reproduced that separate full send
approvals sharing one app window could create separate first-message subjects.
C owns the minimal correction in the existing exercise/outbox identity, without
new tables or historical data mutation. M also reproduced a selected-result
handoff gap: the new read probe discarded the returned tenant before private
configuration mapping. C is authorized to repair this with an explicit option
in the existing controlled entry and a checked parent update of only a blank
`tenant_key`. The default probe remains non-writing; an equal value is a no-op,
conflicting nonempty values or changed bindings are refused, and ordinary output
stays redacted. This authorizes code and synthetic tests only: no real query,
private update, new file, start window or recipient is authorized here. Both
repairs need committed owner evidence, I integration and independent E review.

C delivered core `1a699c7713ea4c62b5cd81b4e47e1c6909064042` and mapping delta
`3dd8cb43c19fac00a6d1099baa4a8f28f3d63671`, both pushed on its existing branch.
Core checks passed 115 after three initial missing-seam failures and one
shared-first-message identity failure. The existing C storage selection now
collects 21 cases, including the original eleven: **none were executed**.
Mapping checks passed 75, including 19 Windows temporary synthetic-file cases
with a mocked ACL verifier; the initial explicit-option regression failed before
repair. Scoped Ruff and diff checks passed. The selections overlap and are not
an additive acceptance total. `tenant-lookup --bind-if-unset` is now implemented;
the prior result-to-private-binding implementation gap is superseded, with real
protected-file/platform verification still pending. In-place I/O failure can
leave modified or unconfirmed bytes; the code reports binding failure and does
not claim crash-atomic writes or retry the lookup automatically.

I integrated the core in `775308f7ded755da410044f8634b2e5f11a6ff23` and delivered
its three-path fixed-factory glue in
`d842b7b43c2f6ed91198a3e3695650db3b2a8cfe`. The new regression first reached the
ordinary fixture factory; the repaired query branch passed 20 offline factory
checks, with 13 PostgreSQL cases unselected and all sixteen original factory
test function ASTs unchanged. E task `task_a8f43e8d111d` / `ctx_65f739b1af73`
reproduced 26 original-entry fixture setup errors caused by the required app
owner, and owns the necessary synthetic-input adaptation without weakening
assertions. Combined integration, independent acceptance and the final single
build remain pending at this checkpoint. No live window or resource is started.

This bounded preparation is owned by C (runtime/private setup), D (channel and
preview), I (existing explicit assembly seams), and E (independent focused
verification). C may create only the authorized private directory/files outside
its normal repository paths; all other exclusive write paths are unchanged.
AB has no current task. Preserve original long-lived sessions/worktrees. C/D old
PTYs are positively reported exited by the execution host; resume their original
provider sessions, preserving all code/history. No general audit or repeated full
synthetic acceptance is part of C1 preparation.

### Completed increment: bounded C1 execution entry, local evidence only

The user's instruction to continue development does not start the phone window
or authorize provider requests. M observed that the accepted
`runtime/c1_product.py` entry only validates preparation and always exits 2;
its docstring explicitly excludes runtime, database and sender construction.
C task `task_f247480eca18`, dispatch `ctx_87833307d171`, reused the original C
session/worktree and reproduced the missing command on the accepted integrated
code. M approved only a `send-once` mode in the existing private/product entries:
bounded structured stdin carries the existing `C1Permission` and an explicitly
approved PostgreSQL URL; exact private bindings and an active explicit start are
checked before the fixed isolated child/factory uses the existing prepare/send
methods. No start time is inferred. I retains factory/CLI glue ownership.
E task `task_a9d4ed2324dd`, dispatch `ctx_5e19c46c0907`, independently owns the
new focused regression in `tests/integration/test_c1_entry.py` and its evidence
in `e2e/runtime-checks.md`. Preparation checks retain their existing meaning.
No direct provider sender, parallel approval registry, background loop, fabricated
identity/start record or new product feature is authorized. Private files remain
untouched; local tests use explicitly synthetic inputs. Production, real
PostgreSQL acceptance, platform receipt and phone display remain separate gaps.

C delivered the five-path owner repair
`7167c63d61a9501c9a69e4a112d9c4a64e86911b`; its two initial regressions failed
before repair and the final focused execution/preparation/runtime selection
passed 47. E first preserved the missing-entry failure in
`2ca3c87577b7b0283e69d475f7822a7623622923`, expanded it in
`618e173cbb5549b55662349cbe9f9b29394e2f9e`, and independently found an integration
failure in its own product-call harness. E reproduced and corrected explicit
argument passing, the second authorization assertion and the actual Delivery DTO
in `cdf3f8a57f2a678110133410735d05eb7d53baf5`. The original positive assertion and
RED history remain unchanged; production authorization and receipt validation
were not relaxed. All nine product-denial cases now execute the explicit mode.

I's accepted candidate and single build source is
`ca0a425dc7bcb7b4c7c0c89b16ba8b7842a050db` on
`songconmaisaix31-design/oil-v01-i`. E independently accepted that exact source
in evidence commit `1a414917bf9b95676f79719102170cb06ef7367d`:
`uv run --locked pytest tests/integration/test_c1_entry.py
tests/integration/test_bootstrap_factory.py -k 'c1_entry or offline_factory'
-q --tb=short` passed 38, with 13 existing PostgreSQL cases deliberately
unselected and no skips. Original ordinary-flow guards and fixed-factory
construction remain; I's scoped lint and diff checks passed. These checks overlap
the owner checks and are not an additive acceptance total.

I performed one `uv build --out-dir
C:/Users/DW/AppData/Local/Temp/oil-agent-i-ctx-1b00956b6bcd/dist`, producing the
wheel and source distribution for that exact candidate. E inspected six scoped
entries in each existing archive in memory: all twelve matched candidate Git
source after LF normalization. Raw archive/Git bytes differed because of Windows
CRLF; raw byte equality is not claimed. No artifact was extracted, installed,
rewritten or rebuilt. I subsequently adopts E evidence and this sole-board
update without changing the accepted application or rebuilding it.

The explicit future entry is `python -m oil_agent.runtime.c1_private send-once`
from the integrated I worktree, supplied only through the protected existing
configuration and bounded structured stdin. A command name alone does not
authorize execution. Accepted output retains the actual platform message ID,
UTC acceptance time and attempt when available; `receipt.api_requests=null`
means UNKNOWN. The entry does not yet report a measured total HTTP count; do not
infer one from the attempt or equate ledger reservations with remote receipt.
Real execution still needs the approved isolated PostgreSQL checks and exact
bindings, plus its unexpired explicit start. No live execution was attempted.

The retained D session completed a read-only official-document mapping without
changing its clean `5355446d00e23dc64b1cd133ec191cfa0467bad8` branch. The next
console action is to add the bot capability, request only
`im:message:send_as_bot` for sending, and publish with availability restricted to
the one intended person. The official API explorer offers an app-specific
"quick copy open_id" selection; select only oneself and do not execute its send
debugger. The helper's internal requests were not observed and are not claimed
to be offline. `recipient_open_id` must not be substituted with employee ID,
User ID, union ID or another app's open ID.

D could not substantiate a console-only `tenant_key` source. The official tenant
query distinguishes `tenant_key` from `display_id`; its documented API requires
the additional `tenant:tenant:readonly` scope. A cold-token lookup needs at least
two future counted product requests (token plus tenant query), excluding any
failure/retry. Existing C1 hooks only implement token/send operations and do not
yet implement a controlled tenant-query path. No such permission change or call
was performed. Record this code gap separately from permission/API approval;
do not guess the value or use a raw lookup script. References:
[user identity](https://open.feishu.cn/document/home/user-identity-introduction/open-id),
[tenant query](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/tenant-v2/tenant/query),
[bot capability](https://open.feishu.cn/document/uAjLw4CM/ugTN1YjL4UTN24CO1UjN/trouble-shooting/how-to-enable-bot-ability).

### C1 completed local preparation: independently accepted, no live sending

The project-private configuration now exists at
`C:\Users\DW\AppData\Local\oil-agent\private\feishu-c1\config.json`.
C created it without overwriting an existing file. M independently checked path
and ACL metadata without printing contents: no reparse point, current-user owner,
protected directory ACL with only the current Windows user and SYSTEM; the file
inherits those same two entries. No platform IDs, host approval or start time
were fabricated. At that initial blank-file acceptance the application was
NOT_CREATED / NOT_CONFIGURED; the later local status is recorded above.

The user edits this JSON locally after actual application creation: change
`application_state` to `CREATED`, enter `app_id` and `app_secret`, and leave
`tenant_key`, `recipient_open_id` and `host_binding` null until exact local
confirmation. The display name and alias are already fixed. Credentials must not
be copied into chat, Git, frontend artifacts or ordinary logs.

Actual non-sending preview files also exist in that same private directory:
`c1-preview.html` and `c1-preview.json`. They use D's shared exercise renderer,
system-generated preview ID/time and the approved text, without login,
confirmation actions or links. Preview metadata is not a platform send receipt.

The fixed local entry is `uv run --locked python -m
oil_agent.runtime.c1_private` from the integrated I worktree. `check` and
`inject-check` actually returned exit 2 with WAITING_FOR_APPLICATION_CREATION,
NOT_CONFIGURED, only missing field names and start NOT_AUTHORIZED. The child
receives only allowlisted C1 values; no dotenv execution, arbitrary factory,
global environment mutation, database connection or provider request occurs.
The fixed `preview` mode is also integrated: it returned exit 0 and
PREVIEW_EXISTS_NOT_SENT without overwriting either existing preview artifact.

Owner increments include C private helper `611c7a9`, D offline preview `584c9a3`,
C exercise contract `fda37c8`, D channel `5355446`, C private preview helper
`76fdb93` and C runtime `30e90df`. I's pushed code candidate is
`f86c29e3bc99f9f761ebb32236b2dd37a7800357` on
`songconmaisaix31-design/oil-v01-i`, including all owner increments and the
limited existing-factory branch. M independently verified C/D/I remote heads.
E independently accepts actual private checks at the unchanged helper version
`ab86e486c9c07e1961d822615ba003409344bf8f` and 17 changed helper tests; earlier
E selections passed 40 preparation/contract/preview and 37 channel cases.
D's offline rendering at 320/390 pixels reported no external requests or
actions. These overlapping local checks are not an additive total or actual
phone/live-service acceptance. E accepts exact code `f86c29e` for local preparation
only; its evidence commit is `88c8b33c0e97baa323e1b1a48d3acc6b7458ac0f` in the
existing `e2e/runtime-checks.md`. No unresolved local-preparation defect remains.

Final I checks on `f86c29e`: `uv run --locked pytest
tests/integration/test_bootstrap_factory.py -k offline_factory -q --tb=short`
passed 10, retaining the original three ordinary guards; 13 existing PostgreSQL
cases were intentionally unselected. `uv run --locked pytest
tests/unit/runtime/test_c1_runtime.py tests/unit/runtime/test_permissions.py
tests/contracts -q --tb=short` passed 46. Scoped Ruff and diff checks passed.
One `uv build` produced wheel and source distribution. E independently inspected
ten scoped archive entries: wheel/sdist entries agree byte-for-byte and match
candidate Git content after CRLF-to-LF normalization only. Initial raw comparison
to E's Windows worktree differed on line endings; no artifact or source was
rewritten, and raw byte equality with Git LF blobs is not claimed.
No full synthetic CI, frontend suite/build or Docker operation was repeated.

E's final command was `uv run --locked pytest
tests/integration/test_bootstrap_factory.py tests/unit/runtime/test_c1_runtime.py
-k 'offline_factory or explicit_active_attempt or expired_host or unconfigured_c1'
-q --tb=short --junitxml=e2e/runtime-artifacts/c1-local-final.xml`: 15 passed,
13 existing PostgreSQL factory cases deliberately deselected, zero failures or
skips. E also verified owner ancestry, unchanged accepted helper/channel content
and scoped Ruff. The actual authorization/private-path and preview evidence above
is retained; test doubles do not replace SQL, platform or phone evidence.

E first reproduced PRIVATE_PATH_UNVERIFIED when the old helper rejected the two
legitimate preview files C had created. C `76fdb93` added only those exact names
to the protected directory's file allowlist. I integrated it and E reran the
actual failing checks at `ab86e486`, obtaining the correct waiting state/exit 2.
No private file was removed or overwritten and no ACL was weakened.

Reproduced implementation blockers are distinct from missing authorization:
ordinary trial construction required news rules, OAuth redirect and callback
secrets, while the old card required links/actions and lacked a per-HTTP budget
hook. I preserved three passing regression assertions for those ordinary-flow
guards. C/D own the minimum explicit nonmarket exercise/runtime/channel repair;
I owns conditional factory assembly. No fake event, callback or approval is used.

- CODE NOT YET IMPLEMENTED: the production factory remains unimplemented before
  formal delivery; it is not a C1 prerequisite. The reproduced C1 coupling and
  helper preview defects and missing foreground execution entry now have
  integrated owner repairs; acceptance remains limited to the explicitly
  recorded local checks. A controlled tenant-query intake path remains absent;
  its additional permission/API scope has not been approved or executed.
- EXTERNAL CONFIGURATION / AUTHORIZATION MISSING: the latest local schema is
  valid but `app_id`, exact tenant, personal open ID and existing test host are
  not configured. Platform ownership/permissions and entitlement coverage remain
  unverified. The direct user start and its fixed expiry are recorded above;
  missing bindings still prevent execution and no renewal is inferred.
- IMPLEMENTED, VERIFICATION NOT EXECUTED: C's 11 PostgreSQL storage tests were
  collected only, without an approved injected database. No database was started
  and no SQLite result substitutes for PostgreSQL transactions/concurrency.
  Thirteen existing PostgreSQL factory cases were also unselected. Platform
  acceptance and physical phone observation remain untested. Login, signed
  callback and identity receipt are outside this round. Before real sending,
  verify the new durable path on an approved isolated PostgreSQL environment.

Feishu product requests 0, message attempts 0, accepted message IDs none and new
paid product cost 0. Development-agent billing is unmeasured. No API failure or
empty success response is inferred from not executing a request. No continuous
monitoring or service was started; no Docker or unknown resource was touched.
C/D finished their bounded tasks and their original resumed sessions were
retained; AB remained idle. I/E complete only evidence/governance adoption and
an unchanged-code/remote check before retaining their sessions. No further
development or testing loop starts without a concrete defect or authorized work.

The user accepts `8af1c001b087c7a37973f2b5e4a8d545ec7d3027` as the code
baseline for **bounded rule repairs and controlled trial preparation passed**.
This is not actual deployment, live-service or production acceptance. Final
[CI 34669986562](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34669986562)
passed on that exact delivery SHA; E independently verified the documentation-only
delta from accepted code `239baa6` and both published E/I branch heads.

Use only the existing minimum intake below. M summarizes missing business
choices in Chinese; agents map them to the existing technical permission fields.
Do not create a second approval system or ask again for confirmed inputs. A phase
change alone does not select a provider, approve costs or identify a recipient.

The following live paths advance independently when their own conditions are
approved; none requires all other paths to be ready:

- A: one finite, read-only real source run verifies authentication, tool
  parameters, bounded incremental records, database persistence and request
  counts. Report empty responses, failures and genuine records separately.
  Model calls, sending and continuous polling remain disabled for this path.
- B: the approved model processes only a bounded set of content with established
  usage rights. Record actual model/version, calls, input/output tokens, cost and
  judgments. Ordinary messages remain silent. Preserve exercise/history labels
  and the approved rule version; never tune rules to make a test message pass.
- C: send only an approved, visibly labeled exercise card to the exact approved
  Feishu test person. Separately record platform message ID/acceptance, phone
  observation, detail access, real login, personal confirmation and durable
  receipt. Do not wait for a real major event or present an exercise as one.

Before the first live call, explicitly approve request/token/fee ceilings and a
stop owner. Every MCP initialization, discovery, pagination and retry request
counts. Do not enable ongoing polling, buy services or expand recipients without
approval. Secrets enter only the agreed project-scoped private mechanism, never
chat, Git or logs.

Use existing trial deployment materials on the approved host to verify actual
egress enforcement, trusted HTTPS, callbacks, database isolation and stop/resume.
Loopback listening does not prove external callback reachability; configuration
checks do not prove effective host rules. Keep provenance and production gates.
The production factory remains unimplemented before formal delivery but is not
a prerequisite for this trial. Inspect only confirmed legacy E resources; no
unknown-resource cleanup or shared Docker restart.

No feature development, generalized audit or repeated full synthetic acceptance
is authorized by this phase transition. Dispatch repairs only for a defect found
in real integration or an already reproduced blocking problem, returning domain
repairs to AB/C/D; I integrates and E independently accepts. M edits governance
only. A track with no executable work ends its current task and retains its
session/results; no waiting loop, repeat tests or work invented to stay busy.

Phase-entry evidence: no running version on an approved live host, genuine
source record, model usage, platform message ID, phone observation or identity
receipt has been verified. Live A/B/C and host operations are NOT EXECUTED, not empty
successful responses or failed provider calls. Product requests/tokens/paid cost
remain 0; development-agent/CI billing is unmeasured. The minimum intake still
lacks the specific source, model/rules/budgets, test-person and runtime approvals.
Only each dependent live action pauses. The existing E Docker observation below
remains unverified; no repeated container probe is needed merely for this phase
change. That phase-entry governance adoption was completed before the newer C1
local-preparation authorization above; the C1 section is the current scope.

## Completed increment: contextual guards and controlled trial preparation

### Final code outcome: independently accepted synthetic repair and preparation

E accepts I code `239baa69b06bf9ede8c71391d12a2cb89e1a1064` within this
bounded increment. [Full CI 34669549557](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34669549557)
passed 375 core and 237 integration tests on separate real PostgreSQL services,
zero failures/errors/skips; 23 frontend tests, schema, TypeScript/Vite, shell and
both Linux image builds passed. [Deployment CI 34669549519](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34669549519)
passed 70 overlapping checks plus actual Nginx syntax/key loading with network
none. I and E independently downloaded JUnit; M independently verified exact
run/job success and origin SHA. E's evidence-only commit is
`6cf292b347f801d442db68734708b51e89ebdc41`.

R-16 is repaired by AB `dea13fa81825f1160ef44187885a98c569375edb` after E
first reproduced eight failures. The original E test files remain unchanged and
now pass; incident/impact negation, planning, exercise/training/procedure, archive,
stale/future/ambiguous controls and PostgreSQL recipient/revision corrections
remain covered. The helper handles bounded casualty-only predicates, not general
Chinese language understanding. R-17 preparation and its Linux compatibility
defect are resolved by E `c557665` and `3afa038214309188d26db2448eb5be076d42e7ed`:
opt-in trial overlay, internal separate database, explicit destination pins,
loopback TLS/callback routing, bounded logs and read-only cold/retained preflight.
Runtime activation, packet filtering, trusted TLS and physical recovery are not
accepted by these configuration tests.

Final report/governance adoption and E's equivalence/remote audit completed at
`8af1c001b087c7a37973f2b5e4a8d545ec7d3027`, preserving application/test/deployment
bytes. All earlier checkpoints below are historical.

| Remaining item | Classification | Actual evidence / next required action |
| --- | --- | --- |
| Source/model/rules/budget and Feishu/runtime inputs (R-05/R-06) | 缺外部授权 | No new approval or secret supplied; the single minimum intake below remains pending. Only matching live actions pause. |
| Real source authentication, MCP discovery/parameters and incremental records (R-01/R-07) | 已有实现待实测 | NOT EXECUTED; 0 product source requests, no real incremental record accepted. Every MCP wire request, including initialization/discovery/pages/retries, must reserve budget. |
| Approved model, actual usage and ordinary-message silence (R-02/R-07) | 已有实现待实测 | NOT EXECUTED; 0 model requests/tokens. Synthetic rules/cost-counter tests are separate from real accuracy and billing evidence. |
| Feishu platform acceptance for labeled exercise (R-04) | 已有实现待实测 | NOT EXECUTED; 0 platform requests/sends. Exact approved test recipient and exercise label still required. |
| Phone viewing (R-04) | 已有实现待实测 | NOT EXECUTED; no phone display or notification observation. |
| Real login and human acknowledgement (R-04) | 已有实现待实测 | NOT EXECUTED; no authenticated real user confirmation. |
| Trial host egress/TLS/callbacks/stop and recovery (R-03/R-17) | 已有实现待实测 | Preparation code passed; no host firewall/network activation or live trial startup/recovery. User-approved runtime and private injection required. |
| Legacy E container and interrupted schema cleanup (R-14) | 已有实现待实测 | Actual targeted Docker check failed because the Linux engine pipe is absent. Exact known E resource remains unverified; no shared daemon restart, stop, deletion or cross-track operation. |
| Production factory (R-13) | 代码尚未实现 | Still deliberately rejects startup; not a controlled-trial prerequisite, but remains unfinished before formal delivery. No relabeling or gate bypass. |

Paid product-call cost is 0; development-agent/CI billing is unmeasured. No new
services were bought, no public port activated, and no recipients expanded.

The user accepts `cd6e8d9d87acbde9b844b4568ab2df72e00bab8d` as the
simulated-integration baseline for real-integration code only. Real source,
model, phone and production acceptance remain NOT EXECUTED. The earlier
delivery interruption below is historical: replacement I/E finished and retained
their sessions, and final CI 34666490657 passed 343 core, 150 integration and
23 frontend tests. This acceptance does not authorize external product calls.

Current audit: M `473078f`, AB `6c517f5`, C `1723886`, D `ea2c3ab`,
E `4676827`, I `cd6e8d9`; all six worktrees clean, existing origin unchanged.
The retained replacement I/E terminals are connected and writable. The retained
AB terminal currently reports disconnected/unwritable with `stop_unverified`;
recover its existing session through Orca evidence, never assume it exited.

Recovery observation supersedes that initial AB status: exact `worker-show` and
`worker-read` from the execution host positively reported the old AB PTY exited.
Scoped session metadata and original Task/Dispatch/commit strings identified its
existing Codex session `01a091b0-2d36-7212-aa19-9bcdc3a64743`; `codex resume`
restored that same session in the same worktree, not a replacement conversation.
Readiness was confirmed before dispatch; the rendered pending task was submitted
once. Current AB Task `task_b670c01d251a` / `ctx_819451107da2` uses
`term_1b57de41-ad0c-4d17-9961-9290a940af2e`. E uses `task_bd31802251e0` /
`ctx_021961ba2ddd` in its retained replacement terminal, I uses
`task_c01affff8c19` / `ctx_6d12690fe3ab` in its retained replacement terminal.
C/D have no work this increment; old terminals are disconnected (C reports
operator_close), and their worktrees/branches/evidence remain preserved.

The first AB resume inherited the old workspace-write/on-request execution
profile; even read-only commands hung and made no changes. M canceled the exact
pending read, observed the interrupted turn, fenced/abandoned that dispatch and
closed only its newly created external PTY (positive ptyKilled receipt). The
same original session was resumed with the current workspace's explicit
danger-full-access/never execution profile; no global hooks/configuration were
changed. Same Task now retries as `ctx_915cc32ffee1` in
`term_c862b0a8-b6ee-4fe0-84bb-f918f4c133ef`; its exact transcript confirms actual
tools returned successfully. Original history/worktree/branch remain preserved.

| Owner | This increment only | Completion evidence |
| --- | --- | --- |
| E then AB | E first commits minimal failing regressions for unrelated casualty negation and midnight freshness; preserve denial/planning/exercise/archive assertions. AB fixes only intelligence-owned paths after reproduction. | Original failures and unchanged assertions passing on I candidate |
| E | Prepare opt-in controlled trial deployment, constrained egress, HTTPS/callbacks, isolated database, scoped recipients, redacted logs and stop/resume; inspect only confirmed E containers and retain data. | Configuration/negative tests and exact resource observations; no public exposure or external delivery |
| I | Integrate owner commits incrementally in existing approved glue paths; map existing configuration into one minimal intake in this board via M handoff. | Exact pushed candidate, applicable core/integration/build checks, independent E acceptance |
| C / D | Retain sessions; domain or contract defects return to their original owners only when found. | Scoped handoff and tests if a change is necessary |
| M | Record decisions, ownership, acceptance and one minimum external-input sheet here. | No business-code edits and no duplicate TODO |

Existing exclusive paths and I transfers below remain authoritative. E may add
deployment overlays/scripts/tests in its owned paths; I retains only the
factory/environment seam in `deploy/compose.yaml` and integrated startup notes
in `docs/runbook.md`. No simultaneous edits to those seams. No production
factory work, project rebuild, new services purchase or public ingress activation.

R-16/R-17 implementation and original failed assertions are now accepted at
`239baa6`, superseding the intermediate pending/failure records below. R-14
remains `已有实现待实测` for exact E container final state. R-05/R-06
remain `缺外部授权`; only their corresponding live actions pause. MCP initialize,
discovery, pagination and every explicit retry count against the approved request
budget; never silently increase cost or hide degraded monitoring. Real source,
model, platform acceptance, phone view and human confirmation require separate
evidence; synthetic tests cannot replace any of them.

### Single minimum live-integration intake

Reused confirmations: existing stack and code, trial/fixture separation, ordinary
news silence, exact test-recipient scope, no public activation or purchase, and
separate real source/model/platform/phone/human evidence. Jin10 priority and the
OpenAI implementation are candidates, not approved services. No new product
authorization or secret was supplied. M consolidates I's inspected configuration
mapping here; this is the only input sheet, not another task board.

| User confirmation still required (nonsecret reference/alias only) | Agent-owned mapping from current code |
| --- | --- |
| Source license: provider/API docs, access/storage/redistribution rights, permitted fields/retention/deletion owner, validity, request/page/poll/retry caps | If Jin10 approved: one `OIL_SOURCE_PERMISSIONS` entry, `OIL_EXTERNAL_SOURCES_ENABLED`, `OIL_DAILY_SOURCE_REQUESTS`, explicit `OIL_JIN10_ARGUMENTS_JSON`, cursor parameter/type. Fixed endpoint `https://mcp.jin10.com/mcp`; initialize, initialized notification, each discovery/page and explicit retry consume reservations before transport. Existing factory polling 300 seconds, max_pages 2, max_items 500 need approval, not automatic quota increases. |
| Model/data-processing approval: provider and exact model, validity, calls/input+output tokens/urgent reserves, currency/amount ceiling and stop owner | If OpenAI approved: `OIL_MODEL_PERMISSION`, `OIL_MODEL_CALLS_ENABLED`, daily model calls/tokens and urgent reserves. Fixed Responses endpoint; persistent reservations retain unknown usage. Currency spending is not enforced by `budget_ref`: require approved provider-side cap or operational control and pricing evidence before paid calls. |
| Chinese first-report rubric: reviewer, facilities/events/impact, original publishers, timezone/freshness, severity, evidence standard and correction policy | Agent builds `OIL_APPROVED_RULES_JSON`; model/send `rules_ref` exactly equals `authorization_ref@version`. `OIL_FIRST_REPORT_POLICY` stays unset until `credible_single_source` or `independent_only` is approved. Contextual negation and midnight repair is R-16, not a request for per-message annotations. |
| Feishu scope: tenant/app, one exact test-person mapping and phone/account/device/time window, operation caps, registered HTTPS URLs and bot send permission | Private identity subject `tenant_key:app_id:open_id`, actor/recipient/role map in `OIL_IDENTITY_PERMISSION`; exact subset in `OIL_TRIAL_SEND_PERMISSION`, `allow_reports=false`. `OIL_PUBLIC_ORIGIN`, web-return `OIL_FEISHU_REDIRECT_URI`, callback `/api/v1/callbacks/ack`, Secure cookies. Outbound stays dry_run until approved; fixture exercise requires separate exercise_dataset/exercise_ref and visible labels. Platform receipt, phone view and human acknowledgement remain separate. |
| Runtime: exact approved host/owner, trial resources, constrained egress/DNS, HTTPS domain/certificate mechanism, private injection path, isolated DB/volume/backup and stop/resume owner | Shared factory, `OIL_DATA_PROVENANCE=trial`, `OIL_FIXTURE_DATASET=null`, internal PostgreSQL URL. E prepares opt-in deployment and I wires approved seams. Existing trial constructors perform no migrations, seeding or provider requests; C provisioning validates exact approved actors separately. No public activation or shared Docker restart is authorized. |

Every permission uses an immutable approval_id, authorization_ref, UTC validity,
budget_ref and max_requests; changed scope needs a new approval_id. Agent fills
technical mappings after confirmation. Credential values must never enter chat,
Git or logs: inject only project-scoped `OIL_JIN10_TOKEN`, `OIL_OPENAI_API_KEY`,
`OIL_FEISHU_APP_SECRET`, `OIL_FEISHU_ENCRYPT_KEY`,
`OIL_FEISHU_VERIFICATION_TOKEN`, database credentials and TLS key through the
approved private mechanism. Public records contain aliases/references only.
References do not implement automatic retention deletion or monetary billing.
Actual product source/model/Feishu calls, tokens and paid product cost remain 0;
development-agent and CI billing are not collected.

First repair evidence: E `b9a241acfe0353ce425a7eef258111d72fcc253d` adds
`test_contextual_guards.py` before AB modification: 8 failed, 28 passed, zero
skipped against the accepted application code. Six failures show unrelated
casualty negation vetoes at rule/guard/assessment boundaries; two show rejection
after a 50-second midnight crossing inside an approved 60-minute age window.
Existing denial and other negative assertions remain unchanged. I is authorized
to integrate this evidence increment; it is deliberately not a passing candidate.

I BEFORE candidate `0fa7d85c8e235403cb893f566828f4213131c34f` is pushed;
E independently verified identical application code and unchanged regression
assertions. CI 34668619029 confirms 343 core pass; integration 163 pass/8 fail,
zero errors/skips. R-14 actual recheck: Docker Linux pipe remains unavailable and
targeted inspection of the known E container failed for that reason. No daemon
restart, deletion, resource stop or cross-track container inspection occurred;
E final container/schema-cleanup state remains unverified.

R-16 owner repair `dea13fa81825f1160ef44187885a98c569375edb` is pushed,
with four AB-owned paths only. Unchanged E regressions changed from 8 fail/28 pass
to 36 pass; AB 210 pass, non-PostgreSQL 435 pass/111 deselected, Ruff and package
build pass. The bounded casualty-only predicate view cannot supply affirmative
event/impact criteria; source quotations remain unchanged. Approved elapsed age
replaces calendar-date equality; explicit denial, compound negative objects,
conditional/procedure/training/archive/future protections remain. It is not a
general Chinese semantic model or live accuracy acceptance. I integrated at
`f8c549b6acdd5a53e6552b969d353c965c6d3d97`, with 147 relevant tests passing;
independent E and full PostgreSQL CI remain pending at this checkpoint.

R-17 E preparation `c557665440ce537017741d84b46396fac77da404` adds opt-in
trial overlay, loopback TLS proxy, explicit approved IPv4 pins, internal database,
read-only preflight, guarded future start wrapper and tests. I integrated it at
`9c5cba6baac9d2ed33a653515334046bae3a8bac` through authorized documentation
and environment-example seams only. Local preparation checks: 54 pass. Linux
focused CI 34669072808: 53 pass/1 fail because an older Compose serializer omits
the explicit false bind field. This is an E implementation compatibility defect,
not missing external authorization; E repairs it without weakening unsafe-mount
assertions. E also implements a read-only stopped-resource revalidation path so
future recovery does not bypass cold-start checks. No network/firewall/container
activation, public exposure, real source/model/platform call or phone test occurred.

## Current phase: real integration v1.1 (2026-09-12)

The user's current conversation is the v1.1 execution authority. The Downloads
directory contains the original v1.0 plan; no separate v1.1 file was found in the
scoped filename check. The user explicitly accepts
`ed1de2e24634e8471e0979cfc168eebec4c12e4c` as the local fixture/dry-run integration
baseline, never production acceptance. Reuse that implementation and the five
original worker sessions/worktrees/branches. Do not rebuild or expand features.

Current code acceptance: `63627eee09bc9fb10e32b68f979f7715db199791` on
`songconmaisaix31-design/oil-v01-i` passed complete
[CI 34665612094](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34665612094).
E independently inspected JUnit: 343 core and 150 integration checks passed,
zero failures/errors/skips, including both preserved domain regressions and all
13 factory PostgreSQL cases. Frontend 23 tests, generated schema, TypeScript,
Vite, shell checks and both Linux image builds passed. M separately verified the
public run/job conclusion and approved producer ancestry. This accepts the trial
code with synthetic provider responses; real source/model/login/phone acceptance
is NOT EXECUTED. Final report/governance adoption changes no application code.

Delivery interruption: I ordinary-merged E evidence 4676827 and M governance
0696b29 into local `930250f8606221bafe797dbb7aa90cd36d8d30d1`, then its exact
original terminal displayed a provider usage-limit error (verified rendered
screen). Accepted code 63627ee is already pushed; the I handoff documentation is
still modified and the final document delivery is not pushed. No code changed.
M requested either restored capacity for that original I session or an explicit
one-time exception limited to the four reviewed document paths. M has not taken
over integration, changed models or bought credits.

Recovery authorization: the user subsequently stated that the account was
changed and explicitly requested new subagents with transferred context. M
verified both old I/E terminals ended on usage-limit errors, stopped/fenced their
dispatches, archived/released I's exhausted terminal through its actual resource
owner, and stopped E's exhausted supervised terminal. Worktrees, branches,
commits and I's uncommitted evidence draft remain intact. Two fresh replacement
workers now resume I and E on those exact separate worktrees and exclusive paths;
AB/C/D implementations remain accepted. No project rebuild or feature expansion
is authorized by this recovery. The previous request for a main integration
exception is superseded by this explicit new-worker instruction.

Recovery execution is verified, not just input acceptance: fresh I
`ctx_c95adee1e8f5` / `term_ca3b9e78-e837-4c93-9fc3-09fac513daad` and fresh E
`ctx_5635456cade8` / `term_9931c47c-89cd-4906-a451-0e3c10cd537f` both have exact
new-session transcripts with actual tools executing. They retry the original
I/E Tasks, preserving the original branches/worktrees and role boundaries.
R-15 capacity interruption is resolved for this execution; final document
delivery is again in progress, with no change to product authorization gates.

Initial read-only audit: M HEAD `7839b316dad94296857c4b901fe11333a8d24644`; AB
`f3c835793da03a0b0f1b8fb130c6312db2094d80`; C
`41a00ded1f949aee8099b549d5d419f0487dd0f9`; D
`0bbdc217b43aec94e66ead9863a734f7902d20f2`; E
`06af7997043c03bd06c91e9afab560bcf4432ae5`; I accepted baseline above.
All six worktrees are clean. Original terminals are live, exact, connected and
writable; old dispatches are settled and require fresh dispatch authority.
Run remains `run_64e3991f76b9`. Public origin and directory ownership are unchanged.

All five original workers have acknowledged v1.1 and executed tools in their exact
existing sessions. AB/C/D/E reused the supervised worker-start path. I's
worker-start returned agent_unconfigured before task creation; the verified live
I terminal was reused through a fresh documented low-level task/dispatch. A
screen check proved the pasted task was still at the composer, and one submit
completed delivery; exact transcript and I's acknowledgement then proved actual
execution. I remains an unsupervised dispatch, with its original resource retained.
No duplicate worker, terminal, worktree or Run was created.

| Track | Current task / dispatch | Current state |
| --- | --- | --- |
| AB | task_2eacda0db6eb / ctx_a5f1b25a8789 | Delivered 6c517f5; settled and explicitly retained; E unchanged T05 passed |
| C | task_5614734edbd3 / ctx_96bb71f83ff1 | Delivered 1723886; E unchanged immutable-session regression passed; settled and retained |
| D | task_c2c9686439df / ctx_87f9412b8dde | Code delivered at ea2c3abb; settled and explicitly retained |
| E | task_826e16b53577 / ctx_5635456cade8 | Replacement verified executing; 4676827 accepted-code evidence retained; final delivery audit |
| I | task_642b869e5aaa / ctx_c95adee1e8f5 | Replacement verified executing; accepted 63627ee and original draft retained; final document delivery |

Construction decisions: AB calls C authorization before every provider request,
including MCP setup/discovery/pagination; no hidden retries. C returns durable
request reservation IDs and records model input/output usage; missing usage stays
unknown and retains its reservation. New real Feishu identity subjects are exactly
tenant_key:app_id:open_id, with no fallback alias from fixture identity/session.
The Jin10 guide documents the MCP endpoint and flash result shape but omits tool
arguments; AB will discover and validate inputSchema and explicit argument bindings
instead of guessing them. The official OpenAI Responses client is an implementation
candidate only; provider/model/rules/call approval remain pending.

Early E evidence: 10 focused HTTP/session/OAuth-adapter cases passed against the
isolated migrated E PostgreSQL, zero skips. Provider responses were synthetic
httpx transports, not a real Feishu login. E stopped and retained its exact test
container afterward. These preparation checks do not accept the future I candidate.

Incremental integration: I candidate 1 `26e3391c24afaa5e098f545831610961204a7802`
contains C `aa7d638` and E `4a55ffe`; candidate 2
`0be5ab779da9cb7b79ed467ed009d171656b0d40` adds D `cfda444`/`8db81c7`.
Both are pushed and remain REVIEW. Candidate 1 CI 34663145891 FAILED: three E
channel cases construct production outbound with a fixture dataset, now correctly
rejected by C's classification validation (79 integration cases passed, 3 failed).
C must finish trial operation and E must migrate these explicit scenarios while
preserving accepted/UNKNOWN/revoked assertions. Do not relabel all fixtures as
production or weaken gates. This is an implementation/test integration gap, not
missing external authorization. I routes the fix to C/E and continues source
integration; no full-suite or production acceptance is claimed.

### One-page incremental execution and ownership

| Increment / owner | Bounded work | Integration and acceptance |
| --- | --- | --- |
| R1 AB | Concrete documented Jin10 MCP flash transport/adapter; concrete documented model client with explicit configuration; approved-rule assessment without per-message manual ClaimReview injection | I merges each verified commit; E checks exact candidate, malformed/duplicate/stale source, untrusted model output and non-urgent silence |
| R2 C | Explicit fixture/trial/production classification, trial permissions and runtime gates; remove unconditional implementation prohibition through validated configuration, not bypasses | I merges; E tests scope, provenance, source/model budget and send denials |
| R3 D | Reuse existing Feishu HTTP/OAuth/callback code; address trial-channel and phone/login/ack seams; provide exact safe test procedure | I assembles; E verifies identity/message binding; actual phone evidence only after approved external inputs |
| R4 I | Assemble R1-R3 incrementally, preserving default fixture/dry-run behavior and all gates | E accepts each integrated increment; failures return to original owner |

M owns only AGENTS.md, README.md and this unique TODO. AB/D/E retain their existing
recursive write paths below. C retains its existing paths EXCEPT the I transfers
below. I owns `src/oil_agent/bootstrap.py`, `.env.example`,
`config/integration-handoff.md`, `tests/integration/test_bootstrap_factory.py`,
the factory seam only in `src/oil_agent/runtime/cli.py`, factory/environment wiring
only in `deploy/compose.yaml`, and integrated startup notes only in
`docs/runbook.md`. C owns all other runtime/contracts/storage/API/config changes;
E owns all other integration tests and deployment/verification files. Shared-file
changes require a coordinator handoff and sequential ownership, never concurrent
edits. Owners merge the accepted I baseline and this governance normally before
implementation. No additional workers/worktrees/branches are needed.

### Current gaps (one authoritative list)

| ID | Classification | Gap / owner | Evidence and next gate |
| --- | --- | --- | --- |
| R-01 | 已有实现待实测 | Concrete news network transport and adapter / AB | Jin10 HTTPS/MCP transport, discovered-schema validation, adaptation, checkpoints and reservation guard integrated and E accepted at 63627ee; approved real provider request/license/retention validation pending |
| R-02 | 已有实现待实测 | Concrete model client and approved-rule assessment / AB | OpenAI Responses implementation candidate and reusable approved rubric, including conditional/training and denial corrections, integrated and E accepted at 63627ee; actual provider/model/business-rule approval and live accuracy/cost evidence pending |
| R-03 | 已有实现待实测 | Trial assembly / I | Implemented at 8de731b, repaired candidate 63627ee passed complete CI and independent E review; process-env/permissions/real adapters/PostgreSQL/synthetic-provider chain verified, approved real chain pending |
| R-04 | 已有实现待实测 | Feishu send/OAuth/signed callback / D + E | Existing code reused with tenant:app:open_id binding, exact test-recipient scope and fixture/trial labels; independent adapter/session/outbox/signed-ack tests passed, actual tenant login/phone receipt/ack NOT EXECUTED |
| R-05 | 缺外部授权 | Source/model/provider/rules/budget and project credential injection / user | One minimal external-input request is pending; no unrelated credential search or paid calls |
| R-06 | 缺外部授权 | Feishu app/tenant, exact test-recipient allowlist, redirect/callback/public URL and test phone / user | No customer-scope expansion; credentials must not enter chat, public Git or logs |
| R-07 | 已有实现待实测 | Real non-urgent source-to-model-to-storage chain and zero-alert result / AB + C + I + E | Requires R-01/R-02/R-03 and approved inputs; a marked urgent exercise is separate evidence |
| R-08 | 已有实现待实测 | Authorized real quote sample, external deployment probes and 7/14-day operation | Outside this increment's first chain; preserve prior gates and do not claim production acceptance |
| R-13 | 代码尚未实现 | Production assembly / I | Deliberately rejected by build_runtime; outside the current trial-first increment. It is missing implementation, not merely missing credentials |
| R-14 | 已有实现待实测 | Local container final-state verification / C + E + I | Docker Linux named pipe disappeared during I final image refresh; C/I had stopped their own containers, E was interrupted. Preserve resources; remote isolated PostgreSQL CI supplies testing while host recovery remains pending |

Resolved during this phase: R-09 fixture/identity test migrations (E d4d772a and
6be21de), R-10 immutable approval on session/API/callback use (C 1723886), R-11
explicit denial correction (AB 6c517f5), and R-12 Compose safe-default assertions
(E 49c75d32). All passed in the final integrated CI without weakening the original
failed assertions. E 87a737b adds independent configuration boundaries; D ea2c3abb
is the final channel/mobile handoff. The earlier failed candidate records below
remain historical evidence and are superseded by the acceptance at this section's top.
R-15 execution capacity was resolved by the explicitly authorized replacement I/E
workers; original stopped attempts and their evidence remain recorded above.

Current construction decisions: rule identity is exactly authorization_ref@version,
with @ excluded from either component, and the loaded rule must match both model
and send permission references. Rules use reusable bounded source/facility/event/
occurrence/impact/currentness criteria, not a complete-message template or a
per-message ClaimReview. They remain conservative literal-text rubrics; approved
real examples and false-positive/false-negative evaluation remain outstanding.
I reads only fixed project credential variables after matching enable/permission
configuration, never arbitrary paths/environment names from credentials_ref.
Trial process-env startup must parse OIL_FIXTURE_DATASET=null explicitly (C fixed).

Further bounded evidence: E independently passed source candidate 85fdcff with 86
non-PostgreSQL checks plus 3 real PostgreSQL checks, including actual HTTPX/HTTPCore
framing over an isolated network backend and transactional cursor/revision recovery.
This is LIMITED_LOCAL_PASS, not real TLS/provider acceptance. Model candidate
05231c5 and source reservation-guard successor 54b9c1d are pushed for E review;
AB source guard code is 412aded9d5207fd542615facc5dd7fde55703752. Full candidate
acceptance remains FAIL pending R-03/R-09 and the subsequent complete checks.

Latest assembled evidence supersedes the early candidate status above. I code
8de731b wires Jin10 transport, OpenAI Responses candidate, reusable approved-rule
assessment, C reservations/provenance/session gates and D OAuth/send/ack through
one factory. CI 34664381567 passed 340 core and 128 integration checks, failed two
integration checks, and skipped none. E f783bac added immutable-session and durable
usage regressions; its CI 34664692956 passed 339 core and 125 integration checks,
failed two, and skipped none. Unknown/overrun usage cases passed on Linux PostgreSQL.
E independently confirmed 93 unchanged rule checks, including the previously
failing Chinese conditional/procedure/training messages. Explicit denial remains
a separate regression. I candidate 6f76950d02fe336508a4d9ff17d3428919fb6119 preserves
all three current domain/test failures. No full acceptance is claimed yet.

The implemented factory preserves default fixture/dry-run and empty startup.
Trial uses explicit settings, matching typed permissions and fixed project secret
variables; no automatic credentials search or per-message ClaimReview is required.
I's own 18-check PostgreSQL smoke passed, including ordinary-message silence and
synthetic-provider OAuth/outbox/signed acknowledgement. These are actual local
runtime/database paths with synthetic provider responses, not real source, model,
tenant login or phone evidence. Frontend 23 tests/schema/TypeScript/Vite passed.
Final corrected code 63627ee supersedes the preceding intermediate FAIL status;
the original failures remain visible in E's report.

Minimal external inputs were requested once: (1) approved source/interface/license,
(2) approved model provider/model and this run's budget, (3) alert rules and
first-report policy, (4) Feishu tenant/app, exact test recipients, registered
login/message callback URLs and available test phone. Supply only the controlled
project injection method, never credential values in chat. Missing inputs leave
live calls pending while implementation and isolated tests continue.

Usage at phase audit: product source requests 0; product model requests/tokens 0;
Feishu sends 0; paid product cost 0. Documentation/Git/Orca reads are excluded from
product-call counts. Record actual provider usage and cost evidence when available;
unknown cost must be reported as unknown, never invented as zero.
Development-agent billing was not collected and is not included in the zero
product-call cost. Synthetic HTTP exchanges are identified per test/smoke in I/E
reports; they are not billed provider traffic or real emergency evidence.

The sections below preserve the previous local phase's historical decisions and
evidence. Their old BLOCKED_EXTERNAL labels and integration timing are superseded
by the classifications and incremental I/E workflow above.

## One-page execution plan

Build the independent refined-oil alert workflow described in the user-supplied
`C:\Users\DW\Downloads\成品油预警Agent_多Agent协作开发规划_v1.0.md` (2026-09-12).
First evidence: labeled replay -> PostgreSQL -> versioned event -> durable outbox ->
dry-run delivery -> authenticated acknowledgement. Then reliability, daily reports,
quote import, mobile views and deployment checks. Real source, Feishu, phone and
14-day operation are separate external gates. No production delivery is claimed.

| Stage | Work | Gate/status |
| --- | --- | --- |
| M0 | Read-only baseline; C freezes contracts, dependencies and API schema | PASS for local foundation and integrated contracts |
| M1 | AB replay/assessment + C transactional pipeline + D dry-run/ack | Local synthetic I/E gates PASS; real source/phone BLOCKED_EXTERNAL |
| M2 | Revisions, independent evidence, failure recovery, authorization | Local synthetic E gates PASS; full process-kill/load/external scope untested |
| M3 | Daily reports, safe quote imports, five responsive views | Local synthetic I/E gates PASS; authorized real quote/report acceptance pending |
| M4 | E regression/security/PostgreSQL/Compose; separate I integration | Integrated code a4617e9 accepted with full Linux CI; production/phone/load gates remain |
| M5 | Authorized source/phone and >=14 days operation | BLOCKED_EXTERNAL |

Ownership is recursive below; prefixes resolve against each track's actual
worktree. Unlisted files have no owner. C receives the plan's M technical files
because the user requires the coordinator to avoid business code. AB combines A
and B to reduce agent count; independent source and processing modules remain.

| Track | Exclusive write_paths | Initial work / state |
| --- | --- | --- |
| M | AGENTS.md, README.md, V01-TODO.md | local candidate decisions, status and acceptance recorded |
| C | src/oil_agent/contracts/, src/oil_agent/storage/, src/oil_agent/runtime/, src/oil_agent/api/, src/oil_agent/__init__.py, src/oil_agent/bootstrap.py, tests/contracts/, tests/conftest.py, tests/unit/storage/, tests/unit/runtime/, tests/unit/api/, pyproject.toml, uv.lock, .python-version, .env.example, .gitignore, alembic.ini, config/ | local runtime accepted; retained for integration fixes |
| AB | src/oil_agent/ingestion/, src/oil_agent/intelligence/, src/oil_agent/reporting/, tests/unit/ingestion/, tests/unit/intelligence/, tests/unit/reporting/ | local increment accepted; integration pending; external source/model gates remain |
| D | src/oil_agent/channels/, web/, tests/unit/channels/ | local increment accepted; real API/phone acceptance pending |
| E | tests/integration/, e2e/, fixtures/, deploy/, scripts/, .github/workflows/, docs/runbook.md | local increment accepted at 06af7997; retained; external gates untested |
| I | oil-v01-i; explicit glue transfers listed in the final integration boundary below | local code accepted at a4617e9; final branch receipt supplied after governance/CI |

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
| I | C:/Users/DW/orca/workspaces/oil-agent/oil-v01-i / songconmaisaix31-design/oil-v01-i | a187197f273a0abfcf84f84f241e7f4bac335b9d / ctx_12b1d40a4d65 (task_55bfd8a7d1fb) | code accepted at a4617e9; terminal retained for final handoff |

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

## Historical integration decisions and evidence

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

## Reviewed fixes before E acceptance

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

I was created through Orca in the explicit new worktree. Terminal
term_ef3b932c-59ff-4d86-9520-e42be2ffb98d accepted the task in request
30294b31-75b6-4126-bf0f-d3337ccbbad8. Main then read the exact provider transcript
and verified the agent's baseline acknowledgement and real handoff/plan read tools;
the ready/input receipt alone was not treated as execution evidence.

## Accepted integrated local candidate

- I normally merged all four exact producer commits without conflicts, ending at
  merge checkpoint 35217f41016c83fa76bda624cb3a31be67a3befc. Main verified the
  resulting diff and reviewed the six-file factory increment
  a4617e9528177c536c1768297f1ff5783ee1f9ec, matching origin. No other domain
  code, lockfile, shared schema, fixture guard or governance file was changed by I.
- The API/CLI/Compose default now shares oil_agent.bootstrap:build_runtime. It
  composes existing AB/D services with C Runtime, creates no users or input data,
  keeps sources/identity/model closed and preserves database authorization.
  Three added actual PostgreSQL integration cases verify those defaults,
  conservative persistence/current summary, HTTP quote import/report/dry-run,
  recipient isolation and revocation.
- Main independently verified Actions 34639549516 SUCCESS on the I code SHA and
  read exact log totals: 195 core + 72 integration + 13 frontend passed, zero
  skips. Frontend schema/type/build and both Linux images passed. The local
  deliberately scoped Python selection passed 169 tests; it is not substituted
  for the full remote PostgreSQL run. Locked sync, Ruff, corpus28 and Python
  packaging passed; one upstream Starlette/AnyIO deprecation warning remains.
- I allocated only new oil-agent-i / oil_i_test at loopback 55435 with a new
  process-scoped password. Fresh migration to 0002_runtime, queue schema,
  recovery, conservative persistence, parser/report, real HTTP 200/401/501
  boundaries and all three worker --once commands passed. Main read the
  task-private smoke result and verified container
  b8948128e9cbe1504ba250eab07e0948a531c4193bfda1181ed7b11009ec93e1 stopped
  with exit 0. C/E resources were not changed; all are retained, not deleted.
- Main also verified E final-report CI 34638645101 SUCCESS on 06af7997. E's
  original eight-browser/restore/restart evidence keeps its original candidate
  attribution. I's new factory evidence does not imply real OAuth, phone,
  external source/model, customer quote or continuous-operation acceptance.
- I adopts the final README/board by ordinary merge, pushes and verifies the
  final branch's own Actions HEAD before its completion receipt. That receipt
  supplies the final SHA; this file does not use a self-referential commit hash.
  The delivery branch is songconmaisaix31-design/oil-v01-i. No merge to main,
  production deployment, external sending or paid product call was executed.
