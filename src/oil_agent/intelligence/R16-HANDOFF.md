# R16 contextual guard repair

## Scope and baseline

Continued the existing `songconmaisaix31-design/oil-v01-ab` branch from clean
`6c517f5c4e5ffc2b4b844f91d49de90aba3848b8`. Ordinary merges adopted accepted
simulated-integration baseline `cd6e8d9d87acbde9b844b4568ab2df72e00bab8d`,
E's test-first reproduction `b9a241acfe0353ce425a7eef258111d72fcc253d` and M
governance `47f0eb3`; pre-repair HEAD is
`d9ed1a7d6266427d4d121df7b911027c2bfb8ecb`. No E test/fixture or I seam was edited.
Repair changes are limited to `intelligence/rules.py`, `assessment.py`,
`tests/unit/intelligence/test_rules.py` and this report. No dependency, DTO,
approved rule schema, runtime authorization or recipient behavior changed.

## Reproduction and behavior

Before changing application code, ran E's exact command:

```text
uv run --locked pytest tests/integration/test_contextual_guards.py tests/integration/test_rules_acceptance.py -q --tb=short
```

Result: **8 failed, 28 passed, 0 skipped**. The six casualty cases failed at
rule matching, status guarding and assessment (same clause/separate sentence).
The two midnight cases failed at matching and assessment, despite only 50 seconds
between publication and processing inside the approved 60-minute age window.

The shared `occurrence_context` helper recognises complete punctuation-delimited
Chinese casualty-only negative predicates. It separates the negative predicate
from event/supply occurrence checking; the negative object must be exclusively
casualties, with no compound object, modal, quotation or unrecognised suffix.
All remaining blocker cues still apply, including in other sentences or titles.
Affirmative configured facility/event/occurrence/impact/currentness terms must
match the remaining text within the same original clause. Thus a negated casualty
object cannot itself satisfy a configured positive impact criterion. The status
guard uses the same context; a casualty-only record cannot become an occurred
event. This grants no credibility, severity or source permission by itself.

Source text is not rewritten: the derived view is transient and evidence remains
an exact original substring, including casualty qualifiers in the selected clause.
Source identity/content hashes and unknown exact occurrence times are preserved.
Explicit operator exclusions still inspect the complete original text. The
existing English reviewed DENIED correction remains denied/routine and preserves
the correction suggestion; C still owns original-recipient delivery semantics.

Freshness now uses the approved elapsed `max_age_minutes` window for publication
and any known occurrence time, without requiring the processing calendar date to
equal the publication date. The exact maximum-age boundary is inclusive; one
second beyond it is stale. Future timestamps, uncertain time quality, source and
provenance scope, rule validity, currentness evidence and trust gates remain.
The configured timezone remains validated; no occurrence timestamp is inferred
from a relative publication phrase.

AB added 32 synthetic unit cases with reused policies, not per-message reviews or
full-message templates. In addition to the original eight failures, AB's initial
qualifier/age tests reproduced five failures; adversarial tests also exposed
missing `没有` and `失实` blocker forms, which now remain conservative even when
a separate casualty-only qualifier is present. Compound denial, impact denial,
conditional/exercise/uncertain text, cross-facility split evidence, negative-only
records and exact age/source/time gates are covered.

## Validation

- Exact E command above after repair: **36 passed**, zero skipped; assertions and
  both test files are unchanged from E `b9a241a` (verified with Git blob hashes).
- `uv run --locked pytest tests/unit/ingestion tests/unit/intelligence tests/unit/reporting -q --tb=short`:
  **210 passed**, including the prior English correction and Chinese false-urgent
  regressions.
- `uv run --locked pytest -m 'not postgres' -q --tb=short`:
  **435 passed, 111 PostgreSQL cases deselected**, one existing Starlette/AnyIO
  deprecation warning.
- `uv run --locked ruff check src/oil_agent/intelligence tests/unit/intelligence`:
  passed.
- `uv build --out-dir "$env:TEMP/oil-ab-r16-ctx-915cc32ffee1"`:
  source distribution and wheel built outside the repository.
- `git diff --check`: passed.

## Integration and practical limits

I should merge the delivered repair SHA and E should independently rerun unchanged
contextual/rules tests and integrated CI, including PostgreSQL correction scope.
AB did not start/restart Docker or execute PostgreSQL tests in this dispatch.
This local result does not establish final I candidate or remote CI acceptance.

The grammar deliberately handles a narrow casualty qualifier, not general Chinese
negation, arbitrary topic resolution, quoted speech or multilingual reasoning.
Other/ambiguous constructions remain subject to the existing conservative
blockers; unrelated unsupported qualifiers can still produce false negatives.
An affirmative rule match is an approved-source assertion, not independent proof
that an event happened. Business rule/provider approval and live accuracy remain
separate from these synthetic examples. This repair does not reprocess or relabel
existing stored records.

Real source/model/Feishu calls, model tokens and paid product cost are **0**;
no credentials were discovered, no recipients were contacted, and no production
factory or external acceptance is claimed. Development-agent/CI billing is unknown.
