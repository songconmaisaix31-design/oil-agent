# Feishu trial construction and evidence procedure

This is a preparation procedure, not approval to call Feishu. The accepted
`ed1de2e24634e8471e0979cfc168eebec4c12e4c` baseline is local fixture/dry-run only.
R3 code `cfda44473a0c260b51f9762624166a6b419a6ce0` reuses the existing adapters.
No source, model, Feishu login/token/message API call or paid product usage was
made during this increment. Public documentation and Git operations are separate.

## Minimal operator inputs

Supply nonsecret values and approval references through the project configuration
owned by C/I. Supply secret values only through the operator's explicit project
process/secret injection; never chat, Git, command arguments, screenshots or logs.
No credential discovery, automatic dotenv load, wildcard recipient or fallback
identity is supported by D.

| Input | Exact scope/use |
| --- | --- |
| Feishu tenant key and application ID | One approved tenant/application bot; same application for send, OAuth and callback |
| Application secret | `FeishuSettings.app_secret: SecretStr`; server-only token exchange |
| Encryption key and verification token | `encrypt_key: SecretStr` and `verification_token: SecretStr`; callback verification for the same app |
| Registered HTTPS redirect URI | `redirect_uri`, exact including path/trailing slash; serves the web application, not a GET to the JSON session API |
| Public HTTPS application origin/base | `public_base_url` for card detail links, same-origin web/API routing and C's public origin; no query/fragment/userinfo |
| Registered card callback URL | Public origin plus `/api/v1/callbacks/ack`, preserving exact raw request bytes and Feishu signature headers |
| Exact test recipient map | Local recipient ID -> `FeishuRecipient(open_id, is_test_recipient=True)`; explicit `ou_...` for this app, no group/email/wildcard expansion |
| Exact identity bindings | C approval lists actor ID, recipient ID, role, provider `feishu`, and subject `tenant_key:app_id:open_id`; only preprovisioned active identities |
| Time-limited approval and budget | C's authoritative identity/trial-send permissions, expiry, exact recipient scope and bounded send count; unapproved or expired permissions fail closed |
| Exercise authorization, if requested | Explicit fixture dataset and exercise scope, separate from real trial source/model permissions; ordinary reports are separately denied by default |
| Test phone and operator availability | Named approved operator independently observes receipt and performs login/ack; never infer phone receipt from HTTP 200 |

App permissions must cover the documented application-bot message API and the
user-info fields actually needed (tenant/open ID). Do not request phone/email or
directory scopes merely to authenticate. Resolve app availability/bot installation
and public URL ownership before enabling the trial; this document does not grant
new platform permissions. See [official references](REFERENCES.md).

## Construction API for I

All existing constructor signatures and `FeishuSettings` fields are unchanged.
Settings has `enabled=False` by default, plus `app_id`, `tenant_key`, the three
server-only secret fields and `redirect_uri`. Recipient mappings are a copied
server-owned snapshot. C/I must match that snapshot to the exact active approval;
do not infer permission from a configured app or a syntactically valid open ID.

Within I's approved factory, after creating the existing `runtime` and explicitly
injected `feishu_settings`, `approved_recipients` and `public_base_url`:

```python
from oil_agent.channels import (
    FeishuAckVerifier,
    FeishuChannel,
    FeishuIdentityAdapter,
    feishu_identity,
)

runtime.services.identity = FeishuIdentityAdapter(feishu_settings)
runtime.services.ack_verifier = FeishuAckVerifier(
    feishu_settings,
    identity_resolver=runtime.resolve_identity,
    delivery_matches=runtime.verify_delivery_message,
)
runtime.services.channels["feishu"] = FeishuChannel(
    feishu_settings,
    recipients=approved_recipients,
    authorize=runtime.authorize_recipient,
    public_base_url=public_base_url,
)
```

This code constructs adapters only; it does not provision users or perform HTTP.
`feishu_identity(feishu_settings, approved_open_id)` returns the exact
`ExternalIdentity` for C's provisioning process. OAuth and callbacks use this same
helper. **No legacy `tenant:open_id` fallback or automatic migration exists.**
C/E must deliberately regenerate their synthetic identity fixtures separately.

Do not add a second delivery loop: use Runtime's durable outbox, preallocated
delivery row and current recipient/revision authorization. The channel checks
authorization before token acquisition and again immediately before send. Both
the map and intent must mark trial/fixture recipients as test recipients. C owns
approval expiry/budget, real urgent-event eligibility, exercise eligibility,
report restrictions and replay-safe acknowledgement transactions.

