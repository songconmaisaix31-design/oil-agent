# Oil Agent verification and operations runbook

This E runtime increment uses the reviewed AB/C/D implementations and the supplied
development plan v1.0. [Runtime checks](../e2e/runtime-checks.md) record exact
candidates, results and unresolved gates. [Baseline checks](../e2e/baseline-checks.md)
remain historical evidence, not the current application status. This checkout
provides local synthetic acceptance and a Linux Compose reference; I still owns
final integration and real deployment remains an external gate.

No deployment, account login, commercial-source request, paid product model call
or customer message is authorized by this document. Ordinary local development,
tests, commits and pushes to the existing origin are already authorized.

## Available local checks

Run from the checkout root with Python 3.13 and uv 0.11.26:

```powershell
uv sync --locked
uv run --locked python scripts/validate_scenario_corpus.py
uv run --locked pytest tests/contracts tests/unit -m 'not postgres' -q
uv run --locked pytest tests/integration -q
uv run --locked ruff check tests/integration deploy/worker_health.py fixtures/runtime_factory.py
git diff --check
```

The checker reads [fixed synthetic scenarios](../fixtures/scenarios/v01.json)
and performs consistency checks only. Its PASS is not a T01-T28 application PASS.
The integration command requires a deliberately injected `OIL_E_TEST_DATABASE_URL`:
`postgresql+psycopg`, host `127.0.0.1`, port `55434`, database/user `oil_e_test` and
the newly provisioned E test password. Without it, PostgreSQL cases explicitly
skip; that is NOT PostgreSQL acceptance. Each case migrates a unique schema then
removes only that schema. GitHub Actions uses its separate ephemeral `oil_e_ci`
database/user on 5432. C's own database-scoped unit tests are not pointed at E.
CI provisions a second isolated service on loopback 55431 (`oil_c_test`), migrates
it explicitly, and runs the complete C/AB/D unit/contract suite with
`OIL_TEST_DATABASE_URL` and `OIL_AB_PACKAGE_ROOT` set. Local E runs list those C
tests as deselected instead of borrowing a teammate's credentials or database.

In `web`, run `npm ci --ignore-scripts`, `npm test`, and `npm run build`. The build
checks generated types against C's OpenAPI before TypeScript/Vite. E browser checks
use the installed `playwright-core` and a new headless Chrome context; they do not
open existing profiles. Real phone behavior and OAuth are separate external gates.

## Linux Compose and local synthetic startup

### Integrated API and worker factory

The shared safe default is `oil_agent.bootstrap:build_runtime`. Both the API
factory `oil_agent.bootstrap:create_app` and `python -m oil_agent.runtime.cli`
load it when `OIL_RUNTIME_FACTORY` is unset or empty. `.env.example` and the base
Compose environment name the same executable path. A trusted explicit environment
override (or CLI `--factory`) is still honored; never accept a factory path from
an HTTP request or source content.

This factory constructs C's Runtime with the existing SafeQuoteParser,
ConservativeAssessmentService, SnapshotReportService and DryRunChannel. It
registers no sources or polling schedules and creates no users, recipients,
sessions, business configuration or sample records. First-report policy remains
unset; source/model/real identity gates remain disabled. Quote imports and daily
reports retain C's fixture labeling and database authorization. Worker ticks can
create an explicitly empty fixture report when due; that is not live monitoring.

After explicitly injecting a newly authorized PostgreSQL URL, run `migrate`,
`queue-schema` and `recover` in that order, then start the API and the separate
ingest/urgent/normal workers using the commands below. For a host API use
`uv run --locked uvicorn oil_agent.bootstrap:create_app --factory --host 127.0.0.1
--port 8000` as one command. Application startup does not provision or log in users.
`/readyz` validates the database schema, not any external capability. The separately
labeled E fixture override and its exact database guard are unchanged; select it
only for an explicitly scoped E rehearsal. I's fresh loopback 55435 database is
separate from C/E, with no reuse of their credentials or revoked browser sessions.

