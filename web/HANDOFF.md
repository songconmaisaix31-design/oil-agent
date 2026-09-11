# D track handoff — 2026-09-12

## Delivery

Branch: `songconmaisaix31-design/oil-v01-d`

Remote: <https://github.com/songconmaisaix31-design/oil-agent/tree/songconmaisaix31-design/oil-v01-d>

Verified frozen base: `dd01ee225ba36c1d7e75acdf5c96cd2d8e0df482`.
Adopted C's exact authorized dependency commits by ordinary merges, latest runtime
snapshot `ffb62d282c3b65a742f303eeab7a61ade0e28643`; no edits to producer-owned files.

Code increments:

- `e55c62c47f76d1763cf5afbee29f1ee3c91cc9ed`: gated Feishu/dry-run, cards, current
  signed/encrypted callback, confidential OAuth v3 and initial security suite.
- `36dc1b056467db23924b6f7ec2452a9936bd8397`: strict provider responses, malformed
  envelopes, expired tokens, bounded response handling and OAuth failure coverage.
- `4c3040f`: exact registered redirect preservation and neutral first-report label.
- `34eee1915531012b917d702413a21e50354d2841`: generated-contract React/Vite mobile UI,
  five views, frontend tests, browser checks, lockfile and setup instructions.

Changed paths are exclusively `src/oil_agent/channels/`, `tests/unit/channels/`
and `web/`. Generated dependencies and local browser evidence are ignored.

## Checks and evidence

Executed in this D worktree, with no production credentials or customer sends:

| Command                                                                 | Result                                                     |
| ----------------------------------------------------------------------- | ---------------------------------------------------------- |
| `uv sync --locked --group dev`                                          | Pass; root lockfile unchanged                              |
| `uv run ruff check src/oil_agent/channels tests/unit/channels`          | Pass                                                       |
| `uv run ruff format --check src/oil_agent/channels tests/unit/channels` | Pass                                                       |
| `uv run pytest tests/unit/channels tests/contracts -q`                  | 81 passed (53 channel, 28 contract)                        |
| `npm run generate:check` in web                                         | Pass; authoritative C OpenAPI matches generated TypeScript |
| `npm run format:check` in web                                           | Pass                                                       |
| `npm run typecheck` in web                                              | Pass                                                       |
| `npm test` in web                                                       | 11 passed                                                  |
| `npm run build` in web                                                  | Pass; Vite production assets generated                     |
| `npm run browser:check` in web                                          | 6 checks passed, 0 page exceptions                         |
| `git diff --check`                                                      | Pass                                                       |

The browser used an isolated headless installed Chrome and intercepted synthetic
HTTP at only `127.0.0.1:5174`. Checked 390px home/detail and 320px administrator
configuration, no horizontal overflow, fixture labels, rejected ack feedback,
unconfigured login, empty report history and viewer restrictions. Ignored local
evidence: `web/.browser-artifacts/result.json`, `home-390.png`, `event-390.png`.

Orca's browser tab loaded the app, but snapshot/help returned `runtime_unavailable`.
The optional fallback above passed; no Orca restart or authority recovery was
attempted. The temporary Orca tab and headless Chrome were closed.

## C/bootstrap integration

Exact imports, constructor parameters, official protocol references and boundaries
are documented in `src/oil_agent/channels/REFERENCES.md`.

- `DryRunChannel()` implements `send(intent, *, context) -> Delivery`.
- `FeishuChannel(settings, *, recipients, authorize, public_base_url)` implements
  the same protocol; `authorize` must accept `RecipientAuthorization`, not
  `NotificationIntent`. Wire C's `Runtime.authorize_recipient`, available in the
  adopted ffb62d snapshot. No bypass lambda.
- `FeishuAckVerifier(settings, *, identity_resolver, delivery_matches)` requires
  C's `Runtime.resolve_identity` and `Runtime.verify_delivery_message`.
- `await verifier.challenge(payload, *, context)` returns authenticated encrypted
  URL challenge or None. None requires `verify` followed by C's durable recipient,
  revision and replay authorization before returning `{}`. Never replace old cards.
- `FeishuIdentityAdapter(settings)` implements `authorization_url(state)` and
  `authenticate(code, *, context) -> ExternalIdentity("feishu", "tenant:open_id")`.
  C owns the one-time state, user lookup, session cookies and CSRF.
- `FeishuSettings` defaults disabled and accepts explicit server-only SecretStr
  injection. `FeishuRecipient` is an explicit open-ID/test-recipient mapping.

## Remaining limitations and external actions

The channel and web suites use mocked HTTP. They do not establish real Feishu API
acceptance, callback registration, SSO, customer phone receipt or PostgreSQL replay
concurrency. Those require authorized configuration and C/E/I integration.

The current NotificationIntent lacks structured assertion/evidence status,
publisher metadata and source publication times. D labels source record IDs,
exact versions and excerpts, and clearly calls its timestamp notification creation.
C has been asked to populate intent body from authoritative event/report fields
with assertion/evidence labels, publishers, unknowns and report cutoff; never
invent unavailable source times. The neutral first-report header avoids inferring
urgency from notification kind alone.

Real SSO and phone tests (forwarded links, logout, revoked permissions, background,
lock screen, DND and offline behavior) remain **BLOCKED_EXTERNAL**. No account
login, secret discovery, production deployment, paid calls, commercial-source calls
or customer message was performed. Bootstrap/reverse-proxy wiring, durable replay,
recipient/version enforcement and full PostgreSQL integration remain C/E/I work.
Coordinator reports C/E's T04 late historical evidence test still failing at the
adopted snapshot; D did not run or claim this cross-track test as passing.
