# E runtime verification

Provider replies and market content in this report are synthetic. Actual local
file/ACL observations are labeled separately. No source license, production
account, model, Feishu recipient, phone receipt or deployed server is accepted.

## Actual local host binding: independent read-only post-state verified

On 2026-09-12, E verified its retained branch clean at
`d4d1225811fd44f6fc7c39259beaabc85ab0e144`, then ordinarily fast-forwarded to
**`e690b61358e4216dfca574a6d58b9c9251edaf0d`**. The only difference was
`V01-TODO.md`; accepted runtime code was unchanged. This task verifies only the
user-confirmed current test-host binding, explicitly without sending or a new
phone-test start. The scoped C transcript corroborated the source, helper checks
and missing fields. M attributed C's maintenance claims to handoff
`msg_91a73a5fc9da` at 10:14:56 UTC and successful completion
`msg_5120f422dca4`. The null-only update and preservation of other pre-update
bytes are **C-reported maintenance**, not an E observation of that earlier state.

E inspected only the approved configuration and its required protected-path
metadata through the accepted helpers:
`C:/Users/DW/AppData/Local/oil-agent/private/feishu-c1/config.json`.
All comparisons remained in memory; output contained only field names, booleans
and fixed check status/exit values. The actual file is a bounded, single-link
regular file without a reparse point, owned by the current Windows user, with
exactly the current user and SYSTEM allowed FullControl. The private directory
has ACL inheritance disabled; the file itself inherits its restricted ACL, so E
does **not** claim the file's inheritance flag is disabled. The accepted path/ACL
verifier passed without repair, and the strict configuration schema was valid.
The configured `host_binding` exactly matched the actual machine name, which
matched the user's explicitly approved current host; no host identifier is copied
here. No configuration value or credential was printed or written.

An inline `uv run --offline --locked --no-sync python -` command loaded the actual
configuration with `load_private_config`, compared the host against Windows
`GetComputerNameW` in memory, and invoked each existing CLI command **once** using
the locked environment's `sys.executable`:

```text
python -B -m oil_agent.runtime.c1_private check
python -B -m oil_agent.runtime.c1_private inject-check
```

Both returned **exit 2**, `NOT_CONFIGURED`, `start_trigger=NOT_AUTHORIZED`, and
exactly `tenant_key`, `recipient_open_id` as missing fields; stderr was empty.
The surrounding verification exited 0. `inject-check` exercised the real fixed
isolated `python -I -m oil_agent.runtime.c1_product` child and compared its exact
redacted response; no child, ACL or configuration double was used. E compared
bounded bytes before and after these checks in memory: unchanged. This supports
read-only E verification and the observed post-state, not reconstruction of C's
earlier write or a claim of crash-atomic maintenance.

Verdict: **ACTUAL LOCAL HOST-BINDING / LOADING / ISOLATED INJECTION VERIFIED**.
Tenant and personal recipient remain missing, and this creates no executable
provider permission. The previous phone window remains expired with no new
start trigger. Product API calls, model tokens, sends and added product cost are
**0**; live receipt API usage remains unknown/null. No private write, broader test,
build, SQL, Docker, host service or provider operation occurred. Platform, phone,
login, callback, deployment and production acceptance remain outside this result.

## Final C1 binding: bounded local code, tests and package members accepted

On 2026-09-12, E independently accepted the bounded local scope of I delivery
**`bfe0209f882f2ffb92fcfc4ab1f651e4541a36cd`**, with exact code/test/build source
**`e98d4a69a2e317b8f573f1c868571dd66fccd1e3`**. E verified its clean retained
branch at `723fbf2da4ee8da99ab8c24e27c57cda053e14c4` and ordinarily fast-forwarded
to that delivery. The exact I remote matched. `git merge-base --is-ancestor`
passed for the retained E checkpoint, source, C mapping
`3dd8cb43c19fac00a6d1099baa4a8f28f3d63671`, E fixture
`8fbea024aabd1ff6ae77c2f2514fee2f53f1662e`, I glue
`d842b7b43c2f6ed91198a3e3695650db3b2a8cfe`, and M board
`eeaf925c6169793f867e5f2a0391265f1fb8ac65`.

`git diff --name-status` from source to delivery returned only
`e2e/runtime-checks.md` and `config/integration-handoff.md`; the corresponding
exclusion diff and `git diff --check` passed. C's five mapping paths match its
exact commit, the entire E entry test file matches `8fbea024`, and bootstrap
plus its factory test match `d842b7b`. From the prior E checkpoint, all changes
are confined to the five C mapping paths, the sole board and I handoff; no
nonallowlisted source drift or later I code change was found. Original positive
and negative entry assertions remain intact; E changed no test or domain code.

### Independent commands and results

```powershell
uv run --offline --locked --no-sync pytest tests/integration/test_c1_entry.py tests/integration/test_bootstrap_factory.py -k 'c1_entry or offline_factory' -q --tb=short
uv run --offline --locked --no-sync pytest tests/unit/runtime/test_c1_tenant_binding.py -q --tb=short
```

Actual results: **65 passed, 13 deliberately deselected, 0.91 seconds, exit 0**;
**19 passed, 0.46 seconds, exit 0**. The first selection retains the existing
Starlette/AnyIO `BlockingPortal` deprecation warning. The 19 binding cases use
Windows TEMP synthetic files and **mocked ACL verification**, with real local
exclusive-handle/file operations; they do not verify the actual private file's
ACL. No broader suite, dependency sync, build or SQL test was run.

The bounded review and cases confirm strict internal selected-result validation,
exact app/host/window/config revalidation in the parent, and explicit opt-in
binding. The Windows handle is exclusive and opens an existing file without
following a reparse point. A matching existing tenant is a no-op; a different
nonempty tenant or changed configuration is preserved and rejected. Only an
unset tenant value is changed, preserving other fields. Ordinary output stays
redacted, default probe does not write, and local binding failure does not
automatically query again. The internal selected-result mode rejects a terminal
stdout. **In-place write failure is not crash-atomic:** the fsync-failure case
returns binding-failed while proving bytes have already changed; a failure can
leave changed or unconfirmed bytes and does not establish rollback or a receipt.

### Existing package members, read in memory only

Source paths and exact artifact paths were checked before archive access. I's
single existing `uv build --offline` output at `e98d4a6` was read from:

- `C:/Users/DW/AppData/Local/Temp/oil-agent-i-ctx-8394797ac280/dist/oil_agent-0.1.0-py3-none-any.whl` (185696 bytes).
- `C:/Users/DW/AppData/Local/Temp/oil-agent-i-ctx-8394797ac280/dist/oil_agent-0.1.0.tar.gz` (782516 bytes).

An inline Python command through `uv run --offline --no-sync --locked python -`
used `zipfile`/`tarfile` in-memory member streams, a 262144-byte per-member bound,
and `git show e98d4a69a2e317b8f573f1c868571dd66fccd1e3:src/oil_agent/<member>`.
The selected relative members in each archive were `runtime/c1_execution.py`,
`runtime/c1_private.py`, `runtime/c1_product.py`, `runtime/permissions.py`,
`runtime/c1.py`, `channels/tenant.py`, `channels/tenant_token.py`, and
`bootstrap.py`. Result: **16/16 LF-normalized matches, 0/16 raw Git-blob matches,
exit 0**. Each package member contains Windows CRLF where the Git blob uses LF;
normalizing CRLF to LF accounts for the complete difference. This is selected
member source correspondence, not whole-archive byte equality or installed
runtime evidence. Nothing was extracted to disk, installed, rebuilt or modified.

No domain defect was reproduced in this scope. The 21 C1 SQL cases remain
**NOT EXECUTED**, and the 13 factory PostgreSQL cases were deliberately unselected;
the known unavailable-engine observation was not reprobed. Real app/tenant/self/
host bindings, durable execution scope and approved database are not established
by these synthetic checks. No actual private config/helper, credentials, API,
database, container, host or shared resource was accessed. Actual product calls,
model tokens, sends and added product cost are **0**; live API usage remains
**unknown/null**. The explicit 2026-09-12 start `08:43:15.149Z` and fixed expiry
`09:13:15.149Z` remain expired, with no inferred new permission. Acceptance is
**LOCAL CODE/TEST/SELECTED PACKAGE EVIDENCE ONLY**; platform, phone, login,
callback, deployment and production acceptance remain unexecuted.

## C-core and I factory: bounded local checks accepted, binding delta excluded

After M explicitly extended this finite task to I's exact glue candidate,
E accepts the tested local C-core/factory scope at I
**`d842b7b43c2f6ed91198a3e3695650db3b2a8cfe`**, with C core
`1a699c7713ea4c62b5cd81b4e47e1c6909064042` and E fixture/regression source
`8fbea024aabd1ff6ae77c2f2514fee2f53f1662e`. E first committed and pushed its
fixture changes, verified the exact E remote, and ordinarily merged the exact
I glue into merge checkpoint `c57a06970843912e2c57b23cd1b5c717d1fe29a4`.
The I remote independently returned the full `d842b7b` SHA. This is not final
combined C1 acceptance or package/build evidence.

The I delta is confined to `src/oil_agent/bootstrap.py`, its owned factory test
and `config/integration-handoff.md`. Its new lookup factory revalidates Settings,
constructs only the C Runtime and D tenant-read adapter, binds the adapter to
the current app reservation callback, reads only the explicit C1 application
secret, and disposes on construction failure. It does not install send, OAuth,
source, report or fixture-provisioning services. C runtime/storage bytes remain
equal to exact `1a699c`; E's complete entry test file remains equal to `8fbea024`.
A read-only AST comparison preserved all 16 original factory test functions and
parameterizations. E authored no factory or C-domain change.

The independent command on merge checkpoint `c57a069` was:

```powershell
uv run --offline --no-sync --locked pytest tests/integration/test_c1_entry.py tests/integration/test_bootstrap_factory.py -k 'c1_entry or offline_factory' -q --tb=short --junitxml=e2e/runtime-artifacts/c1-shared-owner-factory.xml
```

Result: **65 passed, 13 deliberately deselected**, zero failures/skips, 0.86
seconds, exit 0: all 45 E entry cases plus 20 offline factory cases. The existing
Starlette/AnyIO `BlockingPortal` alias deprecation warning remains. The 32 C
app-scope cases previously passed once in the 77-case intermediate selection;
they were not rerun for factory-only changes. These selections overlap and must
not be summed as a final suite total. Final evidence `git diff --check` passed.

No domain failure was reproduced in these bounded checks. C's separately
delivered bind-if-unset delta `3dd8cb43c19fac00a6d1099baa4a8f28f3d63671` was not
adopted or inspected, as directed by M. Its parent write behavior, failure states,
final combined integration and build require an authorized candidate and separate
review. The 21 C1 PostgreSQL cases and 13 factory PostgreSQL cases remain
**NOT EXECUTED**; no SQL guard or unknown engine state was bypassed. All inputs
and HTTP effects here were synthetic; actual product calls/sends/model tokens/
added product cost are **0**, live usage remains unknown/null, and the expired
phone window is unchanged. No real private file or platform was accessed.

## C shared app owner: intermediate review and E fixture adaptation

E ordinarily adopted exact I intermediate
`775308f7ded755da410044f8634b2e5f11a6ff23` from its clean retained
`5aa4219fd09473e7ab6f645289e00de0fde3ec85` branch on 2026-09-12. The exact I
remote matched, and ancestor checks confirmed E `5aa4219` and C source
`1a699c7713ea4c62b5cd81b4e47e1c6909064042`. This checkpoint precedes I factory
glue and is **not final factory or combined-candidate acceptance**.

Before editing any fixture, the unchanged 26 entry cases produced **26 setup
errors**, 5.44 seconds, pytest exit 1: constructing `C1Permission` failed because
the new required `app_request_approval_id` was absent. No entry, runtime, database
or transport effect occurred. This reproduces an intentional required contract
change, not a domain failure or missing real credentials.

E changed only the existing synthetic `entry_scope` fixture to supply a distinct,
stable application-window approval, its explicit reference from the full send
permission, and `app_request_permission` in the stdin envelope. Application,
host, credential reference, exact start/expiry, budget reference, twenty-request
limit and zero-fee bound match the same full permission. A lookup read scope is
added only by the explicit synthetic query fixture; a send permission alone does
not implicitly grant tenant read. The original 26 tests then passed unchanged.

Nineteen bounded E cases were added in the same existing entry test file:

- Ten parent/product boundary cases reject an absent app permission, absent
  owner link, replaced owner, differing active window or differing budget before
  child/factory effects. Invalid input and binding-mismatch results remain redacted.
- Eight parent/product query cases require explicit tenant-read permission and
  an active window, and reject a supplied full send permission in query mode.
- One public product query case connects the actual C Runtime and D transport
  through a patched fixed bootstrap target and mocked HTTP/repository reservation.
  Both token/query operations reserve under the same app owner before their two
  synthetic wires; no sender, recipient provisioning, OAuth, source or model
  service is available. The response has no tenant/receipt/usage disclosure and
  disposal runs once. This tests call flow, not durable SQL accounting or I glue.

Bounded source inspection confirmed full permissions require exact app/window/
budget matching, runtime checks compare constructed scopes, lookup/send
reservations reuse the app approval in the existing ledger, and first-exercise
identity is keyed by app approval rather than a replaceable full-send approval.
The transactional budget and first-subject claims still require PostgreSQL.

### Actual intermediate commands and results

All commands used the existing environment with offline/no-sync flags:

```powershell
uv run --offline --no-sync --locked pytest tests/integration/test_c1_entry.py -q --tb=short --junitxml=e2e/runtime-artifacts/c1-shared-owner-entry-red.xml
uv run --offline --no-sync --locked pytest tests/integration/test_c1_entry.py -q --tb=short --junitxml=e2e/runtime-artifacts/c1-shared-owner-fixture-green.xml
uv run --offline --no-sync --locked pytest tests/integration/test_c1_entry.py tests/unit/runtime/test_c1_app_scope.py -q --tb=short --junitxml=e2e/runtime-artifacts/c1-shared-owner-intermediate.xml
```

Results: **26 setup errors / 5.44 seconds / exit 1** before changes; **26 passed /
0.73 seconds / exit 0** after the fixture-only update; **77 passed / 0.81 seconds /
exit 0** after the focused additions (45 E entry cases plus 32 C app-scope cases).
The final selection had zero failures, skips, deselections or warnings. One
initial Ruff import-order finding was corrected; final `uv run --offline
--no-sync --locked ruff check tests/integration/test_c1_entry.py`, `ruff format
--check` with the same prefix, and `git diff --check` passed. A read-only Python
AST comparison against `5aa4219` confirmed all seven original non-fixture
functions, including every original test and parameterization, remain unchanged.

C's reported 115 owner checks were not rerun; 21 PostgreSQL cases remain
**collected only / NOT EXECUTED**, with no new collection or Docker probe by E.
No private data, real child, database, provider, phone or host operation ran.
Product calls, sends, model tokens and added product cost remain **0**; live
usage stays unknown/null and the expired phone window is not renewed. C's
separate bind-if-unset delta is excluded and requires an authorized candidate.

M subsequently authorized exact I factory glue
`d842b7b43c2f6ed91198a3e3695650db3b2a8cfe` for ordinary adoption after E commits
this fixture increment. Its bounded acceptance is recorded above; this
intermediate result alone accepts no factory.

## D tenant transport accepted: isolated transport scope only

On 2026-09-12, E independently accepts the D transport increment in exact I
candidate **`d4414f9a3b24dc104e2f622ee0391f4ac811811a`**, containing D source
**`da65fb1f2f80a455c058e3107a3df3964c22fbd5`**. This is source/isolated transport
test evidence only. C is still implementing the shared app-window budget and
runtime entry; neither that implementation nor a combined C/I candidate is
accepted by these results. No real tenant identity, API permission, platform
receipt, phone display or production behavior is established.

E verified its clean retained branch at
`a9264158e5ec64983f700d8c0a68373fff7f5be8` and ordinarily fast-forwarded to the
exact I candidate. `git merge-base --is-ancestor` passed for accepted baseline
`fe4b76c2f8b1f17130bd442812cbc046eed1f325`, D `da65fb1`, M
`b6dd9c43cce97a6c621ef1cf7f8f6ad14aa33924` and E `a926415`. The independent
`gh api repos/songconmaisaix31-design/oil-agent/git/ref/heads/songconmaisaix31-design/oil-v01-i --jq '.object.sha'`
query returned the exact full candidate SHA.

### Ownership and bounded source review

The baseline diff contains only M's `V01-TODO.md`, E's existing evidence and D's
six paths: `channels/C1.md`, `channels/__init__.py`, `channels/feishu.py`, new
`channels/tenant.py`, new `channels/tenant_token.py` (under `src/oil_agent/`), and
new `tests/unit/channels/test_tenant_lookup.py`. An exclusion-based
`git diff --exit-code` proved every other tracked path unchanged. Separate
zero-diff checks matched integrated channel code/new tests to D `da65fb1`, the
board to M `b6dd9c43`, and prior E evidence to `a926415`. The complete original
`test_channels.py` and `test_c1.py` files and common channel guards are byte-equal
to accepted `fe4b76c`: no original assertion was edited or removed.

Inspection of the bounded diff and the unchanged `ProviderHTTP` confirmed:

- `FeishuTenantLookup` requires a callable request-authorization hook. Before
  each token POST and tenant GET, it awaits a nonempty string reservation or
  fails before that request. This is a transport contract; the tests use a
  synthetic hook and do not prove C's durable ledger implementation.
- Both routes use fixed `https://open.feishu.cn/open-apis`: token acquisition at
  `/auth/v3/tenant_access_token/internal`, lookup at `/tenant/v2/tenant/query`.
  There is no endpoint parameter or send method. Existing HTTP behavior disables
  redirects and environment proxies, bounds connect time/connections/body size,
  and has no retry loop. The outer deadline also bounds authorization waits.