## Executable checks without credentials

From the existing worktree root:

```powershell
uv run --locked pytest tests/unit/channels tests/contracts -q
uv run --locked ruff check src/oil_agent/channels tests/unit/channels
uv run --locked ruff format --check src/oil_agent/channels tests/unit/channels
```

From `web/`:

```powershell
npm test
npm run typecheck
npm run build
npm run format:check
```

These tests inject `httpx.MockTransport`/browser fetch doubles and synthetic
identities. They do not contact Feishu or establish trial readiness. R3 results:
98 Python tests (70 channel + 28 contract), 18 web tests, all checks above passed.
No development/browser/Compose service was started for R3's first increment.

## Authorized live procedure (not executed)

1. I integrates C's approved permission/configuration implementation and this D
   increment; E verifies that exact candidate. Use C/I's supplied provisioning
   and factory commands after their handoff, never a replacement script or raw
   SQL to create authenticated sessions. Until these are integrated, classify
   missing assembly as implementation work, separately from missing user inputs.
2. Configure only the approved project instance with the table above. Keep
   production sending disabled; initially keep trial sending disabled too.
   Provision exactly the approved C identities (no sessions). Confirm permission
   expiry/budget and registered HTTPS routes. Do not log provider request bodies,
   OAuth query strings, Authorization/Cookie headers or callback payloads.
3. Verify the encrypted Feishu URL challenge through the configured callback
   route. A challenge response creates no acknowledgement. Normal callbacks must
   pass raw-body signature, timestamp, app/tenant/token, operator identity and
   persisted message ID checks before C's recipient/revision/replay transaction.
4. On the approved phone, open the public application and choose Feishu login.
   Browser GET `/api/v1/session/challenge` obtains C's one-time browser-bound state;
   provider returns to the registered web URI; the web clears code/state from the
   address before POST `/api/v1/session`. C exchanges the code, resolves only the
   approved identity, sets an HttpOnly Secure session and supplies a CSRF token
   held only in memory. Denial/ambiguous parameters require a new login. Verify
   the expected recipient/role and logout/session revocation through actual C API
   checks; do not export cookies, OAuth codes, tokens or browser storage.
5. Run the approved real **non-urgent** source/model chain under C/AB budgets with
   provenance `trial`. Verify stored records and **zero notification intents and
   zero sends** for that case. An empty home page alone is insufficient evidence.
6. Only if a separate urgent exercise is approved, enable the exact trial send
   allowance and approved fixture dataset. Use the integrated pipeline to create
   its versioned intent/outbox. The card header and body must say
   `合成演练 · 非真实事件` and preserve the dataset label. A real urgent trial event
   instead says `试运行 · 真实来源`; never relabel fixture content as real evidence.
7. Record the durable intent/delivery/version IDs and redacted platform message
   identity after one bounded send. `ACCEPTED` proves only Feishu API acceptance.
   The designated operator separately observes the card on the phone, checks its
   label/source/time/evidence and uses `确认本版本`. Verify a single durable ack
   bound to that message, approved actor/recipient and revision. Retain old cards
   and versions; test a later revision separately without overwriting history.
8. E verifies forged/stale/other-app/other-recipient/wrong-message/replayed events
   are refused or idempotent at the actual API, with no cross-recipient ack. Test
   expiry, revocation and wrong-CSRF against C's API; a local verifier pass alone
   cannot prove those database/session guarantees.
9. If a send loses its response, record `UNKNOWN`, stop and reconcile using
   authorized platform evidence; do not rerun the job blindly. Provider UUID
   deduplication lasts only one hour and cannot replace durable reconciliation.
   If OAuth response is lost, start a new challenge (never replay the code).
10. Close the trial allowance, record approved versus actual usage and restore
    dry-run defaults using C/I's controls. Report phone receipt and real login
    separately from API acceptance; redact screenshots and identifiers before
    any public artifact. Unknown actual cost stays unknown, never guessed zero.

## Remaining gate classification

- Implementation pending integration: C permission/provisioning/status changes,
  I factory injection and D regeneration from C's authoritative updated OpenAPI.
- Missing authorization: approved app/tenant/recipient/public URLs/project secret
  injection, source/model rules/budget and the optional distinct exercise scope.
- Implemented awaiting real test: Feishu HTTP acceptance, OAuth login, signed
  callbacks and actual phone receipt/ack; no external evidence exists yet.
