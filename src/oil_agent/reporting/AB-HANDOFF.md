# AB integration handoff

AB code owns only ingestion, intelligence, reporting and matching unit tests.
Initial frozen base: `dd01ee225ba36c1d7e75acdf5c96cd2d8e0df482`. The coordinator
authorized ordinary adoption of C contracts `e09683409550bbe7238396bc2506def3969ad202`
and `bb39ece229c32131025b4a4ead7d7502ba471e0b`; AB did not edit C-owned files.

## Runtime entrypoints

```python
from oil_agent.ingestion import ReplaySource, SafeQuoteParser
from oil_agent.intelligence import ConservativeAssessmentService
from oil_agent.reporting import SnapshotReportService

sources = {"replay": ReplaySource(records, source_id="replay")}
assessment = ConservativeAssessmentService()
reports = SnapshotReportService()
quote_parser = SafeQuoteParser()
```

These implement frozen `SourceAdapter.fetch`, `AssessmentService.assess`,
`ReportService.build` and `QuoteParser.preview`, each with `context: CallContext`.
Pass them into C's `RuntimeServices`. AB does not store checkpoints, allocate
durable revisions, grant recipient authorization, send messages or deploy.

## Replay, source admission and evidence

`ReplaySource` accepts only explicitly labeled fixture records, preserves arrival
order, revisions and late publication times, and returns bounded pages. The
immutable evidence identity is `(record_id, revision)`: every source/external-ID
family keeps one stable record ID, and that ID cannot alias another family.
Exact duplicate revisions collapse at their first arrival position; conflicting
same-revision content or metadata is rejected. Distinct revisions share one log.
The checkpoint is a **candidate**; C must commit it with all returned records and
pending work atomically. Replaying a committed cursor is deterministic. Input is
append-only; changed consumed prefixes fail. Pagination and retention gaps are
explicit; retention debt remains until C deliberately resets/reconciles coverage.

Importers use `ingestion.common.content_hash(title, excerpt)`: SHA-256 of the UTF-8
compact JSON array `[title, excerpt]`, with `ensure_ascii=False`. An arbitrary
placeholder digest fails validation. Evidence references require exact record ID,
revision, field and literal excerpt. Content hashing checks consistency, not truth.

`SourceSettings` refuses missing license/rights, credentials, authorization,
endpoint/host allowlist or finite request budget. `BoundedHttpReader` requires
injected resolver/transport implementations; no commercial endpoint or socket
transport is bundled. A future authorized transport must enforce the byte limit
while streaming, connect only to the supplied public IPs, preserve TLS hostname
verification and never resolve again. Each redirect is revalidated. Source
attempts, including failures/redirects, consume the finite local counter; C must
persist accounting, backoff and health across processes. Tests use stubs only.

## Safe file preview and offline background

`SafeQuoteParser.preview(QuoteParseRequest, context=...) -> ParsedQuotes` accepts
the final C trusted envelope. The upload contains base64 bytes, filename, MIME,
canonical-field-to-column mapping and rights reference. Publisher, discovered
time and fixture/trial/production provenance come from C's trusted envelope, not
the upload. Output contains records, observations, row issues, duplicate rows and
file hash; C assigns actor-bound preview ID/expiry and owns confirmation/import.

The lower-level `preview_quotes(data, filename, mapping, *, rights_ref,
origin_publisher, discovered_at, is_fixture, provenance, fixture_dataset=None,
limits=None)` exposes `QuotePreview(file_id, file_sha256, columns, rows)`. Rows have
`row_number`, `row_id`, `mapped`, `errors`, `duplicate_of`, `record`, `observation`.
Invalid/duplicate rows contain no importable DTOs. Required mapped fields are
`value` and `as_of`; timezone offsets are mandatory. Optional comparison fields:
product/spec/region/supplier/quote_type/tax_basis/delivery_basis/currency/unit,
plus published_at. Missing basis remains uncomparable. File identity uses original
bytes; row identity includes file, row number and canonical mapping.

An empty mapping uses only exact canonical field names present in the validated
header, retaining every present optional basis field and published_at. It still
requires value and as_of; case variants, synonyms and missing columns are not
guessed. A nonempty explicit mapping is validated as supplied and is never
automatically completed. Equivalent derived/explicit mappings produce identical
file/row identities and evidence; the caller's mapping is not mutated.

Defaults: 2,000,000 raw upload bytes, 10 MB expanded XLSX, 200 ZIP entries, 100x expansion ratio,
10,000 rows, 64 columns and 2,000 characters per cell. UTF-8 CSV and exactly one
XLSX worksheet are supported. Macro/external/entity content, disguised extensions,
bad archives and oversized data reject the file. Formula cells produce row errors;
there is no evaluation. Parsing runs in a bounded worker thread; timeout prevents
return/import but the bounded read-only parse may finish after cancellation.