- Only validated `data.tenant.tenant_key` is returned: 1-160 ASCII identifier
  characters, strict integer success code, and the expected nested objects.
  Display IDs, configured fallbacks and raw responses do not become identity.
  No private configuration or recipient authorization is written or inferred.
- Token acquisition/cache/expiry handling moved from `FeishuChannel` into
  `FeishuTenantToken`, reused by sending and lookup. A warm lookup reserves only
  its actual GET; token invalidation permits refresh on a later explicit call,
  without an automatic retry. Ordinary `require_app`, send authorization,
  recipient/revocation, fixture isolation and UNKNOWN handling remain guarded.
- Lookup errors retain classified service codes with fixed redacted messages.
  Reservation failure, response loss, invalid data and redirects cannot expose
  provider messages or synthetic secret canaries through the reported error.

### Actual independent commands and results

The documented selections ran with `--offline --no-sync --locked` against the
existing environment. No dependency resolution/download or environment sync was
requested; HTTP transports and credentials in these tests are explicit doubles.

```powershell
uv run --offline --no-sync --locked pytest tests/unit/channels/test_tenant_lookup.py -q --junitxml=e2e/runtime-artifacts/tenant-transport-new.xml
uv run --offline --no-sync --locked pytest tests/unit/channels/test_channels.py tests/unit/channels/test_c1.py -q -k 'default_off or acceptance_has or transport_loss or classified_provider or revocation or fixture_requires or expired_token or trial_recipient or malformed_recipient or c1_http or c1_exhausted or c1_authorization_revoked or c1_request_gate or c1_token_expiry' --junitxml=e2e/runtime-artifacts/tenant-transport-original.xml
```

Results respectively: **34 passed**, 0.27 seconds, exit 0; **36 passed,
56 deliberately deselected**, 0.32 seconds, exit 0. Both had zero failures,
skips and warnings. These are two bounded selections, not a full-suite result.
`git diff --check` also passed. E authored no test or domain changes.

No reproduced transport defect remains within this scope. C's immutable common
budget, reservation persistence and runtime/private entry integration require
their own exact integrated candidate and independent acceptance. No claim is
made that this lookup transport alone supplies a complete executable permission.

The existing missing-Docker-pipe observation below stands without another probe;
the eleven C1 PostgreSQL cases remain **NOT EXECUTED**. This task ran no build,
full suite, PostgreSQL, Docker, private helper, host operation or real HTTP call.
The expired phone window is not renewed; the board's later App ID comparison is
C/M-reported configuration evidence, not a fresh E private-file observation.
Actual product source/model/Feishu calls, sends, model tokens and added product
cost are **0**. The live API usage metric remains **unknown/null**; synthetic
per-test call counts are not live usage or platform/phone evidence.

## E PostgreSQL resource preflight: unavailable engine, no startup

On 2026-09-12, E verified the retained repository
`C:/Users/DW/orca/workspaces/oil-agent/oil-v01-e`, branch
`songconmaisaix31-design/oil-v01-e`, clean worktree and accepted delivery
`fe4b76c2f8b1f17130bd442812cbc046eed1f325`. This finite task inspected ownership
and the narrow SQL test prerequisites; it did not start or test a database.

### Resource identity and actual read-only observation

The existing board, `deploy/compose.yaml`, `deploy/compose.e-test.yaml` and prior
E evidence consistently identify the retained development test resource:

| Field | Recorded E scope; current engine state is not verified |
| --- | --- |
| Compose project / service | `oil-agent-e` / `postgres` |
| Container name | `oil-agent-e-postgres-1` |
| Exact container ID | `b3c3a345428590922eb8e628a996dd634cb3333e5f0c86f588eede8fb7101cab` |
| Retained volume | `oil-agent-e_postgres-data` mounted at `/var/lib/postgresql/data` |
| Compose files | This E worktree's `deploy/compose.yaml` and `deploy/compose.e-test.yaml` |
| Local port / database / user | `127.0.0.1:55434` / `oil_e_test` / `oil_e_test` |
| Image | `postgres:16-alpine@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb` |
| Resource limits in Compose | 128 MiB, 0.5 CPU, 64 PIDs, 64 MiB shared memory |

Historical evidence says the exact container was running when the engine pipe
disappeared; its last interrupted UUID-schema cleanup remained unverified.
Historical stopped states must not be substituted for that later unknown state.

The actual bounded commands ran through `uv run --locked python -`, with
`subprocess.run(..., capture_output=True, timeout=15)` for each Docker command:

1. `docker context inspect desktop-linux --format '{{json .Endpoints.docker.Host}}'`
   returned exit **0**, confirming only the configured local endpoint
   `npipe:////./pipe/dockerDesktopLinuxEngine`.
2. `docker --host npipe:////./pipe/dockerDesktopLinuxEngine container inspect
   --format <selected nonsecret fields> b3c3a345428590922eb8e628a996dd634cb3333e5f0c86f588eede8fb7101cab`
   returned exit **1**: `open //./pipe/dockerDesktopLinuxEngine: The system cannot
   find the file specified`. Selected fields were ID/name/image, four Compose
   ownership labels, state/exit/OOM, named mounts and port bindings; environment
   values were excluded. The Python wrapper exited 0 after reporting that actual
   Docker failure; it was not a successful container verification.

No retry, volume inspection through the unavailable engine, global enumeration,
daemon restart, container start/stop, removal or cleanup followed. Current
container labels/state, retained volume and interrupted-schema cleanup remain
**UNVERIFIED**. Ownership above is historical/configuration evidence, not fresh
engine proof. M received this result and the proposal before any startup.

### Exact SQL scope and fixture prerequisite

The existing target is `tests/unit/storage/test_c1_storage.py`: five single
cases plus six authorization-change variants, totaling the previously collected
**11**. They cover concurrent atomic outbox preparation, rollback, shared
twenty-request/three-send caps, user/permission/grant/host/expiry/person changes,
UNKNOWN recovery/fencing and accepted-send/callback separation. No cases were
collected again or executed in this preflight.

The exact existing test command is:

```powershell
uv run --locked pytest tests/unit/storage/test_c1_storage.py -q --tb=short --junitxml=e2e/runtime-artifacts/c1-postgres.xml
```

This command is **NOT READY FOR E EXECUTION**: its existing `repository` fixture
in `tests/unit/storage/conftest.py` requires `OIL_TEST_DATABASE_URL` bound to
`127.0.0.1:55431/oil_c_test`, user `oil_c_test`, and rejects the E database.
An absent URL skips; skips are not SQL evidence. E will not inject an E URL into
that C-only guard, weaken the guard, or inspect/start/use C's resource.

The narrow E-resource proposal is an E-owned integration adapter that reuses
the unchanged eleven C test assertions and `c1` fixture, binding `repository`
to the existing `e_repository` fixture. That fixture requires
`OIL_E_TEST_DATABASE_URL` with driver `postgresql+psycopg`, exact E local scope
`127.0.0.1:55434/oil_e_test` and user `oil_e_test`; it creates only a fresh
`e_acceptance_<UUID>` schema, applies real migrations, bounds connection setup
to five seconds and statements to five seconds, and removes only that test's
new schema. An E adapter is **not yet implemented**. This is a test-harness
preparation gap, separate from the unavailable engine and live authorization.

### Proposed next resource actions, not executed

After the operator/M makes the existing local engine available, recheck the
same exact container's ID/project/service/worktree/config labels, mount/image,
port and state. Inspect only the named volume with:

```powershell
docker --host npipe:////./pipe/dockerDesktopLinuxEngine volume inspect oil-agent-e_postgres-data --format '{{.Name}} {{.Driver}} {{json .Labels}}'
```

Confirm `127.0.0.1:55434` belongs to the same E resource (or is free if stopped),
retain all old data/schema evidence, and require the explicitly supplied E
development test credential without printing or harvesting environment values.
If and only if the verified container is stopped, the proposed narrow startup
is:

```powershell
docker --host npipe:////./pipe/dockerDesktopLinuxEngine start b3c3a345428590922eb8e628a996dd634cb3333e5f0c86f588eede8fb7101cab
```

There is no full Compose startup, recreation, migration of retained business
schemas, new volume or trial host in this proposal. Only after resource proof
and the E test-fixture adapter exist can the eleven assertions run against fresh
E test schemas; report actual results and inspect exact resource state before
any bounded owner stop. Existing interrupted schemas and volumes must remain
untouched. Ordinary synthetic development tests do not require a live phone
window, but they cannot establish a real trial host or execution permission.

The phone window has expired and is not renewed. Product source/model/Feishu
requests, sends, model tokens and added product cost remain **0**; PostgreSQL
C1 verification, platform/phone receipt and production remain **NOT EXECUTED**.
Only this existing E evidence file changed; no business code, test guard,
credential, Docker resource or unique board was modified.

## C1 final candidate accepted: bounded code and local package evidence only

E independently accepts I candidate and reported single-build source
**`ca0a425dc7bcb7b4c7c0c89b16ba8b7842a050db`** for the bounded C1 execution-entry
code/local evidence scope on 2026-09-12. This closes the earlier missing-entry
regression and test-harness correction in this scope. It does not accept a live
execution, PostgreSQL transaction/concurrency behavior, platform/phone receipt,
login, deployment or production.

The retained E worktree was clean at
`cdf3f8a57f2a678110133410735d05eb7d53baf5` before an ordinary fast-forward to
the exact candidate. `git merge-base --is-ancestor` passed for original RED
`2ca3c87577b7b0283e69d475f7822a7623622923`, E bounded tests
`618e173cbb5549b55662349cbe9f9b29394e2f9e`, E harness correction `cdf3f8a`, C
`7167c63d61a9501c9a69e4a112d9c4a64e86911b`, I factory evidence
`1498863514453c15b26617514626f0d547149d6a` and M
`0a38be78b606e62f6de36a17a98a81d1ecbd4ebd`. The remote query
`gh api repos/songconmaisaix31-design/oil-agent/git/ref/heads/songconmaisaix31-design/oil-v01-i --jq '.object.sha'`
independently returned the exact full `ca0a425` SHA.

`git diff --exit-code cdf3f8a57f2a678110133410735d05eb7d53baf5 HEAD --
tests/integration/test_c1_entry.py` passed, preserving the complete corrected
assertion file. A read-only Python AST/source-segment comparison additionally
confirmed that `test_send_once_reaches_only_fixed_isolated_product_entry` is
exactly unchanged from original RED `2ca3c875`. `git diff --exit-code
7167c63d61a9501c9a69e4a112d9c4a64e86911b HEAD -- src/oil_agent
config/c1-preparation.md tests/unit/runtime/test_c1_execution.py` passed: C's
application source and selected entry contract/test bytes remain unchanged.

### Independent targeted test result

```powershell
uv run --locked pytest tests/integration/test_c1_entry.py tests/integration/test_bootstrap_factory.py -k 'c1_entry or offline_factory' -q --tb=short --junitxml=e2e/runtime-artifacts/c1-entry-final-candidate.xml
```

Result: **38 passed, 13 deliberately deselected**, zero failures/skips, 0.58
seconds, exit 0. This comprises all 26 entry cases and 12 offline factory cases.
The existing Starlette/AnyIO deprecated `BlockingPortal` alias warning remains.
The 13 deselected factory cases require PostgreSQL; the separate 11 new C1
PostgreSQL regressions remain **NOT EXECUTED**. C's unchanged 47-case scope was
not rerun. No full suite, CI, new build, container or real private helper ran.

The tests cover the fixed isolated parent command and environment, strict input
and binding rejection, explicit product execution, authorization before prepare
and again before send, one send/disposal, UNKNOWN handling and restricted receipt
output. The actual product wrapper also constructs the existing guarded C1
channel through the real bootstrap assembly with synthetic engine/bindings;
ambient/configured factory overrides cannot select another factory. Ordinary
rule/web configuration guards and the production gate remain asserted.

### Existing build artifacts: bounded in-memory verification

Only these two existing files were opened, without extraction, installation or
rebuilding:

- `C:/Users/DW/AppData/Local/Temp/oil-agent-i-ctx-1b00956b6bcd/dist/oil_agent-0.1.0-py3-none-any.whl`
  (177482 bytes).
- `C:/Users/DW/AppData/Local/Temp/oil-agent-i-ctx-1b00956b6bcd/dist/oil_agent-0.1.0.tar.gz`
  (747984 bytes).

A one-off `uv run --locked python -` script used `zipfile.ZipFile.read` and
`tarfile.TarFile.extractfile` as in-memory reads, with a 262144-byte per-member
ceiling and regular-file checks for tar members. It compared each listed member
against `git show ca0a425dc7bcb7b4c7c0c89b16ba8b7842a050db:src/oil_agent/<path>`.
Wheel entries have prefix `oil_agent/`; source-distribution entries have prefix
`oil_agent-0.1.0/src/oil_agent/`. The six members below were checked in each
archive, for 12 bounded member comparisons; no other package content is accepted
by this inspection.

| Relative member | Bytes in each archive | Git blob bytes | CRLF count in each archive |
| --- | ---: | ---: | ---: |
| `runtime/c1_execution.py` | 5634 | 5490 | 144 |
| `runtime/c1_private.py` | 7550 | 7356 | 194 |
| `runtime/c1_product.py` | 3889 | 3789 | 100 |
| `runtime/c1_config.py` | 4175 | 4066 | 109 |
| `runtime/c1_acl.ps1` | 4423 | 4341 | 82 |
| `bootstrap.py` | 13818 | 13551 | 267 |

All 12 raw comparisons to Git blobs are **unequal**. All 12 comparisons become
**equal** after only `bytes.replace(b"\r\n", b"\n")` on each side: the complete
observed difference is Windows CRLF versus Git LF. The script exited 0. This
links the selected packaged source contents to exact candidate `ca0a425`; it is
not raw Git-blob equality, full-archive reproducibility or installed runtime
evidence. I supplied the single-build provenance; E inspected the existing
outputs independently and produced no new build/hash/manifest system.

### Authorization and remaining real-evidence limits

The latest user task and M board supersede historical no-start statements below:
M verified the explicit user start in D's structured transcript at
**2026-09-12T08:43:15.149Z**, with fixed expiry
**2026-09-12T09:13:15.149Z**. E did not reread private data or manufacture an
executable permission from that trigger. Exact app/tenant/self/host bindings,
an approved PostgreSQL URL and durable execution scope are still missing; the
window cannot be inferred or renewed. The earlier older-helper ACL denial did
not reproduce with committed C code according to the current task/board; no
current ACL defect is inferred or repaired here.

All test inputs, permissions and delivery receipts in this acceptance remain
synthetic. This E task made **0 product calls, 0 model tokens, 0 sends and 0 added
product cost**. An eventual live receipt's `api_requests=null` remains unknown,
never measured zero. PostgreSQL, Feishu platform/phone receipt, login and
production evidence are **NOT EXECUTED**. I adoption of E's evidence commit is
the remaining handoff; this acceptance does not create business approval.

## C1 entry harness correction: 26 focused synthetic cases pass

On 2026-09-12, E checked its retained branch/worktree was clean at
`618e173cbb5549b55662349cbe9f9b29394e2f9e`, verified the authorized ancestors,
and ordinarily fast-forwarded to I's committed candidate
`56e1be163ab8c6faeefc6e858b9186a4b9c2c7d6`. That candidate includes C
`7167c63d61a9501c9a69e4a112d9c4a64e86911b`, E's original RED history and M
`0a38be78b606e62f6de36a17a98a81d1ecbd4ebd`. No domain source was changed.
This section records a test-harness repair, not final acceptance of I's next
integrated candidate, a real send, or a new business authorization.

Three harness mismatches were observed sequentially, without masking failures:

1. Unchanged E tests reproduced **1 failed, 25 passed** on exact I `56e1be1`:
   product calls were empty. E set `sys.argv` then called `c1_product.main()`;
   the actual API intentionally treats no arguments as preparation, while the
   module boundary forwards `sys.argv[1:]` explicitly. Both positive and nine
   negative product cases now call `main(["send-once"])`, and the misleading
   `sys.argv` override was removed. This tests the supported execution path.
2. With explicit invocation, **1 failed, 25 passed** remained: the operation
   sequence included an additional `authorize` after `prepare`. The assertion
   now requires `factory, authorize, prepare, authorize, send, dispose`, thereby
   verifying permission before preparation effects and again before sending.
   No production authorization check was removed or bypassed.
3. With that sequence required, the single positive case still failed at
   `assert result == 0`: actual result was **3 / C1_UNKNOWN**. Source inspection
   confirmed the product validates `Delivery` through `model_dump`; E's old
   `SimpleNamespace` lacked that method. The sender double now returns the
   existing validated `Delivery` DTO with synthetic delivery/intent/recipient
   IDs, revision, attempt and aware acceptance/update times. The expected
   accepted receipt and UNKNOWN safety semantics remain unchanged.

The exact positive parent fixed-child assertion from RED commit
`2ca3c87577b7b0283e69d475f7822a7623622923` is unchanged. All 26 existing cases
remain, with no additional audit scope. The nine product-denial cases now pass
at the actual explicit send-once API, so their former preparation-only passes
are superseded. The final positive case reaches the real fixed product wrapper
and a patched bootstrap target despite hostile ambient factory settings; the
real bootstrap assembly remains I's separate integration check.

All commands used the same unchanged application candidate:

