# One-way personal alert channel

`FeishuChannel(..., personal_alert_only=True)` renders trial event/report content
as a closed, one-way card and sends it through the existing application-bot
transport. It carries no OAuth, login, callback, action buttons, or links.

## Accepted content

- `subject_type="event"` with `first_report`, `update`, `correction`,
  `withdrawal`, or `reminder` kinds (urgent alerts).
- `subject_type="report"` with `daily_report` kind (the dated daily report).

Every intent must be trial provenance (`provenance="trial"`, not fixture or
production) with an exact test recipient grant. Status and exercise subjects are
rejected; they remain the `trial_status_only` and `c1_display_only` modes.

## Card

The renderer imports the shared `LABELS`/`PROVENANCE_LABELS` and shows the
factual trial label (`试运行 · 真实来源`), the kind label and color, the title,
body, cited evidence and the actual Shanghai generation time. A fixed disclaimer
states platform acceptance is not phone receipt and the message is a trial
reminder, not trading advice. Cards set `enable_forward=false` and contain only
`div` elements; no `actions`, `behaviors`, `url`, `callback`, or `open_url`.

Oversized cards fall back to a link-free plain-text message whose title, trial
label and disclaimer always survive; only the variable-length body is bounded.

## C/I handoff

- Configure exactly one `FeishuRecipient(..., is_test_recipient=True)` and inject
  the existing `authorize`, `authorize_request` and `observe_request` callbacks.
  Both request callbacks are mandatory. The mode cannot coexist with
  `c1_display_only` or `trial_status_only`.
- Reuse the shared platform ledger and bounded retries (at most 20 HTTP
  reservations, 3 send attempts). D reserves before each token/send effect and
  preserves the reservation ID through `started`, `responded`, and
  `transport_failure`. A local `started` marker is not remote receipt.
- UNKNOWN outcomes are durable and never blindly retried; platform message ID and
  acceptance time exist only for a complete successful platform response.

## Focused validation

Synthetic identities and mocked HTTP only:

```text
uv run --locked pytest tests/unit/channels/ -q
```
