# C real integration construction contract

This is a construction handoff, not permission to call a provider or production acceptance.
The first increment defines validated settings and committed source history; the
operational increment implements request reservation, session scope and trial gates.
Default settings remain fixture/dry-run with every external enable flag false.

## Settings (C-owned; I injects, never searches credentials)

`Settings.data_provenance` uses existing `Provenance`: `fixture`, `trial`, `production`.
`fixture_dataset` is required only for fixture and must explicitly be `None` otherwise.
Process environment uses `OIL_DATA_PROVENANCE=trial` and `OIL_FIXTURE_DATASET=null`;
Settings parses the literal `null` as None, including CLI/API startup. Permission
objects/tuples use JSON environment values. There is no automatic dotenv loader.
`outbound_mode` accepts `dry_run`, `trial`, `production`; permission to read real sources
or call a model does not turn on sending or establish production acceptance.

Frozen models in `oil_agent.runtime.permissions`:

- `SourcePermission`: common fields below plus source_id, provider, rights_ref,
  credentials_ref. Supply `Settings.source_permissions=(permission, ...)` and
  `external_sources_enabled=True` only for an approved non-fixture source.
- `ModelPermission`: provider, model, credentials_ref, rules_ref and max_tokens.
  Supply `model_permission`, positive daily_model_calls/daily_model_tokens, and
  model_calls_enabled=True. The model identity and approved rules must be explicit.
- `IdentityPermission`: provider=`feishu`, app_id, tenant_key, credentials_ref,
  identities tuple of `ApprovedIdentity(actor_id,recipient_id,subject,role)`.
  Real subject format is exactly `tenant_key:app_id:open_id`, with no fallback alias.
  Enable identity separately; HTTPS and Secure cookies are required for real login.
- `TrialSendPermission`: recipient_ids, rules_ref, first_report_policy,
  allow_reports=False, exercise_dataset=None, exercise_ref=None. Trial recipients
  must be a subset of approved identity recipients. Fixture exercises require both
  an explicit dataset and exercise approval. Trial is not production provenance.

Common fields: approval_id (stable unique authorization ID), authorization_ref,
valid_from/expires_at (aware UTC), budget_ref and positive max_requests. Permissions
contain references to controlled project injection, never secret values. Expiry must
follow start; runtime will recheck validity before every sensitive operation. Reusing
an approval ID with a different scope must not reset its budget.

Actual credentials remain explicit AB/D `SecretStr` constructor inputs. C permission
references do not discover or load them. Test fixtures and permissive model_copy are
not an authorization path for a real deployment.

## AB hook signatures

Implemented source history hook:

```python
await runtime.latest_source_record(source_id: str, external_id: str) -> SourceRecord | None
```

It reads the latest committed immutable source revision and rejects another data
classification/dataset. AB reuses stable record IDs, returns revision candidates and
does not persist cursors; C atomically commits records plus pending work plus checkpoint.

Implemented operational signatures:

```python
await runtime.authorize_source_request(source_id: str, provider: str) -> str
await runtime.authorize_model_request(
    provider: str, model: str, reserved_tokens: int, *, urgent: bool = True
) -> str
await runtime.record_model_usage(
    reservation_id: str, input_tokens: int | None, output_tokens: int | None
) -> None
```

Before each actual provider request, including MCP setup/tool calls, AB invokes the
matching authorization callback. No hidden retries. The return is an opaque durable
request reservation ID. Source may ignore it; model reports usage against that ID.
Both usage values absent means unknown usage, not zero; reservation remains consumed.
An upper bound for input plus output tokens is reserved before the request. C supplies
durable per-approval and daily budgets; callbacks are bound to the approved provider,
source/model and processing lane by I. Provider pricing/cost remains separate evidence.

## D/I unchanged service seams

`FeishuChannel(..., authorize=runtime.authorize_recipient)` receives the existing
RecipientAuthorization. Trial requires an exact current approved test-recipient scope;
D also verifies its server-owned recipient mapping. `FeishuAckVerifier` uses
`identity_resolver=runtime.resolve_identity` and
`delivery_matches=runtime.verify_delivery_message`. C owns authoritative body labels;
D owns card/mobile rendering. No parallel edits to I's bootstrap, CLI factory seam,
environment file or integration handoff are authorized.

The actual Jin10 provider identifier is `jin10` (not a synthetic `jin10_mcp` label).
The source/model hooks reserve each real wire request. IdentityPermission.max_requests
counts bounded OAuth exchanges, and TrialSendPermission.max_requests counts message
send attempts; D owns the bounded subordinate token/message HTTP operations. These
operation counters must not be reported as measured total platform HTTP usage/cost.

Application schema head is `0003_trial`: sessions add authentication_scope; immutable
permission_scopes and provider_calls persist approval budgets and optional usage.
Run C's existing `runtime.cli migrate` explicitly. No queue replacement or new scheduler.
Unknown model usage stays null and retains its reservation; duplicate matching usage
is idempotent, mismatched replay rejects, and reported usage exceeding its reservation
blocks further requests under the same approval. No credential/prompt/provider body
is stored in this ledger. Sources/models are independently permitted; sending still
requires explicit trial or production configuration. Production is not accepted.

`python -m oil_agent.runtime.provision --actor-id APPROVED_ID` validates one exact
approved identity without writing. Add `--apply` only for that approved identity to
create its user mapping, idempotently; conflicts reject without rewrites. It creates
no session and invokes no provider. The old runtime.cli provision-user command rejects
real/trial settings; there is no fixture alias. Real sessions are issued only after
the configured identity adapter and are bound to the current identity approval ID;
null-scope local/test sessions are rejected by real runtime API authorization.

Runtime data scope filters pending claims, source checkpoint reuse, event/report views,
evidence/feedback/ack/import access, report snapshots, outbox claims and recovery.
Mixed retained data is neither relabeled nor silently promoted. A fixture exercise
uses a fixture runtime/dataset plus an explicit trial send grant; bodies say 合成演练.
Trial data bodies say 试运行. Non-urgent trial events create no notification intent;
daily trial reports stay silent unless allow_reports is explicitly approved. Correction
and withdrawal routing still uses original, currently authorized recipients.

OpenAPI is regenerated from C's Python API. BusinessConfig/RuntimeStatus outbound_mode
adds `trial`; RuntimeStatus adds data_provenance, nonsecret permission booleans and
production_accepted=false. D must regenerate its client from that sole schema. Actual
capabilities require I wiring plus E independent verification; permission fields alone
are not proof of provider receipt, source quality, actual usage or production acceptance.

Usage so far: product source requests 0, product model requests/tokens 0, Feishu sends
and login requests 0, paid product cost 0. Missing implementation is distinct from
missing authorization, and implemented code still needs I integration/E verification.

AB's requested dependency is locked as jsonschema 4.26.0 (referencing 0.37.0,
jsonschema-specifications 2025.9.1, rpds-py 2026.6.3). Use Draft202012Validator with
an explicit empty/controlled Registry, reject remote references and bound schema
size/depth before validation. The [official validator API](https://python-jsonschema.readthedocs.io/en/latest/api/jsonschema/protocols/)
documents the explicit registry parameter; AB owns discovered-schema validation.