| Command | Actual E result |
| --- | --- |
| `uv run --locked pytest tests/integration/test_c1_entry.py -q --tb=short --junitxml=e2e/runtime-artifacts/c1-entry-harness-repro.xml` | 1 failed, 25 passed; 0.65 seconds; pytest exit 1 |
| `uv run --locked pytest tests/integration/test_c1_entry.py -q --tb=short --junitxml=e2e/runtime-artifacts/c1-entry-explicit-repro.xml` | 1 failed, 25 passed; 0.64 seconds; pytest exit 1 |
| `uv run --locked pytest tests/integration/test_c1_entry.py::test_product_uses_fixed_factory_and_existing_runtime_order -q --tb=short --junitxml=e2e/runtime-artifacts/c1-entry-delivery-repro.xml` | 1 failed; 0.62 seconds; exit 1 |
| `uv run --locked pytest tests/integration/test_c1_entry.py -q --tb=short --junitxml=e2e/runtime-artifacts/c1-entry-harness-green.xml` | **26 passed**, 0.49 seconds; exit 0 |
| `uv run --locked ruff check tests/integration/test_c1_entry.py` | Passed |
| `uv run --locked ruff format --check tests/integration/test_c1_entry.py` | Passed; one file already formatted |
| `git diff --check` | Passed |

Disposition: the reproduced failures were E harness errors; these bounded checks
found no remaining executable product defect. I must re-integrate this correction
and verify its fixed bootstrap seam/build, followed by E acceptance of the exact
final candidate. I's later `1498863514453c15b26617514626f0d547149d6a` was reported
by M as additional I-owned factory evidence with unchanged C source; E did not
adopt it or rerun its checks in this correction task.

All permissions, bindings, URLs, deliveries and receipts used here are explicitly
synthetic. Private files, actual children, network, database and containers were
not accessed; no full suite, build, CI or old PostgreSQL tests ran. Product
source/model/Feishu requests, sends and external cost are **0**. Real permission
and active start remain absent; PostgreSQL transaction/concurrency behavior,
platform receipt and physical phone display remain **NOT EXECUTED**.

## C1 controlled-entry regression: RED on accepted preparation baseline

On 2026-09-12, E independently reproduced the missing supported execution entry
against unchanged application baseline
`41cfed431d8c8ac882d4cee88267cc20299b3c83`. The new
`tests/integration/test_c1_entry.py` invokes `c1_private.main(["send-once"])`
with an explicit synthetic active permission and PostgreSQL-shaped URL through
bounded-input-compatible stdin. Private loading and the child process are test
doubles; the real private path is disabled and database construction fails the
test if reached. No actual private file, database or provider is accessed.

The positive regression requires exactly one fixed isolated child invocation:
`[sys.executable, "-I", "-B", "-m", "oil_agent.runtime.c1_product", "send-once"]`.
It also preserves the agreed structured input, protected binding injection and
environment allowlist despite hostile ambient factory/Python settings. The
baseline returns `INVALID_COMMAND` and invokes the child **zero** times, failing
`assert len(calls) == 1`. This is an implementation gap, independently of missing
real authorization. A synthetic child UNKNOWN is not a platform response.

Actual commands at the unchanged baseline:

| Command | Result |
| --- | --- |
| `uv run --locked ruff check tests/integration/test_c1_entry.py` | Passed |
| `uv run --locked ruff format --check tests/integration/test_c1_entry.py` | Passed; one file already formatted |
| `uv run --locked pytest tests/integration/test_c1_entry.py -q --tb=short --junitxml=e2e/runtime-artifacts/c1-entry-red.xml` | **1 failed**, 4.19 seconds, exit 1; missing supported entry reproduced |

This RED regression preserves the earlier local-preparation acceptance below;
it does not accept controlled execution. C/I own the entry/runtime repair and
integration, after which E must verify the exact integrated SHA. Real start
authorization, PostgreSQL transaction/concurrency behavior, platform acceptance
and phone receipt remain unexecuted boundaries. This increment reads no private
configuration and makes no claim about its current state. Source/model/Feishu
product calls, sends and external cost are all **0**; no old PostgreSQL tests,
full suite, build, CI, Docker or service startup ran.

### Bounded entry cases and RED handoff

The first minimal RED source commit is
`2ca3c87577b7b0283e69d475f7822a7623622923` (`[skip ci]`), pushed to the retained
E branch and independently confirmed through the exact remote branch reference
before the follow-up cases were added. Its original positive assertion remains
unchanged. The follow-up tests additionally cover:

- Missing explicit start, expired/future windows, protected host/app/tenant/person
  mismatch, non-PostgreSQL URL and extra input keys at both parent and product
  entry, with forbidden child/runtime/database effects and secret canaries.
- Duplicate JSON keys, an oversized stdin document and a non-object envelope.
- A timeout, malformed child output and an UNKNOWN carrying a spurious receipt:
  one attempt only, UNKNOWN exit 3, no receipt and no secret output.
- The fixed bootstrap target, even under hostile ambient factory settings;
  authorization, preparation, one send and disposal in order using a runtime
  double. A synthetic accepted result must preserve its identifier, aware UTC
  timestamp and attempt, with `api_requests=null` (unknown), and cannot claim
  phone receipt or login. These are proposed acceptance checks, not live results.

`uv run --locked pytest tests/integration/test_c1_entry.py -q --tb=short
--junitxml=e2e/runtime-artifacts/c1-entry-red-bounded.xml` produced **5 failed,
21 passed**, 0.61 seconds, exit 1, still against unchanged baseline application
bytes. Four failures show no child reached; the fifth shows no factory/runtime
operations reached because the product entry still runs preparation. The 21
negative cases pass under that blanket refusal and therefore **do not establish
implemented permission validation** until the positive path passes on an exact
integrated candidate. No negative pass is represented as owner-repair acceptance.

Ruff initially requested two line wraps in the added cases; `uv run --locked
ruff format tests/integration/test_c1_entry.py` corrected them. Final
`ruff check`, `ruff format --check` (both through `uv run --locked`) and
`git diff --check` pass. No existing test assertion or domain file was changed.
C/I implementation and exact candidate integration remain pending; real start
authorization is a separate gap, and PostgreSQL/platform/phone evidence remains
unexecuted. No private-file check was repeated for this entry task.

## C1 independent acceptance: LOCAL PREPARATION ONLY

E accepts integrated code **`f86c29e3bc99f9f761ebb32236b2dd37a7800357`** for
the bounded local preparation scope. This includes private structured loading,
offline preview, explicit exercise contracts, guarded channel construction and
the tested runtime control flow. It does **not** accept PostgreSQL transaction/
concurrency behavior, a live sender, platform message acceptance, actual phone
display, real login or an interaction receipt. No real start window exists.

E reused its clean retained branch/worktree, ordinarily fast-forwarding through
I `723100b637a6f514d19f3dddde903f0636be3696`,
`3b41c8b91e2d1bf0d67769bdf81bf0b27f502907`,
`ab86e486c9c07e1961d822615ba003409344bf8f` and finally `f86c29e`.
Explicit ancestor checks passed for M
`7ba4c2f8115775b5e1bbdc5db2e806bb56ef08b0`, C private helper
`611c7a99866de5fa21f6c2f292b31548949bd809`, D preview
`584c9a3b49c549a4602bc32b0a29d0e7261d7425`, C exercise DTO
`fda37c87719c4ef9840fe866308707314c3832e2`, D guarded channel
`5355446d00e23dc64b1cd133ec191cfa0467bad8`, C preview/ACL fix
`76fdb934525815131fea1bffe79e11630d717c2e` and C runtime
`30e90dfee3c885c17c9cf48690a7381111ac4483`.
The public I branch independently matched the full final candidate SHA. E made
no domain repair, changed no existing assertion and added no duplicate intake.

### Actual private file and preview observations

Only the authorized directory
`C:/Users/DW/AppData/Local/oil-agent/private/feishu-c1` and its three named files
were inspected. `Get-Item`/`Get-Acl` metadata showed current-user ownership,
exactly two current-user/SYSTEM FullControl rules and no reparse point for the
directory, `config.json`, `c1-preview.html` and `c1-preview.json`. File sizes were
268, 1618 and 924 bytes respectively. Configuration last-write time was
2026-09-12T06:28:17.8253613Z; preview files were last written at
2026-09-12T06:32:58.5309379Z. E did not print configuration contents/values or
rewrite any private file, run `prepare`/`preview`, or inspect unrelated credentials.

The initial integrated candidate `723100b` reproduced a concrete implementation
gap: both commands below returned `PRIVATE_PATH_UNVERIFIED`, exit **2**. The fixed
ACL script, run in verify mode only, reported `PRIVATE_PATH_UNVERIFIED:unknown_file`.
Its old allowlist rejected the legitimate newly created preview files. This was
reported to M/C immediately, separately from missing application credentials.
No files or permissions were removed/widened to make the check pass.

After I integrated C's exact three-file allowlist at `ab86e48`, E reran:

```powershell
./.venv/Scripts/python.exe -m oil_agent.runtime.c1_private check
./.venv/Scripts/python.exe -m oil_agent.runtime.c1_private inject-check
```

Both returned the expected **exit 2** with redacted status only:
`WAITING_FOR_APPLICATION_CREATION`, `application_state=NOT_CREATED`,
`configuration_status=NOT_CONFIGURED`, `start_trigger=NOT_AUTHORIZED`,
`product_requests=0`, and missing field names `app_id`, `app_secret`, `tenant_key`,
`recipient_open_id`, `host_binding`. This closes the actual old-path rejection.
It describes an application not created, rather than a configured application
awaiting credential disclosure. The fixed isolated child consumes only allowed
C1 fields and cannot turn that status into a runtime, server or sender.

E ran a one-off `uv run --locked python -` static verifier over only the two
authorized preview files. It parsed the JSON, checked the generated test ID and
aware creation time in memory, reconstructed D's shared `create_c1_preview` using
those metadata, and matched the complete card/HTML without printing values.
Independent literal assertions confirmed the approved Chinese title/body,
`演练／非真实行情`, `本阶段只验证消息到达。`, generation-time wording, forwarding
disabled, and `本地预览 · 未发送 · 非飞书客户端截图`. HTML parsing rejected action/
input/link/script/media elements and URL/event-handler attributes; static checks
rejected resource URLs/CSS imports and required the restrictive CSP. Result:
**PRIVATE_PREVIEW_PASS**, exit 0. This is static file evidence, not a browser,
Feishu client screenshot, send timestamp or phone observation; no requests ran.

### Focused commands and evidence

All executions used the existing locked environment; no full suite, CI polling,
Docker, server, database service, live transport or new host was started. Scopes
below overlap across increments and must not be summed as a final suite count.

| Exact command/scope | Actual E result |
| --- | --- |
| At `723100b`: `uv run --locked pytest tests/unit/runtime/test_c1_preparation.py tests/unit/runtime/test_c1_contract.py tests/unit/channels/test_c1_preview.py -q --tb=short` | 40 passed, zero failures/skips, 1.19 seconds; did not establish the actual private-path status |
| At `3b41c8b`: `uv run --locked pytest tests/unit/channels/test_c1.py tests/unit/channels/test_channels.py -q --tb=short -k 'c1 or trial or unknown or revoked'` | 37 passed, 55 deliberately deselected, zero failures/skips, 0.19 seconds; explicit HTTP doubles only |
| At `ab86e48`: `uv run --locked pytest tests/unit/runtime/test_c1_preparation.py -q --tb=short` | 17 passed, zero failures/skips, 0.13 seconds; private-path recheck recorded above |
| At `f86c29e`: `uv run --locked pytest tests/integration/test_bootstrap_factory.py tests/unit/runtime/test_c1_runtime.py -k 'offline_factory or explicit_active_attempt or expired_host or unconfigured_c1' -q --tb=short --junitxml=e2e/runtime-artifacts/c1-local-final.xml` | 15 passed, 13 existing PostgreSQL factory cases deliberately deselected, zero failures/skips, 3.52 seconds; existing Starlette/AnyIO deprecation warning |
| At `f86c29e`: `uv run --locked pytest tests/unit/storage/test_c1_storage.py --collect-only -q` | 11 tests collected, 0.06 seconds; **NONE EXECUTED** |
| Scoped Ruff over changed runtime/service/storage/bootstrap and their focused test files | PASS |
| Git ancestor checks, diff-check and unchanged previously verified private/channel/contract files from `ab86e48` | PASS |

I performed one wheel/sdist build at the accepted candidate. E did not repeat it;
E read only those named artifacts from
`TEMP/oil-agent-i-ctx-8f37913d12ee/dist` and inspected ten scoped C1 source/helper
entries, including `runtime/c1_acl.ps1`, with `zipfile`/`tarfile` in memory.
The first raw comparison to E's `bootstrap.py` worktree bytes failed due to
Windows line endings. Follow-up comparison to the exact candidate Git blobs
showed all ten entries equal after **only CRLF-to-LF normalization**, and wheel
and sdist entries byte-identical to each other. No artifacts or source files
were rewritten, installed or executed; raw equality to Git LF blobs is not claimed.

### Accepted boundaries and remaining limitations

The focused results preserve strict data-only parsing, duplicate/unknown-key and
untrusted-command refusal, fixed isolated child injection, redacted failures,
no-overwrite preview preparation, and ordinary rules/OAuth/callback requirements.
C1 construction requires its explicit permission and C1 secret with no ordinary
secret fallback; it wires one exact app-scoped test recipient and both runtime
authorization hooks. It constructs no source/model, identity, callback, report,
quote or assessment service. Production remains rejected. Original ordinary-mode
factory guard assertions were retained and passed within the ten offline cases.

Contract/control-flow tests cover one declared identity/host, the exact explicit
start trigger, at most 30 minutes, first-one message, at most three attempts,
twenty total API requests and zero new fee. Source inspection shows stable
exercise/outbox identity, current grant/user/start checks, lease fencing, shared
request reservations before token/send HTTP, and no requeue of UNKNOWN or accepted
delivery. Runtime control-flow tests use an explicit repository double, not SQL.
The eleven unexecuted PostgreSQL cases cover atomic outbox creation/rollback,
20-request/3-send reservation caps, changed authorization and lease recovery;
they are **implemented-awaiting-PostgreSQL-verification**, not passed concurrency
or restart evidence. The thirteen existing PostgreSQL factory cases were also not
executed. No SQLite substitute was used, and no database URL was searched for.

No unresolved implementation defect was found in the bounded local preparation
checks after the owner ACL repair. Missing real inputs are separate: the Feishu
application is not created/configured, exact tenant/person/host bindings are blank,
and the user has not triggered `开始手机测试`. The nominal ceilings do not create
a start window or establish free-service coverage. PostgreSQL durability, actual
provider counting/zero-fee coverage, a real platform message ID, phone display and
operator observations remain unverified. Login/callback confirmation, sources,
models, ongoing polling, public ingress and production are outside C1.

Product source requests **0**, model requests/tokens **0**, Feishu API requests
**0**, sends **0**, paid product cost **0**. Development-agent billing is unmeasured.
M retains the unique V01-TODO intake; final governance/evidence adoption requires
only I integration and E's final equality/remote audit if code remains unchanged.

## Current phase: independent real-integration v1.1 acceptance

### R16/R17 final independent acceptance: synthetic code and preparation PASS

Accepted code SHA: **`239baa69b06bf9ede8c71391d12a2cb89e1a1064`**.
This closes the R16 regressions and R17 implementation compatibility failure
recorded below. It accepts the bounded synthetic code and offline deployment
preparation only; it does not accept a deployed trial, real source/model/Feishu
request, phone receipt or production factory. Earlier results below are history.

E's retained clean branch normally fast-forwarded from
`3afa038214309188d26db2448eb5be076d42e7ed` to this exact I candidate.
Public origin I branch independently matched that full SHA. Explicit
`git merge-base --is-ancestor` checks passed for AB
`dea13fa81825f1160ef44187885a98c569375edb`, E `3afa038214309188d26db2448eb5be076d42e7ed`
and M `e2aabc85b8f121381f667691b05fe5805f36e5ee`.
`git diff --exit-code b9a241a HEAD -- tests/integration/test_contextual_guards.py
tests/integration/test_rules_acceptance.py` confirmed unchanged original assertions.
The E deployment script, overlay, Nginx config, wrapper, tests and focused workflow
are unchanged from verified `3afa038`; I changes stay in its environment/runbook/
handoff seams. No domain changes came from E or the coordinator.

E independently inspected exact-run metadata, job steps/logs and downloaded JUnit
ZIP bytes for [complete CI 34669549557](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34669549557)
and [deployment CI 34669549519](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34669549519).
Both completed **SUCCESS** on the accepted code SHA, Ubuntu 24.04 and Python
3.13.13. C and E tests used their separate real PostgreSQL services/schema scopes;
there was no SQLite substitution, xfail or deselection. Existing Starlette/AnyIO
deprecation warnings remain. The focused 70 are also in the 237 integration cases,
and the Windows 106 overlap those scopes; these counts must not be added together.

| Actual command or step | Result |
| --- | --- |
| E local `uv run --locked pytest tests/integration/test_contextual_guards.py tests/integration/test_rules_acceptance.py tests/integration/test_controlled_trial_deploy.py tests/integration/test_deploy_safety.py -q --tb=short --junitxml=e2e/runtime-artifacts/r16-r17-final-focused.xml` | 106 passed, zero failures/errors/skips, 1.52 seconds |
| CI `uv sync --locked`, scenario-corpus validation and scoped Ruff | PASS |
| CI migrate separate C PostgreSQL test service | PASS |
| CI `uv run --locked pytest tests/contracts tests/unit -q --tb=short --junitxml=e2e/core-acceptance.xml` | 375 passed, zero failures/errors/skips, 24.706 seconds |
| CI `uv run --locked pytest tests/integration -q --tb=short --junitxml=e2e/local-acceptance.xml` | 237 passed, zero failures/errors/skips, 31.022 seconds |
| CI `npm ci --ignore-scripts`, `npm test`, `npm run build` in web | PASS; 23 tests; schema, TypeScript and Vite build |
| CI `bash -n deploy/entrypoint.sh scripts/backup.sh scripts/restore-isolated.sh scripts/compose_scope.sh` | PASS |
| CI `docker build -f deploy/app.Dockerfile -t oil-agent-app:ci .` and corresponding web Dockerfile | Both Linux image builds PASS; neither published nor deployed |
| Focused CI `uv run --locked pytest tests/integration/test_controlled_trial_deploy.py tests/integration/test_deploy_safety.py -q --tb=short --junitxml=e2e/controlled-trial.xml` | 70 passed, zero failures/errors/skips, 0.480 seconds; Compose 2.38.2 |
| Focused CI script/test Ruff and `bash -n scripts/trial-start.sh` | PASS |
| Actual digest-pinned Nginx `-t` in read-only, cap-dropped UID 101 container with `--network none` | PASS; authored disposable test certificate/key only; no server or provider request |

