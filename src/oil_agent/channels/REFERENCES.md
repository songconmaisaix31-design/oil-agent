# Feishu adapter verification

Official documentation and SDK source checked on 2026-09-12. These references
describe the implemented protocol; all executable acceptance evidence uses mocks.

- [Send message](https://open.feishu.cn/document/server-docs/im-v1/message/create):
  application bot, POST `/open-apis/im/v1/messages`, `receive_id_type=open_id`,
  serialized content, explicit response message ID. `uuid` deduplicates for only
  one hour and is limited to 50 characters. Durable idempotency remains C's job.
- [Common errors](https://open.feishu.cn/document/server-docs/api-call-guide/generic-error-code):
  99991400 / 230020 frequency limits; 99991403 monthly quota; 99991663/65 token
  invalid/expired; 99991672 missing scope. These categories are not interchangeable.
- [Internal tenant token](https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal):
  server-only app credential exchange, provider expiry with an early cache cutoff.
- [Current card callback](https://open.feishu.cn/document/feishu-cards/card-callback-communication):
  schema 2.0, `card.action.trigger`, header create_time in microseconds, operator
  tenant/open ID, context message ID. C must respond within three seconds after
  verification and necessary durable work; D's async verification is capped at two.
- [Button component](https://open.feishu.cn/document/feishu-cards/card-components/interactive-components/button):
  current `behaviors` callback/open_url interactions, plain-text card content.
- [OAuth v3](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/authentication-management/access-token/get-user-access-token-v3):
  POST `https://accounts.feishu.cn/oauth/v3/token`, form encoding and confidential
  client secret. The v2 page explicitly marks v2 historical. No public-client or
  PKCE flow is claimed; C owns one-time browser-bound state before this exchange.
- [Authorization code](https://open.feishu.cn/document/authentication-management/access-token/obtain-oauth-code):
  accounts.feishu.cn authorization page, registered redirect, response_type=code.
- [User information](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/authen-v1/user_info/get):
  v1 user_info resolves tenant_key/open_id from the server-only bearer token.

The official Python SDK HEAD was resolved through git ls-remote as
`0b9e6e48b74bb4b34462fc67b7e738b27e73e697`. Inspected pinned files:

- [Event dispatcher](https://github.com/larksuite/oapi-sdk-python/blob/0b9e6e48b74bb4b34462fc67b7e738b27e73e697/lark_oapi/event/dispatcher_handler.py):
  SHA-256 over timestamp + nonce + encrypt key + exact raw body.
- [Decryptor](https://github.com/larksuite/oapi-sdk-python/blob/0b9e6e48b74bb4b34462fc67b7e738b27e73e697/lark_oapi/core/utils/decryptor.py):
  SHA-256 key derivation, base64 IV+ciphertext, AES-CBC and strict PKCS7 unpadding.
- [Card action model](https://github.com/larksuite/oapi-sdk-python/blob/0b9e6e48b74bb4b34462fc67b7e738b27e73e697/lark_oapi/event/callback/model/p2_card_action_trigger.py):
  modern operator/action/context shape.

The local implementation uses existing cryptography/httpx dependencies and adds
constant-time comparison, freshness/size limits, duplicate-key rejection, strict
tenant/application checks and required server identity/message predicates. It does
not use the SDK's logging dispatcher, which can print callback bodies and headers.
No private application credential, actual tenant data or real callback was used.

## Integration entrypoints

`oil_agent.channels` exports `DryRunChannel`, `FeishuSettings`, `FeishuRecipient`,
`FeishuChannel`, `FeishuAckVerifier`, `FeishuIdentityAdapter`.

- `DryRunChannel().send(intent, *, context) -> Delivery` requires channel=dry_run.
- `FeishuChannel(settings, *, recipients, authorize, public_base_url, transport=None)`
  requires server-owned recipient->FeishuRecipient mappings and async
  `authorize(RecipientAuthorization)->bool`. No current grants means no HTTP send.
- `FeishuAckVerifier(settings, *, identity_resolver, delivery_matches)` requires
  async `identity_resolver(ExternalIdentity)->tuple[actor_id,recipient_id]` and
  async `delivery_matches(delivery_id,platform_message_id)->bool`. Wire C's
  `Runtime.resolve_identity` and `Runtime.verify_delivery_message` respectively.
- `await verifier.challenge(payload, *, context) -> str|None` handles encrypted URL
  verification; None means the route MUST call verify before any acknowledgement.
- `await verifier.verify(payload, *, context) -> VerifiedAck` establishes signature,
  identity and message binding. C must still check recipient, revision, current
  permissions and replay atomically; verifier success alone never records an ack.
- `FeishuIdentityAdapter(settings)` implements the shared IdentityAdapter. Wire C's
  challenge/session routes; only preprovisioned active identities may get a session.

Settings accept explicit SecretStr injection, never discover environment/files.
Outbound is disabled by default. No real app login, message send, phone receipt,
production deployment, live SSO, or PostgreSQL replay/concurrency acceptance is
claimed by this channel suite. Old versions are retained by C; D only creates
new messages and returns callback acknowledgement without card replacement.