`parse_eia(data, EiaSeries(...), *, release_at, discovered_at, rights_ref,
is_fixture, provenance, fixture_dataset=None)` is offline. It reads an EIA-v2-shaped
`response.data` array only when series, units and period endpoints match explicit
configuration. No real series or endpoint is guessed. Caller-supplied publication
time stays separate from statistical period; output is US background. Empty data
reports no-new-value, malformed input fails. Changed releases need C-owned source
revision reconciliation before persistence; this parser does not query history.

## Conservative assessment and revisions

The LangGraph has two nodes, no loops/tools/checkpointer, and recursion limit 3,
using the upstream [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api).
LangSmith tracing is explicitly disabled, including when ambient tracing is on.
The tracing helper is already present in the frozen LangGraph dependency tree.
No product model client is bundled or invoked.

An injected client receives only record ID/revision/title/excerpt and a fixed
system instruction. It cannot request tools or alter recipients. Its schema can
return only assertion status plus verbatim evidence. Invalid JSON, unknown IDs,
wrong revisions, unsupported excerpts/numbers, extra fields, excessive output or
timeout degrade to routine unverified candidates. Model output alone never earns
reliable evidence or urgent severity. Plan/denial/archive/future/uncertainty guards
only lower confidence; fallback does not infer occurrence from attack/fire words.
Deterministic tests do not establish general semantic accuracy or live recall.

`ClaimReview` is a trusted application-supplied annotation bound to content hash
and exact evidence. Never construct it from raw model/article fields. Credible
single-source promotion also requires explicit policy and publisher allowlist.
Reviewed matching evidence from distinct original publishers may become independent
multi-source; mirror domains never establish independence.

Default candidate IDs bind source_id/external_id. No matching is inferred from
place names. Constructor `matched_event_ids={(source_id, external_id): event_id}`
accepts only explicit C-reviewed matches. C owns historical matching and monotonic
revision allocation; candidate revision 1 never means an event is new.
`suggest_notification(previous, current, allow_first_report=False)` is advisory
after matching; it has no send authority. Same-origin mirror IDs/timestamps alone
are not material changes; corrections/withdrawals remain suggestions even if
severity falls. C must route changes to the appropriate original recipient scope.

`AssessmentPolicy(model_authorized=True)` and positive `ModelBudget` values are
needed even for an injected stub. Normal/urgent ledgers are separate, finite and
cannot borrow capacity. Attempts reserve tokens before calls, failures retain
reservations, actual usage and blocked attempts are observable. Empty input and
unchanged cached extractions consume no call. Cache is bounded to 128 batches.
C must persist cross-worker/provider reservations; local ledgers are not durable
spending controls. There is no auto-purchase or fallback paid provider.

## Reports and quote thresholds

Reports use only the supplied cutoff snapshot. Late discovery/release/assessment,
uncertain/future times and unsupported references are excluded with gaps. Facts
are labeled source quotations, not copied generated titles/impact numbers. Facts,
watch items and gaps are separate; deterministic impact analysis is empty.

Every observation value and basis field must match its structured source row.
Decimal changes use exact product/spec/region/supplier/quote type/tax/delivery/
currency/unit keys. Missing basis, contradictory same-time quotes or missing prior
quotes yield unknown changes. Shanghai business dates determine freshness; stale
quotes retain value/date but never become today's zero change. US background
retains its statistical period and release, never current domestic inventory.

`QuoteThreshold(comparison_key, Decimal("..."))` configures an explicit absolute
threshold. There are no industry defaults. A threshold hit creates a watch item;
C owns subsequent alert/outbox policy. Mixed fixture/trial provenance propagates
conservatively. Fixture reports carry `SYNTHETIC TEST - NOT MARKET INFORMATION`;
C/D must enforce recipient and delivery isolation.

## Verification and remaining boundaries

Run checks serially on this low-memory host:

```text
uv sync --frozen --group dev
uv run --frozen ruff check src/oil_agent/ingestion src/oil_agent/intelligence src/oil_agent/reporting tests/unit/ingestion tests/unit/intelligence tests/unit/reporting
uv run --frozen pytest tests/unit/ingestion tests/unit/intelligence tests/unit/reporting tests/contracts -q
uv build --out-dir tests/unit/reporting/.build-check
```

Local tests address T01-12, T21-22 and T27-28. E's labeled scenario descriptions
were consulted read-only, not passed as API DTOs. This is not PostgreSQL
transaction/concurrency acceptance, live source coverage, product model accuracy,
recipient authorization, phone receipt or continuous-operation evidence.
External gates: commercial license/credentials/endpoints, actual series/fields,
authorized quote samples, model approval and budgets, deployed-network validation,
phone acceptance and continuous operation. No real data/model requests, customer
sends or deployment occurred.

Initial delivery checks (Windows, CPython 3.13.13, frozen uv environment):

- Scoped Ruff check: passed.
- `uv run --frozen pytest -m 'not postgres' -q`: 85 passed, 3 PostgreSQL tests
  deliberately deselected; one upstream Starlette/AnyIO deprecation warning.