The CI-built image IDs are app
`sha256:8a87cb57e1b0970bff3d69ba49cf93ddbfbf466086d55ef18b2852abded2ce35`
and web `sha256:745193f346672694491d4fde38d5739192509636f3e4818766716e5230e71561`.
Image construction and Nginx syntax/key loading do not prove runtime packet
filtering, public certificate trust or an actual callback round trip.

R16's original 21 cases all pass, including the eight first reproduced failures
and preserved denial, planning, drill/training/procedure, conditional, archive,
stale, future and ambiguous controls. Bounded casualty-only negation cannot
satisfy affirmative impact criteria; source quotations remain unchanged. The
approved elapsed-age limit permits the 50-second midnight crossing. This is not
general Chinese semantic coverage. PostgreSQL T05 lower-severity denial correction
still targets original authorized recipients, T18 binds reminders per recipient/
revision, and T27 preserves fixture isolation. The full integration result also
includes 13 shared-factory cases, 17 Jin10 isolated-transport cases, 15 rule/model
cases, 12 OAuth, 12 security and 7 operational-trial cases; their remote replies
are explicitly synthetic and never real provider/phone evidence.

R17 preparation checks pass for internal/separate database resources, explicit
IPv4 pins compatible with direct non-proxy adapters, closed defaults, loopback
HTTPS, callback/SPA configuration, no sensitive proxy access/error logging,
resource limits and readonly cold/retained preflight. Unapproved/changed scopes
fail before activation. The initial Linux failure at E `c557665` is closed by
`3afa038`, whose own focused [CI 34669473354](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34669473354)
also passed 70 checks in 0.602 seconds plus actual isolated Nginx `-t`.
At intermediate I `f8c549b`, [CI 34669364995](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34669364995)
already passed all R16/PG cases, but its sole old E mount-check failure correctly
prevented whole-candidate acceptance. That result is superseded by `239baa6`.

Remaining limits are classified separately:

- **Implemented, awaiting authorized real test:** host firewall/IP/DNS/IPv6
  behavior, TLS trust/callback reachability, trial startup and graceful stopped-
  resource recovery. The new checker uses isolated Docker command doubles;
  Nginx ran only in network-none CI. Automatic activation and new-trial backup/
  restore automation are not supplied; existing backup guards stay unchanged.
- **Missing authorization/inputs:** exact host/TLS setup, source rights and caps,
  model/data-processing approval and spending control, approved first-report
  rubric, exact Feishu test recipient and phone/account/window. The sole intake
  remains M's V01-TODO.md; technical input mappings are in the existing runbook
  and `deploy/controlled-trial.md`. No credentials were inspected or solicited.
- **Unavailable execution environment:** local Docker Linux named pipe is still
  unavailable. Exact old E container
  `b3c3a345428590922eb8e628a996dd634cb3333e5f0c86f588eede8fb7101cab`, volume
  `oil-agent-e_postgres-data` and interrupted schema cleanup remain unverified.
  No daemon restart, unknown-resource inspection, stop, deletion, firewall/network
  mutation or local deployment occurred. Historical stopped-state evidence does
  not establish current state after the later interruption.
- **Intentionally unsupported:** production factory/activation, paid-host purchase
  and public exposure. No unresolved implementation defect is claimed fixed beyond
  the bounded tested scope, and no real accuracy or operating-period acceptance
  is inferred from this report.

Actual product source requests **0**, model requests/tokens **0**, Feishu requests
**0**, sends **0**, paid product cost **0**. Development-agent/CI billing is
unmeasured. This report is an E evidence-only follow-up to the accepted code SHA;
I/M's final documentation merge requires a last code-equality and remote-SHA audit.

### R16 contextual-guard reproduction on accepted unchanged code

E normally merged accepted I `cd6e8d9d87acbde9b844b4568ab2df72e00bab8d`
and M `b51b152` at `61194af8c082518c1f6e119b12792eb48858dfab` before adding
`tests/integration/test_contextual_guards.py`. No application code or existing
test assertion changed. All new material is explicitly synthetic, using one
approved test rubric and no model, provider, database or sender.

`uv run --locked pytest tests/integration/test_contextual_guards.py
tests/integration/test_rules_acceptance.py -q --tb=short
--junitxml=e2e/runtime-artifacts/contextual-guards-baseline.xml` produced
**8 failed, 28 passed, 0 skipped, 2.42 seconds** on Windows Python 3.13.13.
The eight required failures are preserved, without xfail or weakened assertions:

- Attack plus supply interruption followed by unrelated `未造成人员伤亡`, in
  the same clause and in a separate sentence: `ApprovedRules.match` returns None
  in both cases; `guarded_status` returns UNKNOWN instead of OCCURRED in both;
  the actual assessment graph also returns UNKNOWN/routine in both.
- A qualifying publication at `2026-09-12T23:59:30+08:00` processed at
  `2026-09-13T00:00:20+08:00` is only 50 seconds old, inside the unchanged
  approved 60-minute maximum: both rule matching and full assessment reject it.

The positive control and 12 negative controls pass: event denial, impact denial,
planning, drill, training, procedure, conditional, archive, ambiguous text,
61-minute-old text, future publication and unknown time quality. All 15 existing
rule/model acceptance cases also pass unchanged. These results reproduce missing
contextual correctness, not missing authorization, and are handed to M/AB before
owner repairs. Independent acceptance of any repair requires a later I candidate.
Product source/model/Feishu requests, sends, tokens and paid product cost are 0;
the existing isolated model tests use synthetic HTTP responses only.

### R17 controlled trial deployment preparation

The first R16 reproduction was committed and pushed at
`b9a241acfe0353ce425a7eef258111d72fcc253d` before deployment work and before
AB fixes. E independently inspected I BEFORE candidate
`0fa7d85c8e235403cb893f566828f4213131c34f`: `src` is unchanged from accepted
`cd6e8d9`, and the E contextual regression file is identical to `b9a241a`.
The recorded eight failures remain BEFORE evidence, not an accepted repair.

New deployment files are `deploy/compose.e-trial.yaml`,
`deploy/nginx.e-trial.conf`, `deploy/controlled-trial.md`,
`scripts/controlled_trial.py`, `scripts/trial-start.sh`,
`tests/integration/test_controlled_trial_deploy.py` and the focused
`.github/workflows/controlled-trial.yml`. E did not change the shared base Compose,
factory, integrated runbook, domain code, existing assertion or original CI gate.

`uv run --locked pytest tests/integration/test_controlled_trial_deploy.py
tests/integration/test_deploy_safety.py -q --tb=short
--junitxml=e2e/runtime-artifacts/controlled-trial-preparation.xml`:
**54 passed, 0 failures/errors/skips, 0.76 seconds**, Windows Python 3.13.13.
Ruff check/format, `bash -n scripts/trial-start.sh` and `git diff --check` pass.
The real installed Compose 5.1.4 parses base + trial + authored pin overlay with
an isolated Docker config directory and synthetic environment. An initial harness
error hid the Windows Compose plugin when isolating its config; the harness now
uses the installed standalone Compose binary on Windows, preserving isolation.
No test was skipped or weakened. Linux uses Docker's installed Compose plugin.

Checks cover exact project/database/volume isolation, TLS pairing/validity/DNS SAN,
loopback-only HTTPS, raw callback and SPA configuration, closed capabilities,
shared factories/entrypoint/queue/capability bounds, public IPv4-only pins, exact
effective network selection, absent or bypassed firewall rules, inactive Docker
user hook, unexpected attached networks, recursive DNS and IPv6 denial. The
startup wrapper is exercised against explicit command doubles: failed preflight
never invokes Compose; success invokes only the fixed profile/project with no
build/pull. Preparation neither executes commands nor overwrites a directory.
No actual firewall or packet-filter behavior is inferred from these doubles.

Default action is read-only. Optional preparation creates nonsecret pin/rule
files; a separate future operator action applies reviewed host rules and creates
the dedicated network. The start wrapper does neither. This supports the existing
direct pinned transports without a proxy or adapter changes. Public TLS chain,
actual login/message callback reachability, on-host egress/DNS/IPv6 denial and
phone trust remain NOT EXECUTED. Retained-resource automatic resume is explicitly
unimplemented; the prepared stop/recover procedure preserves data and delegates
UNKNOWN handling to C rather than replaying uncertain sends.

Actual Docker observations at this increment: both `docker version --format
'{{.Server.Version}}'` and a bounded `docker inspect --format ...` on exact old E
container `b3c3a345428590922eb8e628a996dd634cb3333e5f0c86f588eede8fb7101cab`
failed because `dockerDesktopLinuxEngine` named pipe does not exist. Its state,
volume and interrupted schema cleanup remain unverified. No daemon restart,
container/volume mutation, firewall application, network creation or new local
image build was performed. The focused remote job will verify actual Nginx `-t`
under `--network none`; its result must be reported separately when complete.
All real product source/model/Feishu requests, sends, tokens and paid product cost
remain 0. Development/CI billing was not collected. Independent final acceptance
belongs to a later task on I's exact integrated candidate.

### R17 follow-up: Linux serialization and stopped-resource preflight

The initial deployment commit `c557665440ce537017741d84b46396fac77da404`
did not pass Linux: [focused CI 34669072808](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34669072808)
reported **53 passed, 1 failed**, before reaching Nginx. The failure was E's
interpretation of `bind.create_host_path`: Compose v2 omits false in JSON, while
Windows Compose 5.1.4 emits false explicitly. The checker now selects the
representation using the actual CLI major version; unsupported majors and
explicit true remain rejected. Original negative assertions are preserved.

The follow-up implements read-only `check-retained` for seven explicitly recorded
full trial container IDs. It checks ownership labels and configuration paths
before reading container configuration, then clean stopped state, current image
identity, commands/environment, security/resource bounds, exact data/TLS mounts,
loopback ports, DNS pins, IPv6 state and the two exact networks/attachments. It
does not enumerate unrelated containers, start, stop, detach, delete or replay
anything. The previous automatic-resume limitation remains; manual recovery now
has an executable read-only preflight rather than an instruction to bypass the
cold-start check. UNKNOWN delivery still requires the established reconciliation.

`uv run --locked pytest tests/integration/test_controlled_trial_deploy.py
tests/integration/test_deploy_safety.py -q --tb=short
--junitxml=e2e/runtime-artifacts/controlled-trial-preparation.xml` now reports
**70 passed, 0 failures/errors/skips, 0.84 seconds**, Windows Python 3.13.13.
Ruff check/format, `bash -n scripts/trial-start.sh` and `git diff --check` pass.
New negative cases refuse foreign ownership, wrong file paths, running/failed
containers, old data volumes, changed image/environment, unexpected attachments,
replaced network IDs, extra published ports and IPv6. Recorded-state checks use
explicit isolated Docker command doubles; actual retained resource inspection
and stop/recovery remain NOT EXECUTED because the local engine is unavailable.

I intermediate `9c5cba6baac9d2ed33a653515334046bae3a8bac` was independently
diffed against E `c557665`: only M governance and I's `.env.example`,
`docs/runbook.md`, `config/integration-handoff.md` changed. Its integration notes
correctly distinguish configuration parsing from activation and public callback
reachability. This review accepts that documentation scope only; the known E
Linux failure and R16 failures preclude whole-candidate acceptance at that SHA.
Product source/model/Feishu requests, sends, tokens and paid product cost remain
0; development/CI billing is unmeasured. No infrastructure was activated.

### Final independent code acceptance: PASS for synthetic integration

Accepted code: **`63627eee09bc9fb10e32b68f979f7715db199791`**, including I's
configured factory, C `17238867091e1a6529ab91568dff18c32ede32c2`, AB
`6c517f5c4e5ffc2b4b844f91d49de90aba3848b8` and E checks through
`87a737b4e837e8552399e1f066f576202f906187`. E's clean existing branch fast-forwarded
to that exact I candidate; E independently matched the public origin I branch to
the same SHA. No producer tip, new branch/worktree or business edit was used.
This final result closes the earlier code failures recorded chronologically below;
it does not turn synthetic fixtures into real provider, account or phone evidence.

E independently inspected the successful conclusion, individual job steps/logs and
downloaded JUnit artifacts from exact-code
[Actions 34665612094](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34665612094).
The run completed **SUCCESS** on Ubuntu 24.04, Python 3.13.13, uv 0.11.26,
Node 24.16.0, with separate real PostgreSQL 16 services for C and E. Each E case
uses its isolated migrated schema; no SQLite, auth dependency override, xfail or
test deselection substitutes for these results. The existing Starlette/AnyIO
deprecation warning remains.

| Required command / evidence | Exact result |
| --- | --- |
| `uv sync --locked` | PASS; existing lock used |
| `uv run --locked python scripts/validate_scenario_corpus.py` | PASS; corpus consistency only |
| `uv run --locked ruff check tests/integration deploy/worker_health.py` | PASS |
| `uv run --locked python -m oil_agent.runtime.cli migrate` on separate C test service | PASS |
| `uv run --locked pytest tests/contracts tests/unit -q --tb=short --junitxml=e2e/core-acceptance.xml` | **343 passed, 0 failures/errors/skips**, 20.891 seconds |
| `uv run --locked pytest tests/integration -q --tb=short --junitxml=e2e/local-acceptance.xml` | **150 passed, 0 failures/errors/skips**, 26.829 seconds |
| `npm ci --ignore-scripts`, then `npm test` in `web` | PASS; **23 tests passed**, 1.53 seconds |
| `npm run build` in `web` | PASS; authoritative generated schema/types, TypeScript and Vite |
| `bash -n deploy/entrypoint.sh scripts/backup.sh scripts/restore-isolated.sh scripts/compose_scope.sh` | PASS; syntax only |
| `docker build -f deploy/app.Dockerfile -t oil-agent-app:ci .` | PASS; Linux image construction, Python 3.13.15 in image |
| `docker build -f deploy/web.Dockerfile -t oil-agent-web:ci .` | PASS; frontend rebuilt inside Linux image |

Built CI image IDs: app
`sha256:ce5f31e16b1ea1d8f476757a35a7aad3e0d5e6ed7fed756585a409d07af9c83d`, web
`sha256:56030c244cc5858356796f592725323e08d321e8b5869033b3cea00134c0b36b`.
These images were built in CI, not published or deployed to a user server.

| Independent acceptance scope | Final status and observations |
| --- | --- |
| R1/R4 synthetic transport -> model -> approved rule -> PostgreSQL ordinary silence | **PASS**: all 13 I factory cases, E source/network cases and E configuration checks pass; actual injected adapters retain provenance/rights/history and model usage; the routine source/model path persists with zero notification intents; new messages reuse one loaded rule without per-message ClaimReview |
| R2 permission scope, budgets and concurrency | **PASS**: separate C PostgreSQL suite and E 7 operational trial cases pass, including final-reservation contention, durable unknown usage/overrun, immutable approval reuse, fixture-session rejection, revocation and mixed pending/outbox/API scope |
| R3 labeled synthetic login, test-recipient send and ack | **PASS**: 3 E trial-exercise sender cases, 12 OAuth cases, 12 security cases and the I factory OAuth/send/signed-ack chain pass; callback/replay/recipient/revision boundaries hold, UNKNOWN is not blindly retried; all platform replies are isolated doubles |
| Preserved C/AB regressions | **PASS**: unchanged T05 denial correction (0.376 seconds), unchanged same-ID expiry/session case (0.232 seconds), both Chinese procedure/training guards and positive unseen phrasings pass; Git diff confirms E assertions unchanged from 87a737b |
| Frontend, shared deployment defaults and Linux image build | **PASS within automated scope**: 23 frontend tests, schema/type/Vite build, shared default environment/security checks, shell syntax and both serial image builds pass; no new actual-browser, Compose runtime, TLS or phone acceptance is inferred |

Product source requests **0**; product model requests/input tokens/output tokens
**0**; product Feishu login/message requests and sends **0**; paid product cost
**0**. Git/Orca/public CI operations are not product provider calls. Synthetic
HTTP counts and usage are separate: selected case counts are recorded below;
the complete suite's aggregate synthetic request count was **not instrumented**.
No actual provider billing or successful real request is inferred from mock usage.

Remaining classifications and **NOT EXECUTED** operations:

- **MISSING_AUTHORIZATION:** exact provider/license/rights, business rule approval,
  model/budget, tenant/app, test actor/recipient, account, quote sample and server/
  probe inputs. No existing credential was searched, read or copied.
- **IMPLEMENTED_AWAITING_REAL_TEST:** Jin10/OpenAI/Feishu adapter paths have the
  scoped synthetic acceptance above; authorized real source/model ingestion,
  OAuth/account login, platform sends/callbacks and actual phone receipt are not
  executed. Source comparison >=7 days and operation >=14 days have not started.
- **MISSING_IMPLEMENTATION / unsupported:** production factory startup explicitly
  rejects; trial report reminders are explicitly unsupported. The current Compose
  is an internal-network local reference, not a prepared real-provider deployment
  with authorized egress, HTTPS and off-host probes. These are not credential-only
  gaps and were not expanded in this phase.
