# E runtime verification

Provider replies and market content in this report are synthetic. Actual local
file/ACL observations are labeled separately. No source license, production
account, model, Feishu recipient, phone receipt or deployed server is accepted.

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
