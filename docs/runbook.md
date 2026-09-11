# Oil Agent verification and operations runbook

This is the E-BASELINE runbook, based on the supplied development plan v1.0 and
`V01-TODO.md`. It records procedures and unmet gates, not deployment acceptance.
The baseline `f5d5face60c160e70a7565498a6da54ed33c15fd` has no application or Compose
entry point. C's evolving worktree was inspected read-only; its later foundation
commit `558010bee164f2161a0928384eb6aac36e001c07` is not integrated in this E
checkout. Do not infer an available E command from that work in progress. Only
the corpus checker below is implemented in this increment.

No deployment, account login, commercial-source request, paid product model call
or customer message is authorized by this document. Ordinary local development,
tests, commits and pushes to the existing origin are already authorized.

## Available checks and pending commands

Run from this checkout using Python 3.13, with no dependency installation:

```powershell
python --version
python -B scripts/validate_scenario_corpus.py
git diff --check
```

The checker reads [fixed synthetic scenarios](../fixtures/scenarios/v01.json)
and performs consistency checks only. Its PASS is not a T01-T28 application PASS.
See [baseline checks](../e2e/baseline-checks.md) for actual evidence.

| Action | Command availability | Gate |
| --- | --- | --- |
| Corpus consistency | Implemented above | Local, no network or services |
| Contract/unit/integration suite | PENDING: C dependency lock and AB/C/D implementation | Record actual test selectors after integration |
| Browser tests and Vite build | PENDING: D app/package scripts | Exercise real API, not screenshots of fixture pages alone |
| PostgreSQL migration/worker startup | PENDING: C schema and CLI | Fresh E-only database and process boundaries |
| Compose build/up/health | PENDING: E follow-up after app entry points exist | Inspect actual Compose service names and locked images first |
| Backup/restore/schema inspection | PENDING: pinned PostgreSQL tools and schema | Rehearse against empty E-only target |
| API health probe and application rollback | PENDING: actual endpoints/version compatibility | Off-host probe and approved outage window |

Do not paste guessed module, service, route or migration commands into automation.
Replace a pending entry only after the command exists and has been exercised.

## Isolation and secrets

E's reserved future PostgreSQL host port is `55434` and Compose project name is
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
   mapping. These protocol details are pending D/C implementation; do not assert
   invented field names, signature algorithms or timeouts.
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

The following is a pending rehearsal procedure; no database commands are supplied
until C's migration/application interfaces and E's Compose services exist.

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