- **ENVIRONMENT_FAILURE / local verification incomplete:** Docker's Linux engine
  pipe disappeared during the two Windows usage checks. Only the verified waiting
  E pytest PID 2384 was stopped; those cases subsequently passed on CI PostgreSQL.
  Exact retained E container
  `b3c3a345428590922eb8e628a996dd634cb3333e5f0c86f588eede8fb7101cab`
  (`oil-agent-e-postgres-1`, loopback 55434) was last known running in its allocated
  slot. Its current state and interrupted UUID-schema cleanup are **unverified**;
  no successful stop, daemon restart, volume deletion or unrelated-container
  operation is claimed. No E full Compose or local image job was started in v1.1.
- New-schema backup/isolated restore/rollback, real deployment, off-host outage
  detection and a new actual-browser/phone matrix were **NOT EXECUTED** in v1.1.
  Earlier v1.0 artifacts remain attached to their historical candidates only.

This evidence-only follow-up does not rerun unchanged passing code. I owns final
report/governance integration, final delivery SHA and its resulting CI receipt;
M owns the unique board. E's acceptance is tied to the code SHA above.

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

### Candidate 5: nonblank request reservation guard

Exact I **`54b9c1d735ae6b341b25a445b0e947fdcf661f7e`**, including AB `412aded`, was
normally merged after the candidate-4 regression commit `d4d772a`. This increment
requires a nonblank reservation string before source HTTP proceeds. E added seven
negative variants (None, false, true, number, empty/whitespace string and object)
and verifies that neither the DNS resolver nor HTTP transport is called.

```text
uv run --locked pytest tests/unit/ingestion/test_jin10.py tests/integration/test_jin10_acceptance.py -k 'missing_token or invalid_reservation' -q --tb=short --junitxml=e2e/runtime-artifacts/v11-candidate5.xml
```

**11 passed, 46 explicitly deselected, 0 skipped, 0.20 seconds**, exit 0: four AB
guard cases and seven new independent E cases. Ruff check/format and diff-check
PASS. **LIMITED_LOCAL_PASS for this guard only**; no unchanged baseline, PostgreSQL,
image or browser rerun was needed. E guard cases made zero DNS/HTTP requests;
product source/model/Feishu calls/tokens and cost remain **0**. The earlier two
Chinese policy regressions and three sender migrations remain unresolved in this
candidate, so full acceptance is still FAIL. AB's corrective rule commit and C's
operational implementation must arrive through exact later I candidates before E
can change those results.

### Candidate 6: initial operational trial sender migration

Exact I C operational candidate **`bf9c46764f2fea4ac8499620c6628de1e3abcaed`** was
normally merged after E `a3411db`; E merge HEAD was
`2a9316496cfd5abdbdf95542fcf1f7497009135c`. It introduces C `0003_trial` and the
operational approval/session/data-scope hooks. This entry records the first focused
sender subset; broader mixed-scope/budget/session acceptance continues on subsequent
exact integrated candidates containing the same C implementation.

The three original sender scenarios now use explicit synthetic fixture-exercise
trial permissions and a session obtained through C state/approval gates and the
actual D OAuth adapter with isolated HTTP responses. E provisions only exact
approved app-bound identities. All fixture records retain their dataset and
provenance; production validation is unchanged. The accepted-message variant now
also passes its actual synthetic provider message ID through D's signed callback
and C's durable acknowledgement/replay path.

```text
uv run --locked pytest tests/integration/test_postgres_channel.py -q --tb=short --junitxml=e2e/runtime-artifacts/v11-candidate6-channel.xml
```

**3 passed, 0 failed, 0 skipped, 3.31 seconds**, exit 0, actual migrated E PostgreSQL.
Accepted is not resent; lost response remains UNKNOWN; user revocation during
token acquisition prevents the message request. The accepted case becomes ACKED
once and accepts idempotent callback replay. The three earlier configuration-test
failures are **resolved in this local subset**, pending the eventual full integrated
suite. Ruff check/format PASS; existing Starlette/AnyIO warning remains.

Per scenario, OAuth performs two synthetic HTTP requests; accepted/unknown each
perform two sender HTTP requests and revoked performs only token acquisition:
**11 synthetic HTTP requests total**, product source/model/Feishu requests/tokens
and paid product cost **0**. The C ledger records bounded OAuth exchanges/send
attempts separately; those operation counts are not total platform HTTP usage.
No actual tenant or phone is verified. E PostgreSQL remains in the explicitly
allocated lightweight test slot for the next bounded operational tests; no full
Compose or image work is authorized in that concurrent PG slot.

### Candidates 7/8: rule corrections, UI schema and operational isolation

Exact I candidate **`bf4629b7da0d6516aeb93a98eb2f09c71d8ad6a4`** includes candidate
7 `5fd432ce233588f80c34711f904fb3475ea094a8`, AB rule correction
`651c11428642b8a3ac5549c7d40cc6edff3fe0f7`, C operational code/tests through
`f32a9493bcb6fafbca27b9439e580b0d01a04200` and D schema/UI
`7e575c293a2a7ad19f0c08f6c2575db90577fe4f`. E normally merged this exact integrated
candidate at `00a02f76d75cbde4f8a667600935cddbc10b373a`; uncommitted I factory work
was excluded. No producer tip was adopted independently.

```text
uv run --locked pytest tests/unit/intelligence tests/integration/test_rules_acceptance.py -q --tb=short --junitxml=e2e/runtime-artifacts/v11-candidate8-rules.xml
cd web
npm test
npm run build
```

Rules: **93 passed, 0 failed, 0 skipped, 1.42 seconds**. The two unchanged E
Chinese procedure/training regressions now pass; their earlier failures remain in
the candidate-4 record. Frontend: **23 passed, 0 failed, 4.88 seconds**; authoritative
generated-type validation, TypeScript and Vite build PASS. These are local
synthetic rule/UI checks, not the final configured factory or a real browser/phone
session. The five model-client cases use five isolated synthetic HTTP responses.

```text
uv run --locked pytest tests/integration/test_postgres_trial_acceptance.py -q --tb=short --junitxml=e2e/runtime-artifacts/v11-candidate8-trial.xml
```

At the five-case revision of this new file: **1 failed, 4 passed, 0 skipped,
10.36 seconds**, exit 1, Windows Python 3.13.13 and actual E PostgreSQL 16.14 with
real `0003_trial` migrations in isolated schemas. A prior setup error (missing
dry-run channel in the E helper) was corrected before this result; the domain
failure below remains an ordinary required assertion, without xfail/deselection.

The passing cases exercise actual Jin10 MCP request callbacks and durable C
source budgets, routine event persistence with **zero intents/deliveries/sends**,
actual model-client concurrency for the final PostgreSQL reservation and
idempotent/mismatched usage replay, rejection of fixture sessions and unapproved
user provisioning under trial identity, revocation at the actual API, and mixed
fixture/trial/production pending/outbox/API filtering in one retained schema.
Only the trial outbox is sent through the actual D sender with synthetic responses;
foreign intents remain pending and their evidence/event endpoints return 403.
Trusted synthetic per-record annotations are used only in that C isolation case;
it does not establish automatic approved-rule factory assembly.

**DOMAIN_FAILURE / R2 acceptance FAIL:**
`test_R2_reusing_identity_approval_id_cannot_extend_existing_session_permission`
shows that an expired, previously scoped OAuth session becomes usable after a
validated settings reload extends the identity permission expiry while reusing
the same immutable approval ID. The original stored permission fingerprint must
continue to govern session/API/callback access; changed authority requires a new
approval. E handed this reproduction to C through M and preserves the failing
test. This is an implementation defect, separate from missing real authorization.
Opaque session values are omitted from the explicit failure message.

The five-case run used **19 synthetic HTTP requests**: source case 2 OAuth + 4 MCP,
model case 1 Responses request, old-session case 2 OAuth, expiry case 2 OAuth,
mixed-scope case 6 OAuth + 2 sender. None reaches a real provider. Source/model/
Feishu product requests and sends, product input/output tokens and paid cost all
remain **0**; modeled usage 22/8 is synthetic and not vendor billing evidence.

Two additional durable-usage variants were then added (unknown usage remains
reserved after Runtime reconstruction; reservation overrun blocks further calls):

```text
uv run --locked pytest tests/integration/test_postgres_trial_acceptance.py -k model_reservation_survives -q --tb=short --junitxml=e2e/runtime-artifacts/v11-candidate8-usage.xml
```

**ENVIRONMENT_FAILURE / NO COMPLETED RESULT:** Docker's
`dockerDesktopLinuxEngine` named pipe disappeared while this command waited on its
database connection; no usage JUnit result was produced. Only the verified E
pytest process was stopped. These two cases are **NOT EXECUTED to completion**,
not application passes, failures or skipped external gates. The test fixture now
bounds PostgreSQL connection establishment to five seconds; it still refuses any
database outside E's exact local/CI scope. Ruff check/format and diff-check PASS;
the connection-timeout change awaits a restored database for runtime verification.

The coordinator was notified. At daemon loss the exact retained E PostgreSQL
container was running in its allocated lightweight slot; its final state and
cleanup of the interrupted UUID schema cannot yet be verified. E did not restart
Docker, remove a container/volume, run a full Compose stack or build an image.
Final I factory assembly/binding and the C fix require new exact I candidates.
Real scoped source/model/identity/recipient inputs remain MISSING_AUTHORIZATION;
implemented provider paths remain IMPLEMENTED_AWAITING_REAL_TEST. Real provider
calls, OAuth/account login, phone receipt, deployment, >=7-day comparison and
>=14-day operation remain **NOT EXECUTED**.

#### Exact E code Linux CI follow-up

[Actions 34664692956](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34664692956)
ran exact E code **`f783bac621b8e8e5a246cd953bdbed4fec295dd0`**: **339 core tests
passed**, zero skips, 17.217 seconds; **125 integration tests passed, 2 failed,
0 errors, 0 skipped**, 24.010 seconds. The downloaded JUnit artifacts independently
confirm both unknown/overrun model-usage variants **PASS** on Linux PostgreSQL
(0.249 / 0.246 seconds); this supplies completed CI evidence for those cases while
their Windows Docker-interrupted invocation remains incomplete. The bounded
connection fixture also ran in this CI environment. Locked sync, corpus and Ruff
passed; frontend, shell and image steps after failing integration were not run in
this CI invocation. The earlier local 23 frontend tests/build remain separately
scoped evidence.

The two unchanged required failures are the C identity-expiry regression and
`test_T05_lower_severity_denial_corrects_original_authorized_recipients`:
the synthetic correction "Correction: our destruction report was wrong; no
refinery damage is established." now produces `unknown` instead of `denied`.
The AB rule correction applies the general `no` blocker to an explicitly reviewed
denial. E handed this regression to AB through M; the existing T05 assertion is
unchanged. Prior exact E `6be21de` CI
[34664237011](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34664237011)
had **118 integration passes, 2 failures, 0 skips**, 19.983 seconds, with only the
two Chinese procedure/training cases failing and T05 passing. Thus neither new
failure is missing external authorization. **Full acceptance remains FAIL** until
the original owners' fixes arrive through I and pass independent acceptance.
No real product call or additional local container operation was performed.

### Candidate 9: configured shared factory and Compose assertion migration

E normally merged exact I **`8de731b259b676a3187b2b04a63010f59d9371d4`** at
`88bb9f9237f901a4a7dec20b97b4e86067118f78`. It adds the configured trial factory,
I-owned source/model/OAuth/callback PostgreSQL tests and C's explicit rejection of
unsupported trial report reminders. This candidate does not include fixes for
the two recorded domain failures; those required assertions remain unchanged.

I's authorized Compose environment now uses `${OIL_OUTBOUND_MODE:-dry_run}` and
`${OIL_ENVIRONMENT:-test}`. The old E literal-value assertion was stale. E migrated
only `test_deploy_safety.py` to verify those precise safe fallback expressions and
the complete shared application environment after YAML anchor resolution for API,
init and all three workers. It additionally checks fixture defaults, disabled
external capabilities, absent permissions, zero model budgets, empty provider
credential defaults, mandatory database credential injection and Secure cookies.
Existing network exposure, resource, startup, image and backup safety checks stay.

`uv run --locked pytest tests/integration/test_deploy_safety.py -q --tb=short`:
**4 passed, 0 failed, 0 skipped, 1.91 seconds**, Windows Python 3.13.13. Ruff
check/format and diff-check PASS. This is a static Compose boundary check, not a
container start, provider egress, deployment or credential acceptance. No domain,
factory, Compose or I-owned test file was edited by E. Docker remains unavailable;
the coordinator directed remaining PostgreSQL acceptance to Linux CI and forbade
a shared daemon restart. Final candidate acceptance remains pending its complete
CI, independent factory checks and the two owner fixes. Product calls/cost stay 0.

The independent E file `test_trial_configuration.py` adds constructor-boundary
checks without modifying I's factory or factory test. It supplies an authored
environment only to the factory module and traps PostgreSQL connection attempts,
DNS and HTTP client sends. The actual PostgreSQL dialect, Repository, Runtime and
AB/D constructors remain in use; **no database I/O is performed or claimed**.
Checks cover unread disabled-capability credentials, identity-only isolation,
source rights and runtime budget callbacks, no implicit sender or report model,
wrong provider/provenance, expired/unapproved rules, permission validity outside
rules, missing injected keys and explicitly unsupported production assembly.
Two new Chinese messages use the same loaded approved rule, with no per-message
review; a routine bulletin stays routine and the rule snapshot is unchanged.
These newly authored trial-shaped records remain synthetic test material.

`uv run --locked pytest tests/integration/test_trial_configuration.py -q --tb=short
--junitxml=e2e/runtime-artifacts/v11-candidate9-configuration.xml`:
**13 passed, 0 failed, 0 skipped, 1.22 seconds**, Windows Python 3.13.13; Ruff
check/format and diff-check PASS. Synthetic network requests **0**, database
requests **0**, product source/model/Feishu calls/sends/tokens/cost **0**.

Exact E Compose increment **`49c75d32f6a6f9e15aef4cc0855a89ac10d66365`** (before
these 13 new tests) completed Linux CI
[34665288636](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34665288636):
**340 core passed**, zero skips, 19.223 seconds; **135 integration passed,
2 failed, 0 errors, 0 skips**, 29.593 seconds. All 13 I factory cases passed on
real migrated PostgreSQL, including actual injected source/model storage with
zero routine outbox, restart/history/budget behavior, scoped OAuth/send/signed ack
with isolated HTTP responses and five missing/mismatched-rule variants. The static
Compose migration passed. The only failures remain unchanged C approval reuse and
AB T05 denial; owner fixes are not in this candidate. Later frontend/image steps
were not reached. Aggregate synthetic HTTP requests across the full suite were
not instrumented; individual cases assert their own bounded counts. There were no
authorized or executed real product requests. Factory implementation now has
scoped local integration evidence; real provider operation remains
IMPLEMENTED_AWAITING_REAL_TEST with MISSING_AUTHORIZATION, while these two domain
defects keep overall acceptance FAIL.

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

## Actual local recipient binding: independent post-state verified

On 2026-09-12, E observed the real post-state from **11:34:07.928930 UTC**
through **11:34:49.156070 UTC**, using clean E source
`d35a7fc192db05fb134a1459ce13d6748732f3c6`. `git diff --exit-code` confirmed
`src/`, `pyproject.toml` and `uv.lock` identical to accepted I delivery
`3c7ee50383235587063fe938fc7d27fe50d90783`; loaded helper paths resolved to E.
Only the approved configuration was read, with its protected-path metadata:
`C:/Users/DW/AppData/Local/oil-agent/private/feishu-c1/config.json`.

The accepted path/ACL verifier passed without repair. The actual file is a
bounded (at most 16384 bytes), single-link, regular, non-reparse file with valid
UTF-8, duplicate-key rejection and strict schema validation. Directory and file
are owned by the current user; their two allowed FullControl principals are
exactly that user and SYSTEM. Directory ACL inheritance is disabled; the file
inherits its restricted ACL. The configured host matched both the actual Windows
machine name and the approved host; application fields were nonempty. The exact
recipient comparison against M's supplied expected identity passed in memory.
No private value or comparison digest was printed or recorded in this artifact.

An inline `.venv/Scripts/python.exe -I -B -` verification invoked each existing
helper mode once, with the same environment's absolute interpreter:

```text
python -B -m oil_agent.runtime.c1_private check
python -B -m oil_agent.runtime.c1_private inject-check
```

`check` started at **11:34:23.507771 UTC** and `inject-check` at
**11:34:34.182944 UTC**. Both returned **exit 2**, empty stderr, `CREATED`,
`NOT_CONFIGURED`, missing exactly `tenant_key`, `start_trigger=NOT_AUTHORIZED`
and `product_requests=0`. The real fixed isolated `python -I -m
oil_agent.runtime.c1_product` child returned the expected redacted response;
no child, configuration or ACL mock was used. Bounded in-memory comparisons
after each mode and at completion verified unchanged configuration bytes and
file identity. The surrounding verification exited **0**.

C's null-only recipient update at **11:29:39.786335 UTC**, including preservation
of all other bytes, formatting and owner/group/DACL, remains **C-reported** via M's
handoff for `ctx_9c7a6e43d0e0`; E did not observe C's pre-update state. This new
observation supersedes the earlier locally missing-recipient result only.
Verdict: **ACTUAL LOCAL RECIPIENT CONFIGURATION / LOADING / ISOLATED INJECTION
VERIFIED**. Tenant binding is still missing and no executable permission or new
phone window was created. E performed no private write, clipboard/UI operation,
token/tenant lookup, source/model/platform call, send, login, callback, database,
Docker, test suite, build or dependency installation. Product calls/sends and
added product cost are zero for these local checks; earlier browser background
request counts remain UNKNOWN. Source/model/platform/phone/login/callback and
production acceptance remain unexecuted.

## C1 PostgreSQL adapter: routing verified, SQL not executed

On 2026-09-12, E normally merged accepted I
`f04f64f55cc12e7fea4cfa5d56ee768816bad561` and M governance
`0341190eab575e4711fde607762c65257ecb8ec8` from its clean retained branch.
The pre-edit merge checkpoint is `365007b1a429c4ff10a4ca701b50f15d5d759ca2`.
The only new harness file is `tests/integration/test_postgres_c1.py`.

