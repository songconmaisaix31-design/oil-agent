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

## D-FIX-UPLOAD follow-up

Accepted starting SHA: `38a065e1a3f71631e4a8af915069982fe02303e6`.
Repair code SHA: `b35e5a3945157a0c74a4f06410b822dd06c6bef8`, pushed to the same branch.

The upload UI and both client size guards now use exactly **2,000,000 raw bytes
(2 MB decimal)**. The previous 5 MiB allowance disagreed with AB/C validation.
File type checks and field mappings are preserved; no server limits, DTOs,
dependencies or other producer files were changed. E's `3m` gateway request limit
allows JSON/base64 overhead and does not increase the raw file allowance.

Two UI regressions exercise actual FileReader/request behavior: 2,000,000 bytes
reach `POST /api/v1/quotes/preview` with the full decoded length, whereas 2,000,001
bytes display the size error with no file read and no API call. The oversized
regression failed on the original implementation before the fix.

Follow-up checks from `web/`: `npm test` **13 passed**; `npm run typecheck`,
`npm run build` (including `generate:check`) and `npm run format:check` passed.
`git diff --check` passed. Only `web/src/quotes.tsx`, `web/src/test/app.test.tsx`,
`web/README.md` and `web/HANDOFF.md` are in this repair's write scope.
No development/browser service was restarted. These mocked UI boundary checks
do not claim successful server parsing or replace E/I's final integration tests.

## Initial D checks and evidence

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
C delivered authoritative Chinese notification-body formatting in
`ad19dce62819273765d67897d0fcfd392e17887b`; the prior body-content request is now
producer-delivered, pending final integration. That producer commit was not merged
or tested end-to-end in this bounded upload repair. The neutral first-report
header avoids inferring urgency from notification kind alone, and unavailable
source times must remain explicit rather than invented.

Real SSO and phone tests (forwarded links, logout, revoked permissions, background,
lock screen, DND and offline behavior) remain **BLOCKED_EXTERNAL**. No account
login, secret discovery, production deployment, paid calls, commercial-source calls
or customer message was performed. Bootstrap/reverse-proxy wiring, durable replay,
recipient/version enforcement and full PostgreSQL integration remain C/E/I work.
Coordinator reports C/E's T04 late historical evidence test still failing at the
adopted snapshot; D did not run or claim this cross-track test as passing.
