# Synthetic E fixtures

`scenarios/v01.json` is the frozen T01-T28 input corpus, with original synthetic
provenance and explicit expectation references. Its baseline acceptance statuses
describe planned gates. Current executions are reported in `e2e/runtime-checks.md`;
the consistency checker never upgrades application or external gates.

`runtime_factory.py` is an opt-in local Linux/browser composition fixture. Its one
English terminal-outage statement and three `e-browser-*` identities are original
fiction, dated 2026-09-11 UTC for replay. They are not public news, actual customers,
real Feishu accounts or a market claim. Every resulting object carries
`is_fixture=true`, `provenance=fixture`, `fixture_dataset=synthetic-e-runtime`.
The explicit ClaimReview and single-publisher policy are synthetic test inputs;
they do not establish a production source trust policy.

The runtime factory is excluded from the application image and mounted only by
`deploy/compose.e-runtime.yaml`. It rejects non-test, non-dry-run and any database
outside the exact reserved E local scope. It composes existing AB/C/D services;
it does not implement a parser, assessment, queue, sender or authentication API.
The seed command saves only newly generated synthetic sessions into an exclusive
operator-selected file outside Git. It does not discover existing credentials.