Before implementation, an inline `.venv/Scripts/python.exe -B -` probe supplied
a synthetic E-shaped URL to C's original first C1 case and trapped SQLAlchemy
engine construction. The original C fixture failed with **1 setup error**,
`Refusing a database outside C test scope`, pytest **exit 1**, 0.34 seconds;
engine constructions were **0**. The probe's expected-failure validation exited
0. C's guard was not changed or bypassed.

The adapter imports the original C module using pytest's existing test-root
import path, exports its original 12 callable objects, `c1` fixture and postgres
mark, and binds only this module's `repository` fixture to `e_repository`.
There are no copied assertions, wrapper test bodies or global fixture overrides.
The original parametrizations still expand to **21 cases**. E's migration 0001
already seeds the default BusinessConfig singleton; no extra insert or actors
fixture is added. The original `c1` captures and freezes E's assignable clock.
One function-scoped repository/engine is shared with `c1`; its ordinary sessions,
parallel connections and disposable-schema cleanup remain unchanged. C's
read-only contract handoff `msg_a2e4ba1e5310`, relayed by M, confirmed these seams.

```text
uv run --offline --locked --no-sync pytest tests/integration/test_postgres_c1.py --collect-only -q -p no:cacheprovider
uv run --offline --locked --no-sync ruff check tests/integration/test_postgres_c1.py
uv run --offline --locked --no-sync ruff format --check tests/integration/test_postgres_c1.py
```

Final collection: **21 collected**, exit 0, 0.04 seconds; both Ruff checks passed.
The initial `tests.unit` import failed under the console pytest entry; using
pytest's existing `unit.storage` namespace resolved that observed import error.
An inline collection audit compared original and adapted case names/parameters,
original callable/fixture/mark identity, and effective fixture definitions for
all 21 cases: **PASS**, exit 0, no engine construction. C still resolves its own
guarded fixture; E resolves the existing function-scoped migrated fixture and
never requests `e_actors`. Original C1 source, C fixture and E fixture content
and AST were unchanged against accepted I; product sources and locks were also
unchanged.

Focused adapter guard probes used engine-construction traps, not fake SQL
repositories. With no E URL: **21 skipped**, zero test bodies executed, pytest
exit 0, 0.03 seconds, each citing E's explicit `NOT EXECUTED` reason. With a
synthetic C-shaped URL supplied to E: the first case had **1 expected setup
error**, pytest exit 1, 0.17 seconds, `Refusing database outside the explicit E
local/CI synthetic scope`. Both probes validated the expected outcomes with
outer exit 0 and **0 engine constructions**. These are harness checks, not
passed SQL assertions.

The one authorized resource observation used `docker --host
npipe:////./pipe/dockerDesktopLinuxEngine inspect --type container` against exact
previous E container `b3c3a345428590922eb8e628a996dd634cb3333e5f0c86f588eede8fb7101cab`,
requesting only identity/state/labels/mount/port metadata. It exited **1** because
the named pipe was missing. No current ownership, running state or database
binding was proven. No retry, enumeration, start, restart, cleanup or SQL/schema
operation followed; old E resources were untouched.

Verdict: **ADAPTER IMPLEMENTED; COLLECTION / ROUTING / GUARDS VERIFIED;
21 POSTGRESQL CASES NOT EXECUTED**. No domain failure was observed because SQL
test bodies did not run. A confirmed E-owned PostgreSQL scope is still needed
for those original assertions; this grants no live C1 database permission.
No private configuration, clipboard/browser, provider/model call, send, new phone
window, dependency installation, full-suite replay or build was performed.
Platform, phone, login, callback and production acceptance remain unexecuted.

## C1 actual PostgreSQL: 21 original cases passed after Docker resumed

On 2026-09-12, E normally merged accepted I
`4ec6c480dc971d44d176c3539bcbcade4ee7f802` and M governance
`3ad12a67c0b5518d2c10451099b61ececc363c72`, preserving history at tested source
**`c725a56a803c77b94efec54956e30a97fea437fd`**. The documentation conflicts were
resolved to the exact accepted I and then M board blobs. Product sources, locks,
the adapter, all original C assertions and both database fixtures remained
identical to accepted I. No test or product fix was needed.

Fresh selected Docker metadata verified the original resource before database
access; the user-started engine supersedes the earlier missing-pipe observation.

| Verified field | Actual value |
| --- | --- |
| Endpoint | `npipe:////./pipe/dockerDesktopLinuxEngine` |
| Container | `oil-agent-e-postgres-1` |
| Full container ID | `b3c3a345428590922eb8e628a996dd634cb3333e5f0c86f588eede8fb7101cab` |
| Compose project / service | `oil-agent-e` / `postgres` |
| Compose working directory | `C:/Users/DW/orca/workspaces/oil-agent/oil-v01-e/deploy` |
| Exact configuration files | The above directory's `compose.yaml` and `compose.e-test.yaml` |
| Image reference | `postgres:16-alpine@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb` |
| Image ID | `sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb` |
| Volume | `oil-agent-e_postgres-data`, local driver, mounted at `/var/lib/postgresql/data` |
| Volume ownership labels | Project `oil-agent-e`, volume `postgres-data` |
| Configured and active host binding | Only `127.0.0.1:55434` to container `5432/tcp` |
| Actual database / user | `oil_e_test` / `oil_e_test` |
| Actual server | PostgreSQL **16.14**, UTC, server port 5432 |
| Original and final container state | Already running and healthy; E neither started nor stopped it |

An initial metadata assertion incorrectly expected the repository root as the
Compose directory. The corrected read-only check matched the actual E `deploy`
directory and both exact configuration paths; no resource was changed. Neither
E test credential variable was inherited. M explicitly authorized one bounded
read of only this container's existing synthetic password into Python memory.
E validated it, built the exact scoped URL structurally, and injected it only
into the intended test child. No password, DSN or full environment was emitted
or written, and no unrelated credential or C1 private configuration was read.

```text
uv run --offline --locked --no-sync pytest tests/integration/test_postgres_c1.py -q --tb=short
```

This command ran **once**, from **12:36:26.871108 UTC** to
**12:36:42.254355 UTC**: **21 passed, 0 failed, 0 skipped, 13.26 seconds,
pytest exit 0**. It used actual PostgreSQL migrations and the unchanged E
fixture's fresh disposable schemas. The original concurrent preparation,
transaction rollback, shared-budget races, authorization/expiry checks and
UNKNOWN fencing assertions ran against real PostgreSQL; their approvals and
provider-result inputs remain explicitly synthetic. No SQLite or fake database
substituted for this execution.

Bounded, repeatable-read, read-only snapshots of this database were taken before
the run at **12:36:26.871033 UTC** and checked after it by
**12:36:43.767653 UTC**. The only original user schema was `public`, with
**73 relation identities**, **29 data objects** and **823 row/sequence-state
records**. Schema and relation identities, complete bounded table-row multisets
and sequence values matched before/after; **no new schema remained**. Container
and volume metadata, image, mount, ports, running state and start/restart fields
also matched. Only fixture-created UUID schemas were created/dropped; no old
schema, data or resource was cleaned up. The verification wrapper exited **0**.
These are logical database snapshots, not physical-volume byte identity or a
production backup/restore claim.

Verdict: **THE 21 C1 POSTGRESQL CASES PASSED ON THE VERIFIED E SYNTHETIC DATABASE**.
This supersedes their prior NOT EXECUTED result only. No full suite, build,
dependency installation, daemon restart, resource recreation, provider/source/
model/Feishu call, send, new phone window or UI/private-file action occurred.
The E test database is not approved as the future live C1 database; platform,
phone, login, callback, deployment and production acceptance remain unexecuted.

## Dedicated C1 database: offline deployment preparation

On 2026-09-12, E continued from pushed SQL evidence
`87065fea2e5ccfddad918dabf6db4a39df3d51d1` and normally merged exact M governance
`d38af512d295e6f237936a71d4bee6f4f1a3dd31` at
`d52790701e5b299fa09cd1f3173bb8b31b9c3637`; no conflict or history replacement
occurred. The accepted **21 real E PostgreSQL passes were not rerun** and their
container, volume, database and credentials were not accessed in this task.

The new standalone `deploy/compose.c1-db.yaml` renders only `postgres` under
project `oil-agent-feishu-trial`, with database/user `oil_c1_trial`, volume
`oil-agent-feishu-trial_c1-data`, sole internal IPv4 backend network and requested
loopback `127.0.0.1:55436:5432`. It reuses the accepted pinned PostgreSQL 16 image,
requires only process-injected `OIL_C1_DB_PASSWORD`, retains fixture/`feishu-c1`
labels, disables automatic restart and bounds resources/logs. These names are
proposed resources, not existing or activated identities.

Red/green evidence:

- Before the Compose file existed,
  `uv run --offline --locked --no-sync pytest tests/integration/test_c1_database_deploy.py::test_standalone_database_has_no_application_or_activation_services -q --tb=short`
  exited **1** with **one setup error**: the standalone database definition was
  missing. No daemon was contacted.
- The first render run had **4 passed, 1 failed** because Compose serialized
  `mem_limit` as a string. The assertion now compares its numeric value to the
  same 128 MiB bound; no configuration limit was weakened.
- Final command:
  `uv run --offline --locked --no-sync pytest tests/integration/test_c1_database_deploy.py tests/integration/test_controlled_trial_deploy.py::test_trial_rejects_unsafe_resolved_configuration[db-port] tests/integration/test_controlled_trial_deploy.py::test_trial_refuses_invalid_tls_prerequisites[http] -q --tb=short`
  exited **0**, **7 passed in 0.61 seconds**, none skipped. The five new cases
  cover actual Compose rendering, exact service/network/port/volume boundaries,
  fixture labels/resource bounds and refusal of missing/empty process passwords.
  The two unchanged general-trial cases still reject a database port and HTTP.
- `uv run --offline --locked --no-sync ruff check tests/integration/test_c1_database_deploy.py`
  and the corresponding `ruff format --check` both exited **0**.
- Actual `docker-compose version --short` returned **5.1.4**. Tests invoked its
  `--env-file deploy/compose.env --file deploy/compose.c1-db.yaml config --format json`
  with an isolated child environment and synthetic in-memory password. Resolved
  output was captured; passwords were compared then removed before assertions.
  No full rendered environment or credential was emitted or stored.