See [I's integration handoff](../config/integration-handoff.md) for the tested
candidate and final CI evidence. The original E screenshots and eight browser
flows remain evidence of the exact E/AB candidate recorded in runtime-checks.md;
they are not relabeled as a new I browser run.

### E-only rehearsal commands

Inspect exact `oil-agent-e` labels, port 55434 and port 18084 before starting. All
commands use the deliberately empty public `deploy/compose.env` to prevent automatic
loading of an unrelated `.env`. Inject a new isolated database password through
`OIL_POSTGRES_PASSWORD` and the matching internal DSN through `OIL_DATABASE_URL`
(host `postgres`, port 5432, database/user `oil_e_test`). Never print rendered
Compose configuration or environment values; use `config --quiet`.

```sh
docker compose --env-file deploy/compose.env -f deploy/compose.yaml -p oil-agent-e config --quiet
docker build -f deploy/app.Dockerfile -t oil-agent-app:e-local .
docker build -f deploy/web.Dockerfile -t oil-agent-web:e-local .
docker compose --env-file deploy/compose.env -f deploy/compose.yaml -f deploy/compose.e-test.yaml -f deploy/compose.e-runtime.yaml -p oil-agent-e up -d --no-build --no-recreate init api ingest urgent normal gateway
```

Run builds serially on a memory-constrained host. API and all three queue workers
use the same nonroot application image. PostgreSQL is internal-only in the base
file; the explicit E test override publishes loopback 55434. The gateway alone
publishes loopback 18084, serves D's static build and forwards `/api/`, `/healthz`
and `/readyz`. It preserves the API's 3,000,000-byte request limit with a 3m proxy
ceiling, allowing the canonical **2,000,000 raw byte** CSV/XLSX cap after base64.
Read-only filesystems, tmpfs, dropped capabilities, resource/log limits and restart
policies are configured. Worker health reads the actual named queue heartbeat and
fails after 150 seconds; a running process alone is insufficient.

`init` executes the real C CLI in sequence:

```sh
python -m oil_agent.runtime.cli migrate
python -m oil_agent.runtime.cli queue-schema
python -m oil_agent.runtime.cli recover
```

The worker commands are `python -m oil_agent.runtime.cli worker --queue ingest`,
`--queue urgent`, and `--queue normal`; `--once` drains available tasks and exits.
Do not run a second initializer concurrently. Existing queue schema detection is
not a queue-schema upgrade tool; review upstream migration requirements for any
future Procrastinate version change.

The optional `compose.e-runtime.yaml` mounts `fixtures/runtime_factory.py` read-only.
That factory accepts only test/dry-run and E's exact local database; it composes
the actual ReplaySource, ConservativeAssessmentService, SnapshotReportService,
SafeQuoteParser and DryRunChannel. It has no Feishu/OAuth/model/external source.
Omit this override outside local E tests. An approved production factory, HTTPS
termination, identity, licenses and operations ownership are still required.

For synthetic browser data, inject the host E DSN and `OIL_ENVIRONMENT=test`, then
run `uv run --locked python -m fixtures.runtime_factory --seed-session-file` with
an explicit new private file path outside Git. The seed creates only named E
synthetic users and fixtures, with a midnight test report schedule. Existing users
must match the exact synthetic scope. It saves newly generated test sessions
without printing them. Never reuse it for a real identity or production database.
Set `OIL_E_SESSION_FILE` to that newly created file and run:

```sh
node e2e/browser-runtime.mjs
uv run --locked python e2e/gateway-upload.py
```

Session material stays outside artifacts. Browser screenshots/results contain only
labeled synthetic content. The script directly exercises the gateway/API/PostgreSQL;
it blocks external requests without mocking local responses. A repeat run may
observe an already persisted acknowledgement; it must not erase that evidence.

Stop only E services after a rehearsal. Do not use `down`, `prune` or volume deletion.
Replacing the six stateless E-created services is permitted only within the verified
local ownership scope; preserve the PostgreSQL container/volume/networks. Record
old/new image and container IDs. Production rollout and compatible image rollback
require their own reviewed candidate and outage window.

## Isolation and secrets

E's reserved PostgreSQL host port is `55434` and Compose project name is
`oil-agent-e`. Reservation is not proof of availability. Immediately before any
future start, check the port listener, inspect only resources with the exact E
Compose project label, record the intended database/service/volume names, and
confirm ownership. If occupied by unrelated or unexplained work, stop and request
coordinator allocation. Do not stop, restart, migrate or delete another project's
containers. No global Docker stop/prune/down operations. Bind test PostgreSQL to
loopback; production databases must not be publicly exposed.

Use a new empty E-only restore target distinct from the source database, with its
allocation recorded before creating it. Do not infer a database name from the
reserved port. No shared C/AB/D test database. Never substitute SQLite for
PostgreSQL transactions, leases, locks or concurrency acceptance.

Local/test/production configuration and recipient lists must be distinct. Sending
defaults to dry-run; repeat reminders, SMS and phone are disabled; first-report
policy is unset until recorded. Fixture evidence remains marked through events,
reports, outbox and UI, and must never enter production recipient delivery.

Never discover or read existing credential values. Operators supply newly
authorized credentials using the agreed secret mechanism; retain only reference
names and approval status in public artifacts. Do not place values in shell
arguments, command history, repository files, screenshots, client bundles, model
context or exception reports. Avoid diagnostic commands that expand environment
variables or print fully rendered connection strings/configuration. Do not add
persistent Git proxy settings; any approved proxy use is process-scoped.

## External gate register

Current status for every row is **NOT EXECUTED / BLOCKED_EXTERNAL**. The coordinator
owns the authoritative status in `V01-TODO.md`; this runbook is not another task
board. Record approval references privately and publish only redacted conclusions.

| Gate | Required evidence before execution | Acceptance observation |
| --- | --- | --- |
| Source authorization | Actual publisher/provider, exact approved API/docs, license/trial scope, retention/redistribution rights, quota, polling and retry limits, owner and expiry | Read-only authorized requests; record time fields, paging/revision/late-record behavior and errors |
| Business and recipients | Actual products/regions/suppliers/events, recipient whitelist, roles, maintenance contact, first-report and correction policy | Server rejects missing policy or unauthorized recipients; no assumed region or industry threshold |
| Quotes/background | Authorized CSV/XLSX sample, owner permission, mapping, comparison basis; official series/period definitions | Preview errors/duplicates safely; no formulas/macros; deterministically reconcile metrics to source revisions |
| Feishu tenant and identity | Approved app/tenant, permissions, test actors, callback and SSO configuration; credential reference only | Current SDK/doc-aligned verifier and identity binding; platform acceptance distinct from human acknowledgement |
| Costs and retention | Approved amounts/request and token caps, alert contacts, retained fields/periods and deletion ownership | Count failed requests/retries, block hard cap without auto-purchase, keep maintenance warning available |
| Deployment and recovery | Approved host, HTTPS ingress, minimal-permission runtime, storage/backup ownership, external probe host and outage window | Fresh deployment, restore and compatible rollback actually exercised |
| Phones | Approved devices/accounts and explicit test-message scope/consent | State matrix below with observed display and verified acknowledgement |
| Live source comparison | Approved reference feed/list and comparison rights, clock synchronization and metric definitions | At least seven days of comparison including gaps/failures |
| Trial operation | Stable candidate, agreed scope/service expectations, actual operator and feedback process | At least fourteen natural days, incident and data-gap review |

Inspect the actual approved provider documentation before implementation; the
scenario error codes and limits are fictional. Do not guess commercial endpoints
or bypass access controls. A public page or SDK documentation is not license or
account authorization. If access expires, stop that capability, preserve its last
checkpoint and show monitoring degradation. Report quotes as offers unless actual
authorized transaction evidence establishes otherwise.

## Feishu acceptance and identity procedure

1. Freeze the actual SDK/version, current message and callback documentation,
   tenant/app, required permissions, callback response deadline and identity
   mapping. The implemented protocol and official source references are recorded
   in [D's references](../src/oil_agent/channels/REFERENCES.md); reverify against
   the approved tenant before external acceptance. Local signature tests alone
   do not establish the tenant, permissions or actual provider callback deadline.
2. Configure an approved test recipient only. Use a clearly marked synthetic card
   and associate the source record, event/revision, recipient, notification intent,
   delivery and platform message identifiers. Keep the mapping private/redacted.
3. Verify raw callback authenticity, freshness/replay handling, required decryption
   and tenant/app identity according to the frozen protocol. Verify that the actor
   is the intended, still-authorized recipient for the delivery and event revision.
   A body-supplied actor alone is not authenticated identity.
4. Execute T17/T18 negative variants: forged/stale body, replay, wrong actor,
   forwarded card/link, wrong revision and revoked authorization. Repeat a valid
   callback to prove idempotency. An old revision's acknowledgement cannot suppress
   a correction/new severe revision or another recipient's reminders.
5. Exercise server-side SSO/session access for all five mobile views. Anonymous,
   viewer-as-admin, forwarded link, logout and revoked sessions must be denied at
   API level. Credential values are never a readable admin API response.
6. Record API acceptance, phone display and verified user acknowledgement as three
   observations. Preserve UNKNOWN after a post-request disconnect; do not call it
   success or blindly resend. Query/retry only with verified platform rules and
   a bounded policy; otherwise route to maintenance reconciliation.

## Phone matrix (T24 and D-04)

For each approved iOS/Android device record model, OS, Feishu version, account
alias/role, notification settings, network, clock offset, candidate commit and UTC
test time. Device labels below are slots, not evidence that phones are available.
Run all states on each available device; mark missing devices NOT EXECUTED.

| State | Action | Required observation |
| --- | --- | --- |
| Foreground | Open app and send one approved test card | Visible card time and authenticated acknowledgement |
| Locked | Lock screen before test send | Whether/when notification appears; no display is a recorded result |
| Background | Background Feishu before test send | System notification and later in-app display separately |
| Do not disturb | Enable DND and record settings | Actual muted/delayed/visible behavior; never promise bypass |
| Offline then reconnect | Disconnect before send, then restore network | Acceptance, reconnection, display and ack times separately |
| Account logged out | Log out before test send | No authenticated read/ack while logged out; observe behavior after approved login |

Use columns: `case_id/variant`, device alias, expected, actual,
`platform_accepted_at`, `network_restore_at`, `phone_displayed_at`, `ack_at`, actor
alias, revision, evidence reference, tested commit and status. Unknown/unobserved
times stay null; never substitute API time for phone time. Cropped screenshots
must exclude personal messages, identities, credentials and unrelated apps. Obtain
consent and keep originals private. Report mobile view readability, evidence links,
empty/stale/error states and role restrictions as separate observations.

## At least seven days of live source comparison

Start only after source authorization and the reference denominator are defined.
Record UTC start/end, actual elapsed duration and gaps; require at least seven
days (168 hours). The interval may overlap the fourteen-day trial. Historical
replay is separate and must use material available at the historical instant.

For each reference item retain an authorized stable identifier/revision, original
publisher, publication time, provider-available time if supplied, discovered time,
durable-receive time, platform-acceptance time and case disposition. Do not invent
missing times. Group reprints by original publisher before counting independent
evidence. Audit all missing/late items and source error periods, including quiet
days, weekends/market closures and pagination truncation.

Calculate and label separate intervals:

- External discovery: `discovered_at - published_at`; provider delay separately
  when available. Report per-source P50/P95/max and sample/unknown counts.
- Internal path: `platform_accepted_at - durable_record_received_at`, including
  queue time. The plan proposes P95 <= 60 seconds at 10 new records/minute; record
  the accepted test load and whether actual evidence meets that target.
- User touch: acceptance to observed phone display, then display to authenticated
  acknowledgement. Report unobserved/failed outcomes, not an invented latency.

Use an explicitly documented percentile method (for example nearest rank over
sorted completed samples). Always report the total eligible count alongside
completed, failed, timed-out, UNKNOWN and missing-timestamp counts; a percentile
of successful samples alone cannot pass the gate. Report each deadline miss or
unresolved record separately. A negative interval triggers clock/data review,
not silent clipping. Count source requests, paging/retries and model usage/cost.

Compare recall/false positives only against the agreed authorized reference set,
with numerator, denominator and reviewer disposition. No claim of global coverage
or zero missed major events follows from a quiet week or a small fixed corpus.

## At least fourteen days of operation

Require at least fourteen natural days (336 elapsed hours) of recorded operation.
Log daily candidate commit/image/migration versions, component heartbeats, source
gaps/errors, checkpoint lag, queue/outbox states, budget consumption, daily report
cutoffs, backup outcomes and operator/customer feedback. Include ordinary days
without major events and add labeled historical replay if needed; replay does not
replace the elapsed-time requirement.

Keep outage and maintenance windows visible. Do not compress a fourteen-day clock
into a replay or silently exclude downtime. Coordinator acceptance must explicitly
decide whether a material fix invalidates/restarts an affected observation window.
Failure or incomplete evidence remains open. A single-host service does not claim
high availability, and automatic all-day operation is not a promise of all-day
human support. Record the actual maintenance agreement.

## Safe backup, restore and rollback (T25)

The implemented `scripts/backup.sh` and `scripts/restore-isolated.sh` use official
PostgreSQL tools in the exact E PostgreSQL container. Both verify Compose project
and service labels. Backup requires an absolute new filename, creates it exclusively
with private permissions and checks the custom archive listing. Restore requires a
trusted regular archive and a **new** `oil_e_restore_` database; `createdb` refuses
an existing target. Restore uses one transaction, no owner/ACL restoration and no
clean/drop operation. Failed output/targets are retained for inspection.

Pass the chosen absolute archive path to `sh scripts/backup.sh`; pass that same path
and the new database name to `sh scripts/restore-isolated.sh`. Inject the E Compose
environment first, as for startup. Do not put dump files in Git or public artifacts.
On this Windows rehearsal, Git Bash preserves binary dump streams; PowerShell text
pipelines are not used for archive data. These scripts are scoped to E and are not
authorized production backup automation.

The local rehearsal restored one source record, two immutable versions and one
acknowledgement, matching the source snapshot. A synthetic expired in-flight lease
inserted only in the restored database became UNKNOWN under the actual recovery
CLI; three other dry-runs remained dry-run. Repeated backup/restore against the same
targets failed safely. Measured RPO/RTO, real off-host backup storage and an actual
production rollback remain NOT EXECUTED.

1. Inventory the exact approved E source database and new empty restore database,
   application commit/image, PostgreSQL version, schema migration revision and
   state counts. Keep connection credentials out of the record. Pause test sending
   and ensure restored services cannot reach live recipient endpoints.
2. Select version-compatible PostgreSQL backup tools and a consistent database
   snapshot covering records, checkpoints, pending work, event revisions, outbox,
   recipient authorization/acks, cooldown, report uniqueness and audit state.
   Preserve necessary application/configuration references separately. Do not copy
   existing secret values; arrange secret reprovisioning through its owner.
3. Back up to the approved restricted, encrypted location; record UTC start/end,
   success/failure, size and retention disposition. Production policy should define
   daily backups and periodic restore rehearsals. Retention follows licensing and
   customer agreement; no public dump upload or unapproved deletion.
4. Verify the target is empty and belongs to E before restoring. Restore into that
   target, never over an existing unexplained database or volume. Reconcile counts
   and key records, migration revision and constraints; run the T25 fixture seed
   checks against real PostgreSQL. A readable dump alone is not a restore PASS.
5. Start the compatible test application with dry-run enforced. Recover pending
   records/intents; verify acknowledged/accepted deliveries do not repeat and
   UNKNOWN deliveries remain held for reconciliation. Preserve per-recipient and
   per-revision authorization, report date/timezone uniqueness and source cursors.
6. Record measured data-loss window (RPO) and recovery duration (RTO), actual
   commands/tool versions and outcomes. No target value is implied by this runbook.
7. Before a release, record current and previous known-good image/commit/schema
   revisions. For rollback, first pause affected market sending while keeping
   maintenance alarms and safe audit/ingestion available. Check previous app/schema
   compatibility in the isolated restore target before a switch. Prefer a tested
   forward fix or restore path for incompatible migrations; do not blindly run a
   destructive downgrade. Any production restore/switch requires its actual
   approved scope. Reconcile items created after the backup to avoid data loss or
   duplicate sends; do not resend UNKNOWN as if it were PENDING.

## Monitoring, incident handling and evidence redaction (T26)

Monitor API, ingestion, urgent/normal workers and sender independently, with valid
heartbeat age and work progress, not just process existence. At least one approved
probe must run off-host. Exercise worker termination and host loss only in the
approved window; confirm maintenance notification with observed timestamps.
Local polling cannot establish off-host detection. Market-send pause must not
disable maintenance alerts. Never affect unrelated host services/containers.

If severe false information is detected, pause affected market sends, preserve
records and audit history, investigate, then issue an authorized versioned
correction to the still-authorized original recipients. Keep source degradation,
outbox UNKNOWN and budget stops explicit. Do not discard evidence to clear alerts.

Use T26's synthetic non-secret canary to test application logging redaction across
Authorization/Cookie headers, URL parameters, nested exceptions and exported
reports. Execute these checks only against generated test output; this is not
permission to search the machine for credentials. Structured allowlisted logs
should retain useful opaque object IDs/status/times while omitting request bodies,
connection strings, token values and customer/publisher content outside its rights.
Review the exact public diff and intended artifact list before publication.

If a suspected real secret appears unexpectedly, stop output/export, retain only a
redacted location reference, notify the coordinator, and let its owner handle
revocation/rotation. Do not print, copy, probe or validate the suspected value.

Every acceptance record needs case/variant, input/evidence reference, expectation,
actual result, exact executed command, tested commit, environment/tool versions,
UTC interval, status and limitations. Keep raw sensitive evidence in approved
private storage; public records contain redacted references. Separate deterministic
synthetic, PostgreSQL integration, platform-accepted, real-phone and longitudinal
results. Never backfill PASS or timestamps for skipped/blocked work.

The deployment uses official [uv Docker guidance](https://docs.astral.sh/uv/guides/integration/docker/),
[Compose startup dependencies](https://docs.docker.com/compose/how-tos/startup-order/),
[PostgreSQL dump](https://www.postgresql.org/docs/16/app-pgdump.html) and
[restore](https://www.postgresql.org/docs/16/app-pgrestore.html) tooling. Base images
are pinned to the digests actually built in this rehearsal. Dependency locks and
image digests improve reproducibility; they do not establish production safety.
