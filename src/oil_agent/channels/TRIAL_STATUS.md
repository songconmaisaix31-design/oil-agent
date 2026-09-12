# Bounded personal trial status channel

The agreed C contract is `b67f714154ce9e0cf16b477fb9e3b0ad6e72dbfd`.
`FeishuChannel(..., trial_status_only=True)` accepts only C's `status` intents
with `onboarding` or `morning_status` kinds, revision 1, trial provenance, no
fixture dataset/evidence, an exact recipient grant and C's exact approved copy.
The renderer imports `STATUS_MESSAGE_PAIRS`; it does not define another schema.
Both cards show `试运行状态通知／非实时行情`, only their actual generation time,
and no links, actions, login prompts, market events or model-connectivity claim.

## C/I handoff

- Configure exactly one `FeishuRecipient(..., is_test_recipient=True)` and inject
  the existing `authorize`, `authorize_request` and `observe_request` callbacks.
  Both request callbacks are mandatory for this mode. It cannot coexist with
  `c1_display_only`; ordinary report and C1 behavior remains unchanged.
- C owns the durable `StatusNotification`, matching grant, immutable dated scope,
  due/expiry checks and queue/runner scheduling. This channel has no clock wait,
  task creation or scheduling. The old C1 30-minute permission is not extended.
- I must use its dedicated status assembly without the ordinary trial factory's
  redirect/login/callback requirements. No public URL or callback secrets are
  needed for these fixed cards. Confirmed app/tenant/self injection remains with C.
- Reuse the shared platform ledger for token, tenant lookup and message requests,
  including bounded retries: at most 20 HTTP reservations and 3 send attempts for
  the approved scope. D reserves before every token/send effect and preserves the
  same reservation identifier through `started`, `responded`, or
  `transport_failure` observations. A local `started` marker is not remote receipt;
  a reservation may never start. Do not report these as equivalent counts.
- The existing idempotency UUID includes the product subject, purpose, revision,
  recipient and idempotency key. C must retain each persisted task identity across
  attempts and never create another task/window to bypass UNKNOWN. D does not
  retry internally. Platform message ID and acceptance time exist only for a
  complete successful platform response containing the message ID.

## Actual remaining prerequisites

At dispatch, the app and sole self binding were confirmed and tenant mapping was
unresolved; C owns its current private status. D did not read private configuration
or make live calls. The existing app-only tenant lookup can populate that mapping
through the authorized product entry and shared request ledger. No additional
console permission or availability change was observed as necessary in this task;
report an actual lookup/platform rejection before prescribing such a change.

This fixed nonmarket fallback does not require a model call. The read-only I
baseline `56b49bb4df272d58b4ae3357ede4a5ac09b7dc83` wired OpenAI assessment;
entering a DeepSeek key alone did not wire that provider. Model/source integration
is a separate owner concern and must not become a false claim in these cards.
Punctual execution and app visibility still require the integrated dated runner,
local runtime availability, completed tenant mapping and actual platform acceptance.

## Focused validation

Synthetic identities and mocked HTTP only:

```text
uv run --locked pytest tests/unit/channels/test_trial_status.py tests/unit/channels/test_c1.py tests/unit/channels/test_channels.py tests/unit/runtime/test_status_contract.py -q
```

Coverage includes exact approved copy, no-action mode isolation, mandatory shared
request hooks, sole test-recipient setup, pre-network rejection of tampered intents,
distinct task idempotency, observed token/send ordering, live grant rechecks,
budget denial, UNKNOWN without retry and original C1/ordinary channel assertions.
These checks do not establish actual Feishu counts, platform acceptance, phone
receipt, source/model connectivity or an overnight scheduled execution.