**WINDOWS HOST DATABASE ACCESS IS NOT ESTABLISHED.** The bounded primary-source
review used Docker's [internal network contract](https://docs.docker.com/reference/cli/docker/network/create/#internal)
and [Desktop networking limits](https://docs.docker.com/desktop/features/networking/networking-how-tos/#known-limitations).
Internal mode still permits Docker-host communication; those documents do not
prove that localhost publication always fails. The old E second-network
workaround is historical evidence, not a current C1 packet test. No ordinary
external bridge was added. The exact later finite activation/mapping/read-only
identity probe and stop-on-failure boundary are recorded in the existing
`deploy/controlled-trial.md`; rendering does not settle live network behavior.

M instructed E to finish this preparation without waiting for C's owner commit.
The resource/label contract was handed to M for C; exact committed helper
integration and its fail-closed runtime mapping checks remain pending owner
handoff. No C helper, original test/fixture, general trial gate, product source
or lock was edited. No new resource, image pull, migration, queue initialization,
recovery, SQL run, private credential access, provider call, send, phone window,
full suite, build or CI job was performed. Verdict: **OFFLINE COMPOSE PREPARATION
PASSED; C1 ACTIVATION, HOST ASSEMBLY AND PHONE/PRODUCTION ACCEPTANCE NOT EXECUTED**.

After the initial preparation commit, M relayed C's exact required-password
placeholder text. E aligned only that interpolation error message to
`${OIL_C1_DB_PASSWORD:?Explicit C1 database password required}` and reran
`uv run --offline --locked --no-sync pytest tests/integration/test_c1_database_deploy.py -q --tb=short`:
**5 passed in 0.30 seconds**, exit **0**. The required-variable gate is unchanged;
this checks actual rendering after interface alignment, not execution of C's
still-uncommitted helper.

## Business baseline: events, daily analysis and finite recovery

On 2026-09-12 E normally merged accepted I
`78e5363d7c7da5d6bb76c3be6296b1f6e4010d87` and M phase-switch governance
`c4e41982fd1128c513d3b89750e7586eb23abb30`, producing baseline
`a3c1a8ac3cedf204519cebeb81cb600004581e0b`. The V01-only conflict was resolved
to the exact M blob; no history was replaced. Frozen E expectations were
committed/pushed as `08db6fc8c6d4ca373c9705dc4779972b3003735c`, then qualified
by `83774440004fdf3969f2d3f0d283134e98bd8a87` before adopting any owner fix.
Product source, original unit/integration assertions, E/C fixtures, R16 guards,
the original v01 scenario corpus and dependency inputs remain unchanged.

The new `business-days.json` is explicitly synthetic/fixture provenance. The
bounded expectations cover ordinary silence; reuse original same-origin,
independent follow-up, correction-recipient and R16 cases; require cutoff-valid
Chinese conditional analysis with resolvable event/revision/evidence citations;
exclude superseded evidence; preserve missing-price uncertainty; and exercise
three report failure/recovery dates with durable daily uniqueness.

**Correction to the initial E baseline interpretation:** the first positive
body contained exercise/uncertainty language, so the real assessment correctly
classified it unknown/routine/unverified. Its empty analysis was not proof of
a missing supported-event analysis. That exact content is retained as a new
negative. The corrected separate positive remains explicitly labeled in fixture
metadata, uses a port loading/transport interruption predicate, and asserts
occurred/credible-single-source/urgent before checking report output. No guard
was relaxed. An earlier missing required `observations` test argument was also
an E setup error, not a product failure.

At corrected source `8377444`, this no-database command exited **1**:

```text
uv run --offline --locked --no-sync pytest tests/integration/test_business_reports.py -q --tb=short -p no:cacheprovider
```

Result: **2 failed, 5 passed in 0.64 seconds**, no skips. With qualified positive
preconditions, `impact_analysis=()` still fails. A newer source revision also
leaves the superseded revision in current report facts. Exercise protection,
cutoff exclusion, absent-quote unknown/no-flat behavior, latest denial and invalid
latest reference without fallback pass. AB received both exact reproductions;
these red expectations remain frozen for integration, not weakened to match
the baseline. Chinese analysis and watch lines use the owner-agreed existing
field format `[event=<id>@<revision>; evidence=#<1-based index>]`; tests resolve
the index to the full in-cutoff evidence reference rather than matching prose.

The real SQL baseline ran once at source `08db6fc` from
**14:37:04.448007 UTC to 14:37:14.036587 UTC**. The exact scoped E identity was
reconfirmed before connecting:

- Endpoint: `npipe:////./pipe/dockerDesktopLinuxEngine`.
- Container: `b3c3a345428590922eb8e628a996dd634cb3333e5f0c86f588eede8fb7101cab`,
  `/oil-agent-e-postgres-1`; project `oil-agent-e`, service `postgres`.
- Compose directory: `C:\Users\DW\orca\workspaces\oil-agent\oil-v01-e\deploy`;
  config labels reference exactly its `compose.yaml` and `compose.e-test.yaml`.
- Image reference: `postgres:16-alpine@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb`;
  container image ID matches that digest.
- Sole volume: `oil-agent-e_postgres-data`, local driver, project/volume labels
  `oil-agent-e` / `postgres-data`, mounted at `/var/lib/postgresql/data`.
- Configured and active mapping: only `127.0.0.1:55434:5432`; PostgreSQL reports
  database/user `oil_e_test` / `oil_e_test`.

The container was already running and was left running. Only its authorized
synthetic password was captured into process memory for the fixed child DSN;
no credential value or DSN was printed or stored. The existing `e_repository`
fixture ran real migrations in fresh `e_acceptance_<UUID>` schemas and dropped
only those schemas. No container/volume/network was created, started or stopped.

```text
uv run --offline --locked --no-sync pytest tests/integration/test_business_reports.py tests/integration/test_business_cycles.py tests/integration/test_corpus_replay.py::test_T03_two_domains_do_not_create_two_independent_publishers tests/integration/test_postgres_pipeline.py::test_T04_independent_late_evidence_upgrades_same_persisted_event tests/integration/test_postgres_pipeline.py::test_T05_lower_severity_denial_corrects_original_authorized_recipients tests/integration/test_contextual_guards.py tests/integration/test_postgres_operations.py::test_T14_real_normal_queue_block_does_not_delay_urgent_delivery -q --tb=short -s -p no:cacheprovider
```

Result: **3 failed, 30 passed in 7.80 seconds**, no skips, exit **1**; measured
child-process wall time **9.589 seconds**. This run predates the pure positive
fixture correction: one failure was the unqualified empty-analysis case above,
one was the superseded source fact, and one independently reproduced missing
report failure health. SQL was not repeated for the pure fixture correction.

The finite cycle body measured **0.933 seconds** for **3 accelerated business
dates (2026-09-14/15/16)**, **3 Runtime/Repository reconstructions** and **6 real
Procrastinate report-job triggers**. It used the actual migrated PostgreSQL
repository, bounded normal-queue workers and existing report lease/outbox logic.
Injected `TimeoutError` and an unexpected builder exception were synthetic fault
stimuli; quota refusal came from the real SQL processing budget while preserving
urgent reserved capacity. This did not measure a sixty-second deadline or kill
and restart an OS process. The clock advanced across dates and past the existing
90-second lease; it did not simulate elapsed uptime by sleeping.

| Accelerated date / fault | Failure health observed | Recovery observed |
| --- | --- | --- |
| Sep 14 / timeout | missing, no safe error detail | 1 report, 2 unique intents |
| Sep 15 / quota exhausted | stale, no safe error detail | 2 reports, 4 unique intents cumulatively |
| Sep 16 / unexpected exception | stale, raw RuntimeError escaped, no safe error detail | 3 reports, 6 unique intents cumulatively |

All three cycles recovered after reconstruction and lease expiry, restored
`ok` on commit, became `stale` after six accelerated minutes, rejected stale
build tokens and produced no duplicate daily report or recipient/revision
intent. The separate original real-queue case also preserved urgent delivery
while normal delivery was blocked; its channel remains explicitly dry-run.
The missing/degraded-health assertions were collected after recovery, so their
failure did not suppress observation of the complete three-cycle sequence.
C received this exact persistence-backed red evidence.

Bounded repeatable-read/read-only snapshots of the scoped database compared all
original schema/relation identities, bounded table-row multisets and sequence
states: **equal before/after**, **1 schema, 73 relations, 29 data objects,
818 table rows** at both boundaries. No new schema remained. The final selected
container read confirmed the same running identity, pinned image and loopback
mapping. This proves bounded logical preservation, not physical-volume identity.

Scoped Ruff check and format check for the two new integration files and
`git diff --check` passed. The same bounded selection with `--collect-only -q
-p no:cacheprovider` collected **34 cases in 0.63 seconds**, exit **0**, after
adding the exercise negative; collection is not SQL execution. No full suite,
C1 replay, build, dependency change,
provider/model/source request, private configuration read, external send, phone
window or continuous polling occurred. **Verdict: baseline defects reproduced
and regression expectations frozen; final business acceptance remains pending
owner repair and exact I integration.** Three accelerated dates and subsecond
cycle-body execution do not establish fourteen-day operation, daemon uptime,
SLA, real market accuracy, platform/phone delivery or production acceptance.

## Final business acceptance on integrated candidate 69a43a8

E independently accepted candidate
`69a43a8cc9842ed5acbe9f5def7b93034f4049d9` on 2026-09-12. A fresh
`git -c http.proxy=http://127.0.0.1:7890 -c http.version=HTTP/1.1 ls-remote origin refs/heads/songconmaisaix31-design/oil-v01-i`
matched that full SHA; both original I and E worktrees were clean. E used a
normal fast-forward merge from `8fbf808cb8e015f5688c646caa2e2e6acdaf21d6`
to the exact candidate before testing, without changing source or expectations.

Git ancestry and per-path blob comparisons verified all **12 changed paths**
against the original owners: M `c4e41982fd1128c513d3b89750e7586eb23abb30`,
AB `19c9194164eb42f6e16a29c628039118a20aeef4`,
C `0593954a18837b9c9d4ec732b8f7cc27e9d4fe57`, and
E `8fbf808cb8e015f5688c646caa2e2e6acdaf21d6`. No unassigned changed path was
present relative to accepted I `78e5363d7c7da5d6bb76c3be6296b1f6e4010d87`;
all other tracked files, dependency inputs, original fixtures and tests were
unchanged. The existing assessment test gained a separate test function only.
`git diff --check` passed. The corrected frozen positive preconditions and
original exercise negative remained intact.

E read the exact retained I dispatch `ctx_6d240a3b2a66` using bounded
`orca orchestration worker-show` / `worker-read --source transcript --limit 14`.
The actual tool result showed **217 passed, 1 existing AnyIO deprecation warning,
6.19 seconds, exit 0**, and the subsequent exact-candidate offline wheel/sdist
build result exited **0**. This was I's run, not another E execution; the bounded
transcript was clipped outside the inspected result blocks. E also read the
existing `oil_agent-0.1.0-py3-none-any.whl` and `oil_agent-0.1.0.tar.gz` in
`C:/Users/DW/AppData/Local/Temp/oil-agent-i-business-ctx-6d240a3b2a66/dist`:
both contained the exact I worktree bytes for the two changed service modules
and declared 14 dependencies. Windows CRLF bytes differ from Git LF blobs but
match after line-ending normalization. Initial E artifact-reader assumptions
about directory file count and raw Git/archive byte equality failed; narrowing
to the two existing archives and checking both checkout bytes and normalized
Git content resolved those inspection-helper errors without modifying artifacts
or product code. E did not repeat I's test union, Ruff or build, install a
package, or execute an installed distribution.

E then ran **once** the same frozen seven-target pytest command printed in the
business baseline above, now containing **34 cases**, on the exact candidate:

```text
uv run --offline --locked --no-sync pytest tests/integration/test_business_reports.py tests/integration/test_business_cycles.py tests/integration/test_corpus_replay.py::test_T03_two_domains_do_not_create_two_independent_publishers tests/integration/test_postgres_pipeline.py::test_T04_independent_late_evidence_upgrades_same_persisted_event tests/integration/test_postgres_pipeline.py::test_T05_lower_severity_denial_corrects_original_authorized_recipients tests/integration/test_contextual_guards.py tests/integration/test_postgres_operations.py::test_T14_real_normal_queue_block_does_not_delay_urgent_delivery -q --tb=short -s -p no:cacheprovider
```

Actual result: **34 passed, 0 failed, 0 skipped, 6.31 seconds, exit 0**.
The child process ran from **14:49:57.177368 UTC to 14:50:05.391588 UTC**,
measured wall time **8.214 seconds**. The finite cycle body measured
**0.947 seconds**, with **3 accelerated business dates (2026-09-14/15/16)**,
**3 Runtime/Repository reconstructions** and **6 real Procrastinate report-job
triggers**, using the actual migrated E PostgreSQL repository and outbox.

| Accelerated date / injected fault | Safe failure state | Recovery / cumulative durable rows |
| --- | --- | --- |
| Sep 14 / timeout | degraded, `timeout` | ok, 1 report / 2 unique intents |
| Sep 15 / actual SQL quota refusal | degraded, `quota_exhausted` | ok, 2 reports / 4 unique intents |
| Sep 16 / unexpected builder exception | degraded, `invalid_output` | ok, 3 reports / 6 unique intents |

The frozen tests now pass for Chinese conditional impact and watch citations,
latest-source correction without stale facts, exercise/denial/invalid-reference
guards, cutoff exclusion and missing-price uncertainty. Ordinary events remain
silent; same-origin reposts are not independent evidence; independent follow-up
and correction to the original authorized recipients pass. Each report cycle
preserves the existing 90-second lease, suppresses an immediate rebuild,
recovers the current business date after expiry, rejects a stale token, stays
unique under a repeated queue trigger, restores healthy state on commit and
becomes stale after six accelerated minutes. Urgent budget reserve and the
original actual normal/urgent queue isolation case also pass. No assertion was
weakened and no new test or product change was needed for this acceptance.

Before connecting, E freshly verified container
`b3c3a345428590922eb8e628a996dd634cb3333e5f0c86f588eede8fb7101cab` /
`oil-agent-e-postgres-1`, project/service `oil-agent-e` / `postgres`, the exact
original E Compose directory and two config labels, pinned image and image ID
`sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb`,
sole local volume `oil-agent-e_postgres-data`, only loopback
`127.0.0.1:55434:5432`, and database/user `oil_e_test` / `oil_e_test`.
The endpoint and complete resource paths are recorded in the baseline section.
The existing synthetic password was captured only from that container into
memory for the child process; no raw password/DSN was emitted, saved or placed
in global environment. Only fixture-created `e_acceptance_<UUID>` schemas were
created and dropped; no preexisting resource was started, stopped or altered.

Bounded repeatable-read/read-only logical snapshots were **identical** before
and after: **1 original schema, 73 relation identities, 29 data objects and
818 table rows**, including full bounded row multisets and sequence states.
No new schema remained. All selected container and volume metadata matched
before/after, including running state, mount, labels, configured/active port,
image, start time **2026-09-12T12:25:48.707130701Z** and restart count **0**.
This is logical preservation evidence, not physical-volume byte identity.

**Verdict: PASS for this bounded integrated event/report business behavior and
real E PostgreSQL recovery increment.** It closes the qualified baseline's
empty analysis, superseded fact and invisible report-failure defects. Only this
existing evidence file is appended after acceptance. I must integrate the
evidence commit; no further code repair was identified in the frozen selection.
Synthetic timeout/unexpected exceptions are fault stimuli, and notification
delivery uses dry-run channels. Runtime objects were reconstructed, not OS
processes killed. Accelerated dates and bounded queue jobs do not establish
fourteen-day operation, sixty-second deadline timing, daemon uptime, SLA,
installed-product behavior, actual market accuracy, provider/source/model
transport, real sending, platform/phone/login/callback or production acceptance.
No full-suite/C1 replay, new Docker resource, shared restart, private C1 read,
external product call, continuous polling or purchase occurred.

## C1 dedicated database host-path diagnosis and bounded stdio proof

On 2026-09-12, E investigated the concrete C1 assembly blocker under dispatch
`ctx_13fb0d6d365e`. Accepted I `6f70295768fa3eb98e92cf4cdfd1a6135ab99df8`
and M governance `c28106623e3d3a5163016a4dbf7507738719ca36` were normally
merged, preserving history, at E source
`75ee3eee768cd0fca48f89cce8b7f5765927e7c0`. No deployment or helper source
was changed for this diagnosis; only this existing evidence file is appended.

Selected metadata reads used only
`docker --host npipe:////./pipe/dockerDesktopLinuxEngine` and these approved
resources, without dumping container environment or reading private files:

- Container `5ab6d8fb192e33242f51a6b80e3e768eb4421fbd81de80c5627d02a161583b76`,
  name `oil-agent-feishu-trial-postgres-1`, project/service
  `oil-agent-feishu-trial` / `postgres`, scope/dataset `feishu-c1`,
  provenance `fixture`.
- Compose workdir `C:/Users/DW/orca/workspaces/oil-agent/oil-v01-i` and config
  `C:/Users/DW/orca/workspaces/oil-agent/oil-v01-i/deploy/compose.c1-db.yaml`.
- Image reference `postgres:16-alpine@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb`
  and the same image ID, with sole local volume
  `oil-agent-feishu-trial_c1-data` at `/var/lib/postgresql/data`.
- Sole bridge network `oil-agent-feishu-trial_backend`, ID
  `a2a3036e03807d1840b9b5c01135349eeeaf7168d10755b26cdfa6b625569ef5`,
  internal `true`, IPv6 `false`, and only the approved container attached.
  Its address was `192.168.96.2/20`, gateway empty.
- Running and healthy; start time `2026-09-12T15:34:52.072399985Z`, restart
  count `0`; HostConfig requested `127.0.0.1:55436:5432`, while actual
  NetworkSettings ports were exactly `{"5432/tcp": []}`.

One Windows `socket.create_connection(("127.0.0.1", 55436), timeout=3)`
failed with `ConnectionRefusedError`, Windows error **10061**, after **2.036
seconds**. One fixed in-container command
`docker --host npipe:////./pipe/dockerDesktopLinuxEngine exec <exact-container-id> pg_isready -h 127.0.0.1 -p 5432 -U oil_c1_trial -d oil_c1_trial`
returned **exit 0**, `127.0.0.1:5432 - accepting connections`. These are
readiness/protocol observations, not authenticated SQL or schema inspection.
An initial selected-network JSON formatter had a missing closing brace;
correcting that inspection-helper syntax resolved its parse error without
changing resources or product code.

**Reproduced blocker:** the healthy PostgreSQL service has no effective Windows
host publication in this internal-only topology. Requested PortBindings do
not prove an active endpoint. Docker Desktop documents that the host cannot
directly route to the Linux bridge network and relies on published ports;
the upstream internal-only publication discussion corroborates this symptom.
These references explain the observed path failure, rather than proving an
uninspected daemon version or all possible internal-network behavior:
[Docker Desktop networking](https://docs.docker.com/desktop/features/networking/networking-how-tos/),
[Moby internal-only publication discussion](https://github.com/moby/moby/discussions/53256).
C's helper correctly refuses the absent actual endpoint and reports
`C1_DB_EFFECT_UNKNOWN` after creation; it must not reinterpret that result as
successful host connectivity or automatically repeat/clean up the effect.
C reported that migration had not run; E did not execute migration.

The existing pinned image's `/bin/busybox nc --help` succeeded and identified
BusyBox **1.37.0**, including its client-mode timeout option. E then ran one
fixed, bounded no-authentication probe from Windows:

```text
docker --host npipe:////./pipe/dockerDesktopLinuxEngine exec --interactive --user postgres <exact-container-id> /bin/busybox nc -w 3 127.0.0.1 5432
```

Python `subprocess.run` supplied exactly `struct.pack("!II", 8, 80877103)`
(the eight-byte PostgreSQL SSLRequest), captured output, and imposed a
six-second parent timeout. Result: **exit 0**, **3.145 seconds**, one response
byte **N**, empty stderr. No username, password, query or application payload
was sent. This proves the fixed Docker stdio path reaches PostgreSQL; it does
not prove authentication, migration, a working connection pool or an implemented
host bridge. `/bin/busybox timeout --help` also confirmed an in-container
TERM/kill-grace deadline mechanism is already available without an image change.

The minimal repair contract was handed to M, who assigned it to C in
`msg_40b6137092c1`: retain the exact container, volume and internal network;
C owns a bounded process-owned Docker stdio transport and helper validation,
and I owns only fixed-child wiring. A host-side bridge must bind only the
approved loopback address/port and use fixed endpoint/container/user/target
argv, without a shell or configurable nc listener/execute flags. Bound
connections and child lifetimes explicitly; the current SQLAlchemy engine
uses default pool sizing, so an existing small pool cap must not be assumed.
Use a hard in-container deadline as well as parent cleanup, because terminating
only the Docker client does not establish remote-child termination. The probe's
three-second timeout is not the runtime idle allowance for the approved
120-second exercise. Refuse bind/identity uncertainty, close only owned sockets
and children, and never blindly replay an uncertain database operation.
Keep native publication checks strict outside the explicit transport mode;
require actual transport and database binding before the existing
`runtime.cli migrate` path, with process-scoped DSN injection and no queue
initialization/recovery expansion. Authenticated validation and lifecycle tests
remain C/I work followed by independent E acceptance.

This option adds no image, persistent service, network attachment or fee; its
cost is bounded Docker exec/BusyBox children per active database connection
and explicit process-lifecycle handling. Static inspection of existing general
trial templates found a broader app-image/multiservice assembly, not an already
verified C1 application process; E did not enumerate or probe unknown resources.
Adding a normal network to PostgreSQL would change its isolation and was not
used. No Compose-only edit can be accepted here merely to obtain a reachable
port while weakening the approved internal boundary.

The single focused command
`uv run --offline --locked --no-sync pytest tests/integration/test_c1_database_deploy.py -q --tb=short -p no:cacheprovider`
returned **5 passed in 0.33 seconds, exit 0**. It includes actual captured
Compose rendering with synthetic credentials and existing boundary assertions;
it is configuration evidence, not a Docker publication or connectivity fix.
No new test case, full suite, SQL replay, build or dependency change was needed.

A final selected container/network read at **15:44:23.203363 UTC** exited **0**
and confirmed the same running/healthy identity, image, start time, restart
count, volume mount, internal network and endpoint, configured binding and
absent actual published port. E did not start, stop, restart, recreate or
remove a resource, alter a network, inspect credentials, authenticate to SQL,
or read database contents. This is selected metadata preservation evidence,
not an independent logical/physical comparison of database data; protocol
readiness requests may themselves produce server logs.

**Verdict: diagnosis and minimal existing-container transport feasibility
confirmed; actual host database access remains blocked pending C repair and
I integration.** The bounded SSL byte exchange is not authenticated SQL,
migration, installed-product behavior, autonomous two-card execution, platform
or phone receipt, or production acceptance. No provider/source/model request,
Feishu call, send, exercise start, new resource or purchase occurred.

### Additional local compatibility checkpoint requested by M

Before settlement, M requested bounded independent verification of published I
`1b28e6b74c81fd5da3886699f065c5b5782c1110` in `msg_8d6b782dcf38`.
An independent command-scoped proxy/HTTP/1.1 `git ls-remote origin
refs/heads/songconmaisaix31-design/oil-v01-i` matched that exact SHA.
I HEAD also matched, but its worktree already contained staged D channel
integration changes, so E did not run candidate tests in that changing tree.
E normally merged the exact checkpoint into the retained E branch at
`127179b152b2e8b76515fb6f4c09223d84f7ce09`, preserving this evidence append.
The committed E tree equaled the complete I candidate tree, with only this
evidence file differing in the working tree before execution.

Git verified exactly seven changed paths versus accepted I `6f702957`: the
six C-owned source/test files and M's existing board. Each blob matched its
owner: DTO and contract tests from
`f194225f0dcb96354c7fd63c666a7ac3cc75cc27`; local configuration, private
field mapper, local preparation and local tests from
`f5cd36560b3869c79f53bead9a758120aba297a2`; V01 from
`21d7d7ec62a282e08afcde00c0147d56c8db3f44`. All owners and the accepted
baseline were ancestors; all other tracked paths were unchanged. The original
contract test file remained an exact prefix of the new version.

E ran only
`uv run --offline --locked --no-sync python -B -m pytest tests/unit/runtime/test_c1_contract.py tests/unit/runtime/test_c1_local.py -q --tb=short -p no:cacheprovider`:
**32 passed, 0 skipped, 0 failed, 0.41 seconds, exit 0**. These tests use
synthetic values, a temporary Windows file and mocked child/resource operations;
they do not access the real protected configuration or database. They preserve
the original fixture exercise and permit only the two additional exact approved
title/body pairs, rejecting altered or mixed pairs. They also cover null-only
local mapping, refusal to reset or bind unrelated fields, fixed child arguments,
secret stdin/environment filtering, wrong-host/missing-secret refusal, existing
resource refusal without a retained ID, and preparation without a start window.

**PASS for this local compatibility and closed-card contract increment only.**
M reported I's separate 68-case run; E did not replay that larger selection.
These tests do not accept the real private-file state, authenticated database
transport, migrations, queue installation, runner lifecycle, elapsed 120-second
automation, real Feishu delivery or phone receipt. C's transport and the later
I runner integration still require their own concrete candidate and independent
acceptance. No C/I source or test was edited by E.

### Final ready C/D card and request-observation checkpoint

M subsequently requested the concrete ready checkpoint
`d27368a37af85be7ab3ec87a1a948dd8c24b9dc8` in `msg_b8d6a5afbe13`.
Independent `git ls-remote` matched that exact I SHA; I HEAD matched and
`git status --porcelain=v1` was empty. It normally merges D
`7a74236c1a6cf68ab5eef8438f7520772ddf60b3` onto the checked compatibility
checkpoint `1b28e6b`. All ten new channel/test/document blobs matched D exactly,
and the prior seven C/M paths were unchanged: **17 authorized paths total**
versus accepted `6f702957`, with no other change. AST comparison of every
preexisting test function in the two affected channel test files passed.

E normally merged this exact checkpoint at
`8ab2788643afd16f4c8f3ecc6d1a2619cb9f4f09`, keeping the already pushed
diagnosis/compatibility evidence `dc4f57668b8de05a35a974f180702e1adf20f9c9`.
E was clean before execution; all tracked paths equaled the candidate except
the existing E evidence file. Only the direct two-card and request-observation
selection was executed, without repeating the compatibility or full channel
suite:

```text
uv run --offline --locked --no-sync python -B -m pytest tests/unit/channels/test_c1.py tests/unit/channels/test_tenant_lookup.py -k 'autonomous_exercise or two_exercise_tasks or c1_observes or observer_failure or observed_transport or observed_http or response_observation or tenant_lookup_observes' -q --tb=short -p no:cacheprovider
```

Result: **27 passed, 56 deselected, 0 skipped, 0 failed, 0.21 seconds, exit 0**.
The selection checks both exact exercise cards, noninteractive fixture labels,
rejection of altered scope before a request, distinct stable task send keys,
reservation/start/response ordering, omission of cached token requests, and
safe classifications for pre-request recorder failure, post-response recorder
failure/timeout, transport failure and nonaccepting HTTP responses. It also
checks tenant-query observation with the exact reservation. All requests use
`httpx.MockTransport` with synthetic identities and responses. No real provider
request, recorder persistence, private configuration or database operation ran.

**PASS for the bounded C/D local implementation checkpoint.** M reported I's
separate 44-case run; E did not repeat it. No runner, durable recorder or new
runtime integration glue is accepted by this checkpoint. Authenticated database
transport/migration, actual runtime lifecycle, first accepted-at plus 120-second
timing, platform acceptance and phone receipt remain unexecuted and require the
later concrete C/I delivery and explicitly authorized exercise. Only this
evidence append was authored by E; owner source and assertions remain intact.

## C1 stdio short-response check and scoped connection-budget regression

Under E dispatch `ctx_cb7006602d1c`, on 2026-09-13 local time, E normally
merged accepted I `f688b78e997deda0bfd60fdfd8965adc2c500a06` at
`d0666a3ab4ad5692a8900b636ff47307fd79823a`. The bounded target was C's
existing `c1_stdio.py` byte flow and fixed child lifecycle, without accessing
Docker, the dedicated database, credentials or protected configuration.

E ran one in-memory Python probe using the actual bridge implementation with
only its Docker child replaced by an explicitly synthetic local Python child.
The test listener used an ephemeral loopback port instead of the approved live
port. The double read the eight-byte SSLRequest, flushed one byte `N`, waited
for another input byte, returned `Z`, and remained alive awaiting further input.
The original fixed Docker argv, unbuffered pipes, upload partial-write loop and
`os.read` download path were preserved and checked; Docker was never invoked.

Result from `uv run --offline --locked --no-sync python -B -`:
**exit 0**; first short response in **0.458076 seconds**, second bidirectional
exchange in **0.000081 seconds**, both before child EOF; complete probe body
**0.520282 seconds**. Exactly one owned child and the temporary listener closed
on exit. **No EOF-buffering defect was reproduced** on this source, so E did
not add an alternative bridge or a speculative streaming regression. This
local child bypasses Docker startup and cannot prove Docker protocol latency,
authentication or PostgreSQL readiness.

M relayed C's actual observations in `msg_3dba726c9c89`: bridge SSLRequest
completed in **5.175 seconds**, direct persistent Docker stdio in **4.79
seconds**, exceeding the existing three-second connection budget. This is
C-reported live evidence, not an E resource probe. E independently froze
`tests/integration/test_c1_connect_budget.py`: the real SQLAlchemy engine's
`do_connect` event captures the final driver arguments and raises before any
DBAPI network/authentication operation. The regression requires 15 seconds for
the exact `feishu-c1` fixture and preserves three seconds for ordinary and
similarly named fixtures, plus the existing UTC/statement timeout settings.

Baseline command:
`uv run --offline --locked --no-sync python -B -m pytest tests/integration/test_c1_connect_budget.py -q --tb=short -p no:cacheprovider`
returned **1 failed, 2 passed in 4.67 seconds, exit 1**; the exact C1 case
failed with `assert 3 == 15`. No database connection was opened.

E then normally merged exact C repair
`2a3e7faade6b167d42f78eec29e1e0e0b1515a8d` at
`ca0d11fab08bc1c9d66f624a05b0587220558ca7`, without editing C source or tests.
The unchanged three-case E regression plus C's existing constructor regression:
`uv run --offline --locked --no-sync python -B -m pytest tests/integration/test_c1_connect_budget.py tests/unit/runtime/test_c1_connection.py -q --tb=short -p no:cacheprovider`
returned **4 passed in 2.25 seconds, exit 0**.

Two additional E cases exercise Procrastinate's locked `_create_pool` path with
the real psycopg pool constructed using `open=False`; neither `open_async` nor
connection workers run. They confirm the effective default driver/acquisition
budgets remain **3/5 seconds**, while the explicit C1 option gives **15/17
seconds**, preserving pool bounds **1..4** and UTC settings. Psycopg's
`getconn` uses this pool timeout when no per-call timeout is supplied.
`uv run --offline --locked --no-sync python -B -m pytest tests/integration/test_c1_connect_budget.py -k queue_acquisition -q --tb=short -p no:cacheprovider`
returned **2 passed, 3 deselected in 1.43 seconds, exit 0**. These inspect a
closed real pool's configuration, not actual slow connections or SQL recovery.
Scoped Ruff check and format check passed for the new E test file.

E's owner handoff `msg_35be2a93c26a` also identifies a remaining assembly limit:
at this exact checkpoint, `c1_local.database_ready` still calls
`create_queue_app` without the new timeout option. The later C/I C1 queue
assembly must explicitly pass 15; the constructor's optional support alone is
not end-to-end queue readiness. M relayed C's subsequent authenticated database
identity success in `msg_6185ef347f10`, with migration still unexecuted at that
receipt; E did not independently run authentication or inspect database state.

**Verdict: no short-response/EOF fault found in the bounded local child check;
C1 driver-budget regression reproduced and the exact owner repair passes the
independent driver/pool configuration checks.** Only the focused E integration
test and this existing evidence file were authored by E. Original assertions,
stdio argv/lifecycle and all existing project resources remain untouched by E; no full suite,
build, private read, real database operation, migration, provider request,
send or exercise start occurred. I integration and later actual C1 queue/runtime
verification remain required; phone receipt, autonomous 120-second timing and
production acceptance are not claimed.

Before settlement, M supplied final C source
`2b3b8d54fd9abbeedd7babb9051a8f01d6d0ffbe` in `msg_a27cf78a83c4` for
read-only call-site verification. AST inspection confirmed all three C1
`create_queue_app` calls now explicitly pass `connect_timeout=15`:
`c1_local.py` lines 188 and 383, and `c1_runner.py` line 158. Its storage and
queue-constructor blobs equal the already checked `2a3e7fa` blobs. This closes
the call-site omission in source only; no runner execution or final I integration
was independently verified in this task.

The same comparison caught a changed stdio lifetime configuration: hard/idle
arguments are now **1800/1800 seconds**, previously **240/180 seconds**;
the byte-flow implementation is unchanged. An initial assumption of whole-file
equality therefore failed and was narrowed to the actual unchanged constructor
blobs. The earlier local-child fixed-argv check is not presented as acceptance
of these later lifetime settings. They remain part of the later exact-candidate
lifecycle verification, with no additional live probe or broad audit here.

## C1 two-task PostgreSQL and final local preparation acceptance

E dispatch `ctx_00211d421bdc` independently checked executable I source
`75a6fc4b7e0cd00fc82fdb49a4cc8cc615b67c9a`, normally merged into retained E at
`9503e0569f66a396ae64f105d9d12ee09e48b9e9`; their committed trees were identical.
Published I delivery `cc4c13b8f990c136ff222e2a3a0da1ec34537d38` differs from that
executable checkpoint only in `V01-TODO.md` and `config/c1-preparation.md`.
Independent `git ls-remote` matched that exact I SHA and its worktree was clean.
Owner blob checks preserved C `2b3b8d54fd9abbeedd7babb9051a8f01d6d0ffbe` and
the prior E `82cadafde1ff2c8191de557d8a4978854b8b5476` tests/evidence. Only the
new E integration test below and this evidence append were authored here.

I reported 62 focused checks, the scoped lint/format checks and eight entry
outcome probes; E did not repeat those tests. E inspected the actual successful
offline wheel/sdist build receipt from I dispatch `ctx_f3e355899a8e` and read
its existing artifacts under
`C:/Users/DW/AppData/Local/Temp/oil-agent-i-c1-ctx-f3e355899a8e/dist` without
rebuilding or installing. Eight relevant helper/bootstrap/queue/storage members
in both archives matched the final source after line-ending normalization;
the wheel declared 14 dependencies. This is artifact/source evidence, not an
installed-product execution.

### Five focused cases on the existing E PostgreSQL database

`tests/integration/test_c1_two_task_postgres.py` reuses `e_repository`, its real
migrations and fresh `e_acceptance_<UUID>` schemas, plus the existing explicitly
synthetic C1 configuration builder. The five cases cover:

- Concurrent deduplication of each distinct task/outbox, refusal before the first
  accepted receipt and before its exact 120-second due time, and shared durable
  limits of three send reservations and twenty total requests across both tasks.
- Per-reservation scope/order checks, concurrent idempotent observations,
  transport uncertainty, repository reconstruction and durable stop refusal.
- Durable UNKNOWN and stopped states returning before the queue can open or any
  request can be reserved; these are two parameterized cases.
- An actual Procrastinate worker automatically executing two durable jobs on
  real wall time with a synthetic channel, then returning completed after
  repository/runtime reconstruction without another job or send.

E reverified only container
`b3c3a345428590922eb8e628a996dd634cb3333e5f0c86f588eede8fb7101cab`, name
`oil-agent-e-postgres-1`, project/service `oil-agent-e`/`postgres`, original E
`deploy` workdir and `compose.yaml`/`compose.e-test.yaml` labels, volume
`oil-agent-e_postgres-data`, database/user `oil_e_test`, and configured/active
loopback-only `127.0.0.1:55434:5432`. Its image was
`postgres:16-alpine@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb`.
It was already running healthy, started at `2026-09-12T12:25:48.707130701Z`,
restart count zero. Only this exact container's project synthetic password was
captured in process memory for the scoped test child; it was not printed,
written to a file or placed in a global environment.

Collection returned **5 cases in 0.20 seconds, exit 0**. The first actual run:

```text
uv run --offline --locked --no-sync python -B -m pytest tests/integration/test_c1_two_task_postgres.py -q --tb=short -s -x -p no:cacheprovider
```

returned **2 passed, 1 failed in 2.95 seconds, exit 1**, stopping at the new E
harness's missing required `App(connector=...)` argument. E corrected only that
constructor to use a real closed connector with an explicit forbidden-open
assertion, preserving all business assertions. No product repair was needed.
The process ran from `2026-09-12T16:24:52.928686Z` to
`16:24:57.624751Z`, **4.696 seconds**. The remaining three cases were then run:

```text
uv run --offline --locked --no-sync python -B -m pytest tests/integration/test_c1_two_task_postgres.py -q --tb=short -s -x -p no:cacheprovider -k 'durable_unknown or real_queue'
```

Result: **3 passed, 2 deselected in 122.81 seconds, exit 0**; process
`2026-09-12T16:25:59.824715Z` to `16:28:04.386535Z`, **124.562 seconds**.
All five cases therefore passed across the two bounded executions after the
E-only harness correction; this is not a claim of one clean five-case run.
Scoped Ruff check and format check passed for the new test.

The actual queue case recorded first synthetic acceptance at
`2026-09-12T16:26:03.428431Z`, durable second due time
`16:28:03.428431Z`, and second synthetic acceptance at `16:28:03.812655Z`:
**120.384224 seconds apart**, with **120.822 seconds** measured flow-body time.
There were exactly **two real successful queue jobs, two synthetic sends and
three reserved/started/responded synthetic requests**; no uncertainty/failure
remained in that case. No calendar acceleration or agent-issued second send
was used. The test channel returns synthetic receipt DTOs and records synthetic
request observations; it makes **zero platform requests**. These timings prove
the local real-queue schedule, not Feishu acceptance latency or phone receipt.

Both runs compared bounded logical inventories of only this E database before
and after: **1 schema, 73 relations, 29 data objects and 818 table rows**.
The complete bounded row multisets and sequence states matched; the fixtures'
new schemas were removed and no preexisting schema/data changed. Selected
container/volume/binding/running metadata matched before and after. E did not
create, restart, stop, prune or alter an existing Docker resource.

### Actual protected C1 readiness on the final I source

After M relayed C's completed preparation and released the dedicated resource
for E read-only checks in `msg_20a1d58748a6`, E used final I `cc4c13b` directly.
Before access, checked-out protected helper bytes matched C `2b3b8d5`, and the
existing protected loader verified the explicitly authorized project path,
owner/ACL/reparse/link/schema constraints. No credential or identity value was
printed. The only absent fields were `tenant_key` and `exercise_start`.

Exact resource proof covered container
`5ab6d8fb192e33242f51a6b80e3e768eb4421fbd81de80c5627d02a161583b76`, name
`oil-agent-feishu-trial-postgres-1`, project/service
`oil-agent-feishu-trial`/`postgres`, original I workdir/Compose path, the same
pinned image above, volume `oil-agent-feishu-trial_c1-data`, and sole internal
network `oil-agent-feishu-trial_backend` with ID
`a2a3036e03807d1840b9b5c01135349eeeaf7168d10755b26cdfa6b625569ef5`.
The existing configured loopback binding and empty native runtime port mapping
were retained; connectivity used C's fixed-container process-owned stdio path.

Each command below ran once through the final I isolated interpreter, with
captured redacted output, no stderr and **exit 0**:

```powershell
& 'C:/Users/DW/orca/workspaces/oil-agent/oil-v01-i/.venv/Scripts/python.exe' -I -B -m oil_agent.runtime.c1_local db-status
& 'C:/Users/DW/orca/workspaces/oil-agent/oil-v01-i/.venv/Scripts/python.exe' -I -B -m oil_agent.runtime.c1_local status
```

`db-status` returned **C1_DB_READY**, empty fields, from
`2026-09-12T16:30:13.645668Z` to `16:30:30.772905Z` (**17.127 seconds**).
`status` returned **C1_NOT_STARTED**, field `exercise_start`, from
`16:30:30.773204Z` to `16:30:46.414534Z` (**15.641 seconds**).
One subsequent explicit read-only SQL transaction through the same protected
bridge verified database/user `oil_c1_trial`, migration head `0003_trial`, and
a readable real Procrastinate queue. Aggregate counts were all zero: queue
jobs, recorded provider calls, permissions, exercise subjects and request
observations. These are observed database records, not independent evidence
about unobserved external activity. C performed the prior migrations; E did
not rerun them or independently prove C's earlier before/after preservation.

During that authenticated read-only connection, selected process inspection
observed **one `nc`, one `timeout`, hard/idle arguments 1800/1800 seconds and
one loopback listener**. At completion `2026-09-12T16:31:08.183897Z`, these
counts all returned to zero, matching the precheck; selected resource metadata
and protected file bytes/file identity were unchanged, with protected path/ACL
checks passing again. This verifies final-context arguments and ordinary
cleanup; it does not test waiting thirty minutes for expiry or an OS crash.
The earlier 240/180-second local-child evidence remains limited to its original
source. The dedicated database remained running with no topology/resource or
private-configuration mutation by E.

### Verdict and remaining user action

**PASS for the bounded PostgreSQL/queue implementation and actual source-worktree
C1 local readiness.** No C/D/I domain defect was reproduced in this scope.
There was no live start, tenant lookup, platform send or phone observation.
The new tests never write the user's actual private `exercise_start`; all test
identities, bindings, permissions, failures and receipts are synthetic and
isolated in disposable E schemas.

From an interactive local terminal the reviewed entry command is:

```powershell
& 'C:/Users/DW/orca/workspaces/oil-agent/oil-v01-i/.venv/Scripts/python.exe' -I -B -m oil_agent.runtime.c1_local start
```

Only the user's invocation opens the actual permission window. With the same
interpreter/module, `status` is the read-only command observed above; `stop`
records the exercise stop and `resume` retains its identity/budget. E reviewed
those entry paths and tested durable stop/UNKNOWN/completed reconstruction on
synthetic E state, but did not invoke actual private `start`, `stop` or `resume`.
UNKNOWN is not permission to resend. Live execution still must establish the
missing tenant binding under the approved shared request budget, send only the
two approved cards to the sole authorized recipient, and provide separately
platform IDs/timestamps, autonomous second timing, final accounting and the
user's phone feedback. No real-source/model, SLA, continuous operation or
production acceptance is claimed. I still integrates this E test/evidence commit.