- Earlier AB plus contract check before the two final revision regression cases:
  72 passed. Final non-PostgreSQL run includes all AB and contract tests.
- `uv build --out-dir tests/unit/reporting/.build-check`: wheel and source
  distribution built successfully; temporary build outputs removed after checking.

The PostgreSQL tests were not run in AB: this track starts no extra database or
Docker services and makes no database concurrency/transaction acceptance claim.

## AB-FIX-REPLAY follow-up

Base: `25cceea0bfb78930879060417054e4675d84956d`. E identified that the old
record-ID-only deduplication rejected legal revisions sharing a stable ID.
The correction uses composite evidence identity and enforces both directions of
the source-family/record-ID mapping; cursor format and prefix hashing are unchanged.
Only replay.py, its existing ingestion test file and this handoff were modified.

Two new stable-ID pagination/extension tests failed on the original implementation
before the fix. Regressions now cover one collection with revisions 1 and 2,
page_size=1/max_pages=1, exact-duplicate collapse, repeated fetch, restart from the
original committed cursor, append-only extension after checkpoint creation, exact
old-evidence preservation, consumed-prefix content/rights/order/removal rejection,
and conflicting same-revision payloads and aliases. The earlier pagination test
was corrected to keep its record ID stable across revisions.

Follow-up checks on the unchanged frozen dependency environment:

- `uv run --frozen ruff check src/oil_agent/ingestion/replay.py tests/unit/ingestion/test_ingestion.py`: passed.
- `uv run --frozen pytest tests/unit/ingestion/test_ingestion.py -q`: 25 passed.
- `uv run --frozen pytest -m 'not postgres' -q`: 95 passed, 3 PostgreSQL tests
  deselected, one existing Starlette/AnyIO deprecation warning.
- `uv build --out-dir "$env:TEMP/oil-ab-fix-replay-ctx-e350f1136c55"`: wheel and
  source distribution built successfully outside the repository.

C's ffb62d ingestion code and E's PostgreSQL pipeline tests were read only;
no shared contract or C/D/E/M file changed. Main/E must rerun actual PostgreSQL
T09/T05 against the delivered fix SHA. No Docker, live source/model/API request,
customer send or external acceptance was performed by this follow-up.

## AB-FIX-QUOTE-DEFAULT follow-up

Base: `f3b726d1a194f192f7fc4dc5908882190b416b96`. E's actual browser/API path
submitted the advertised default field_mapping={} and encountered an invalid-input
response before the parser inspected standard headers. Empty-map derivation now
runs only after file/header validation and feeds the existing strict mapping and
row validation. The shared DTO, raw upload cap and production settings are unchanged.

The new CSV and XLSX SafeQuoteParser regressions both failed before the fix.
They now confirm default preview success, all standard basis/release values,
trusted fixture provenance and identical file/row identities versus the same
explicit mapping. Additional cases cover missing/near-match mandatory headers,
unknown optional names, explicit-map validation/non-enrichment, invalid headers,
formula rejection and the unchanged 2,000,000-byte raw limit.

Checks on the frozen local environment:

- `uv run --frozen ruff check src/oil_agent/ingestion/quotes.py tests/unit/ingestion/test_ingestion.py`: passed.
- `uv run --frozen pytest tests/unit/ingestion/test_ingestion.py -q`: 42 passed.
- `uv run --frozen pytest -m 'not postgres' -q`: 112 passed, 3 PostgreSQL tests
  deselected, one existing Starlette/AnyIO deprecation warning.
- `uv build --out-dir "$env:TEMP/oil-ab-fix-quote-default-ctx-10a78cbe3c9a"`: wheel
  and source distribution built successfully outside the repository.

Only quotes.py, the existing ingestion test file and this handoff changed.
E's browser test and C/D/E/M files were not edited; no injected UI/test mapping
workaround was used. Main/E must rerun the unchanged real browser/API/PostgreSQL
default upload flow on the delivered SHA. No Docker, product model, source API or
customer sending was used for this local fix; existing external limits remain.

## AB-FIX-SUMMARY-COPY follow-up

Base: `026490a4558ffc50dba03a28c14b2e03dcfa32e9`. Replaced only the user-visible
change_summary coordination placeholder with a concise Chinese explanation that
the assessment uses the listed sources and presents fact status, evidence status
and unresolved questions separately. It does not claim a new event, update,
confirmation or durable revision. Matching and revision allocation remain C's
responsibility; no processing behavior, IDs/hashes, severity/evidence fields,
unknown codes, model settings or DTOs changed.

- `uv run --frozen ruff check src/oil_agent/intelligence/assessment.py`: passed.
- `uv run --frozen pytest tests/unit/intelligence -q`: 14 passed.
- Existing tests were used without adding text-only assertions.

Only assessment.py and this handoff changed. No Docker or live calls were used.
The coordinator's reported eight-browser/264-Python integration evidence applies
to the base above, not this successor. Final I must adopt the copy-only successor
and rerun integrated CI; that validation was not performed in this AB follow-up.
