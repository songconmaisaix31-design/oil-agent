# Fixed synthetic V01 scenarios

`v01.json` freezes concrete inputs and expected behavior for T01-T28 from the
supplied development plan v1.0, sections 12-13. It contains original fictional
material only. Nothing here is a real market event, customer quote, platform
response, credential or delivery receipt. No external content was fetched.

Run from the repository root with Python 3.13 (standard library only):

```powershell
python -B scripts/validate_scenario_corpus.py
```

The validator checks exact ordered coverage, fixture provenance, safe default
settings, UTC timestamps, decimal strings, input/expectation references and
acceptance classifications. It does not test the application, the truth of an
assertion, a model, network policy, signature verification or a database. A
successful exit means **corpus consistency only**. The frozen corpus retains its
baseline `NOT_EXECUTED` planned-gate labels; actual application executions are in
[runtime checks](../../e2e/runtime-checks.md). Missing references or unsafe defaults
return a nonzero exit.

## Reading the data

- `clock_at` freezes the test's current UTC instant; future/old input timestamps
  are intentional where the case requires them.
- Each input has `is_fixture: true` and a `provenance_ref` to the corpus's original
  synthetic provenance. Nested payload objects inherit that label. A future
  adapter must propagate it to every materialized record, report and intent.
- `kind` and `payload` describe a test stimulus, not a duplicate production DTO.
  E's integration fixtures adapt these values to C's authoritative contracts.
- `input_id#/path` is a JSON Pointer into that input's `payload`, scoped to its
  case. For example, T01 `old#/occurred_at` resolves to the original occurrence
  instant. These are local evidence references, not external URLs to fetch.
- `expectations` are assertions for future tests, never an `actual` result.
- Inline `variants`, `sequence` and `kill_points` are all mandatory subcases.
  Test each failure independently from clean seeded state unless `sequence`
  explicitly defines order. Repeat mutation/restart checks against durable state.
- T11's comparable quote inherits the complete base comparison key and overrides
  value/time. Apply each incompatible override independently. T22 file descriptors
  are instructions for a future temporary test-file builder, not real files.
- T17's signature verdicts are scenario descriptions. They cannot be fed straight
  into a stub and counted as verifier acceptance: generate signed raw envelopes
  with ephemeral test keys and exercise D's real verifier once available.
- Integer load, retry, quota, reminder, freshness and file-size limits are fixture
  values, not approved production configuration. First-report policy remains unset
  globally; T04 has an explicit test-only override.
- Domains ending in `.invalid` and attack URL strings are inert test payloads.
  No validator code evaluates text, runs commands, follows URLs or sends messages.
  T26's canary is deliberately non-secret test text, not a stored credential.

## Acceptance categories

| Category | Intended execution | Evidence scope |
| --- | --- | --- |
| `automated_local` | Deterministic replay/stubs, API/browser checks with actual application code | Runtime report identifies executed subsets |
| `automated_postgresql` | Real PostgreSQL with independent connections, migrations and isolated worker processes | Runtime report; no SQLite substitute |
| `external_manual` | Authorized source/platform, identity, phones or off-host operational observations | NOT_EXECUTED; external gates pending |

Some cases have both automated and external gates. Passing the automated portion
does not pass the external portion. T24 requires real phones; a rendered mock card
cannot satisfy it. T25 needs an actual restore and T26 needs an off-host probe.
The >=7-day comparison and >=14-day operation are additional longitudinal gates
described in [the runbook](../../docs/runbook.md), not accelerated replay tests.

## Future harness and evidence

Preserve this corpus when integrating contracts. A requirement change should
explain the input/expectation delta in its commit and receive coordinator review;
do not delete a failing case or lower a target to get green output. Keep new
historical material separately licensed and labeled with what was available at
the event time; it must not silently replace these synthetic inputs.

For each real execution record `case_id`, variant, corpus/input reference,
expected, actual, status, exact command, tested commit, dependency/DB/browser
versions, environment and UTC time. Keep failure and skipped evidence. Record the
executed result outside this fixture so immutable expectations cannot be confused
with actual outcomes. See [baseline evidence](../../e2e/baseline-checks.md) for this
increment's limited checks and [the runbook](../../docs/runbook.md) for private
operational records and redaction rules.
