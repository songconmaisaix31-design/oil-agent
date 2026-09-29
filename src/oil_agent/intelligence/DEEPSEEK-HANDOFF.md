# Official DeepSeek Responses adaptation

Task `task_e9755428b9dc`, dispatch `ctx_3104af8d5e34`. Base is the clean,
pushed AB `19c9194164eb42f6e16a29c628039118a20aeef4` on
`songconmaisaix31-design/oil-v01-ab`. I `56b49bb` was inspected read-only;
its intelligence code matches this base and its bootstrap accepts OpenAI only.
No checkout, reset, extra worker or cross-owner edit was needed.

## I/C constructor and configuration mapping

| Binding | Exact value / responsibility |
| --- | --- |
| Import | `oil_agent.intelligence.deepseek.DeepSeekSettings`, `DeepSeekResponsesClient` |
| ModelPermission provider | `deepseek` |
| ModelPermission model | `deepseek-flash` (explicitly supplied; no alias rewrite) |
| Endpoint | `https://api.deepseek.com/responses` (`ENDPOINT` constant) |
| Allowed hosts | `("api.deepseek.com",)` only |
| Credential | Explicit project-scoped `SecretStr`, injected by I after C verifies destination; proposed I mapping `OIL_DEEPSEEK_API_KEY` |
| Authorization | Existing `authorization_ref`, `authorize_model_request` callback and exact provider/model permission |
| Accounting | Existing `record_model_usage(reservation_id, input_tokens, output_tokens)` callback |

```python
from oil_agent.ingestion.http import HttpBounds, PinnedHttpClient
from oil_agent.intelligence.deepseek import ENDPOINT, DeepSeekResponsesClient, DeepSeekSettings

client = DeepSeekResponsesClient(
    DeepSeekSettings(
        model=permission.model,
        authorization_ref=permission.authorization_ref,
        api_key=explicit_project_key,  # SecretStr already injected by the owner, never discovery.
        authorized=explicitly_enabled,
        urgent=urgent_lane,
    ),
    http=PinnedHttpClient(HttpBounds(ENDPOINT, ("api.deepseek.com",), request_limit)),
    authorize_model_request=runtime.authorize_model_request,
    record_model_usage=runtime.record_model_usage,
)
```

Construction does not authorize or issue a request. `authorized` defaults false;
`urgent` defaults true; timeout defaults to 20 seconds (maximum 60); output defaults
to 2048 tokens (maximum 8192). Preserve separate lane budgets/clients. C/I own the
initial scope of 10 requests / 100000 reserved tokens relayed by M; do not replace
durable per-permission enforcement with the transport's local request limit.
C reported that the key alone was present and destination fields were empty:
official-versus-gateway confirmation remains necessary before key transmission.
An exact host/model conflict pauses the corresponding integration; this adapter
does not rewrite user configuration, discover a default key, or substitute a model.

## Minimal implementation and preserved behavior

`deepseek.py` binds a subclass to the fixed official endpoint/provider and validates
explicit DeepSeek settings and the returned model identity. `openai.py` reuses the
same bounded request, extraction schema/parser and usage handling with class-level
fixed bindings. Default OpenAI endpoint, request shape and model behavior are
unchanged. A whitespace-only reservation is now rejected before it is assigned as
a durable usage identity, consistently with the existing HTTP authorization gate.

Requests are non-streaming, stateless, `tools=[]`, `tool_choice="none"`, strict
`text.format` extraction, and never contain a prior response/conversation. Existing
input-byte, serialized-request, response-body, output-token and timeout limits
remain in force. The pinned HTTPS transport retains exact Host/SNI validation,
public-address checks, no ambient proxy, no redirects and no automatic retries.
Reasoning output is ignored as evidence; tool/refusal/malformed/duplicate-JSON
output fails validation. The assessment service still validates source references
and conservative rules; this does not generate a morning report from model memory.

Input/output totals include cached/reasoning subtotals; the existing total-token
callback neither subtracts cache hits nor adds reasoning twice. No monetary cost
is inferred (`provider_cost=None`). Known valid usage is retained even when output
validation or model identity fails. Missing/malformed usage or transport failures
retain `(None, None)`, never an invented zero/refund. The usage callback is bounded
and its failure is surfaced; no fallback provider or automatic retry occurs.

## Verification

- Before implementation: `uv run --offline --frozen pytest tests/unit/intelligence/test_openai.py -q --tb=short`
  -> **18 passed**. The new DeepSeek test file then failed collection because the
  adapter module did not exist; this is the implementation gap, not live failure.
- `uv run --offline --frozen pytest tests/unit/intelligence/test_openai.py tests/unit/intelligence/test_deepseek.py tests/unit/intelligence/test_assessment.py -q --tb=short`
  -> **78 passed**, zero failures/skips (18 original OpenAI, 44 DeepSeek and 16
  assessment cases). Original test files/assertions were not edited.
- `uv run --offline --frozen ruff check src/oil_agent/intelligence/openai.py src/oil_agent/intelligence/deepseek.py tests/unit/intelligence/test_deepseek.py`
  -> passed.
- `uv build --offline --out-dir "$env:TEMP/oil-ab-deepseek-ctx-3104af8d5e34"`
  -> wheel and source distribution built using cached declared build dependencies.
- `git diff --check` -> passed. Delivery commit and independently checked full
  remote SHA are in the terminal handoff, avoiding a circular self-commit field.

Synthetic `httpx.MockTransport` exchanges cover exact `/responses` and Host/SNI,
disabled/missing-key/quota/invalid-reservation gates before DNS, no alias/gateway
substitution, cached/reasoning accounting, malformed output, unknown usage,
input/output/time/body limits, and failure/timeout of usage recording. No full
suite, provider call, real source fetch, key/private-file access, Feishu message,
polling or production operation was performed. I owns bootstrap/environment
assembly; C owns destination/permission/usage verification; D owns Feishu. Actual
morning sources, fallback timestamp policy and phone receipt are not accepted by
these local tests. No report/event redesign or daily-analysis code was changed.

## Official sources checked on 2026-09-13 (Asia/Shanghai)

- [DeepSeek V4.1 Flash release](https://deepseek.com/news/deepseek-v4-1-flash/):
  `deepseek-flash` names V4.1 Flash. Deprecated aliases are not substituted here.
- [DeepSeek Responses guide](https://api-docs.deepseek.com/guides/responses_api/):
  official base, Responses compatibility, supported formatting and usage totals.
  Unsupported parameters may be ignored; runtime gates and local validation do
  not depend on those parameters being enforced by the provider.
