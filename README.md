# Oil Agent

Refined-oil news monitoring, evidence review and mobile alerts. The real-integration
v1.1 candidate adds explicit trial assembly to the accepted local fixture/dry-run
baseline. Licensed live calls, real Feishu login and phone receipt still require
the specified external authorization and real test evidence. Production assembly
is not implemented and rejects startup.

The implementation uses FastAPI/Pydantic, PostgreSQL/SQLAlchemy/Alembic,
Procrastinate, bounded LangGraph processing and React/Vite. It includes:

- Immutable source revisions, evidence-linked assessments, corrections and a
  transactional outbox, with separate ingest/urgent/normal queues.
- Per-recipient/version acknowledgement, database sessions/roles/CSRF and bounded
  recovery; ambiguous delivery outcomes remain UNKNOWN without blind resend.
- CSV/XLSX preview and idempotent import, a 2,000,000-byte raw upload limit,
  Decimal comparison on matching quote bases, and evidence-linked daily reports.
- Chinese mobile views for events, evidence, reports, quotes, settings and feedback.
- Linux Compose, scoped backup/restore tools, fixed synthetic cases and Linux CI.
- Bounded Jin10 MCP HTTPS transport, schema discovery and revision adaptation;
  an explicitly configured OpenAI Responses client with durable request/token limits.
- Reusable approved-rule assessment without per-message manual annotations,
  separate fixture/trial/production provenance, and scoped Feishu OAuth/send/ack.

## Trial connection

The common `oil_agent.bootstrap:build_runtime` factory selects trial components
from validated settings. Set `OIL_DATA_PROVENANCE=trial` and
`OIL_FIXTURE_DATASET=null` for authorized nonfixture data; keep fixture exercises
labeled with their dataset and a separately approved exercise/send permission.
The default remains an empty fixture/dry-run runtime.

Each source, model, identity and send capability requires its matching typed
permission, validity window and explicit project-scoped configuration. The factory
reads only fixed credential variables for enabled capabilities. It performs no
provider requests, migrations, identity provisioning or sample seeding at startup.
See [.env.example](.env.example), the [trial startup runbook](docs/runbook.md#explicit-trial-assembly),
and [C's permission contract](config/real-integration-contract.md) for exact fields
and the separate approved-identity provisioning command.

Loaded rules must match each model/send `rules_ref` as
`authorization_ref@version`. The reusable rubric is conservative and literal;
its source/facility/event/occurrence/impact/currentness criteria require business
approval and real false-positive/false-negative evaluation. Model output cannot
grant severity, provenance or send permission. Ordinary messages remain silent;
an urgent delivery exercise requires its own label and exact approved recipients.

Contextual guards separate complete casualty-only negative predicates from
affirmative event/impact evidence. Freshness uses the approved elapsed-age bound,
including a short midnight crossing; denial, planning, exercises and stale-news
protections remain. See the [R16 repair evidence](src/oil_agent/intelligence/R16-HANDOFF.md).

The [controlled trial preparation](deploy/controlled-trial.md) adds an opt-in
overlay, internal isolated database, explicit public IPv4 pins, loopback HTTPS
and read-only cold/retained-resource checks. Preparation does not apply host
firewall rules, activate public ingress, start a trial or send a message.

The implemented chain is Jin10 transport -> model extraction -> approved rules ->
PostgreSQL/checkpoint/outbox -> authorized Feishu -> authenticated acknowledgement.
Current synthetic-provider tests exercise the real adapters and PostgreSQL runtime;
they do not prove live provider access, platform acceptance or phone receipt.

## Local startup

Use Python 3.13 and uv 0.11.26; the frontend was verified with Node 24.16.0.
Allocate a new local PostgreSQL database and explicitly inject `OIL_DATABASE_URL`
using the `postgresql+psycopg` driver. No dotenv file or stored credential is loaded
automatically. Keep credentials outside Git and command output.

```sh
uv sync --locked
uv run --locked python -m oil_agent.runtime.cli migrate
uv run --locked python -m oil_agent.runtime.cli queue-schema
uv run --locked python -m oil_agent.runtime.cli recover
uv run --locked uvicorn oil_agent.bootstrap:create_app --factory --host 127.0.0.1 --port 8000
```

Run each worker in a separate terminal using
`uv run --locked python -m oil_agent.runtime.cli worker --queue ingest`,
`--queue urgent`, or `--queue normal`. API and workers share
`oil_agent.bootstrap:build_runtime`. The default fixture branch creates no users,
recipients, source subscriptions or sample records. Trial capabilities use only
the explicitly configured permissions above.

See the [runbook](docs/runbook.md) for the Linux web gateway, full service startup,
explicit E-only synthetic browser rehearsal, database isolation and recovery.
The E rehearsal is a separate opt-in; its test sessions are not real authentication.
The current container disposition is recorded in V01-TODO.md; historical stopped
container evidence does not replace a current host-state check.

## Historical fixture candidate

Factory code `a4617e9528177c536c1768297f1ff5783ee1f9ec` passed
[Linux CI 34639549516](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34639549516):

| Check | Result |
| --- | --- |
| `pytest tests/contracts tests/unit -q` with PostgreSQL | 195 passed, 0 skipped |
| `pytest tests/integration -q` with separate PostgreSQL | 72 passed, 0 skipped |
| `npm test` | 13 passed |
| Generated OpenAPI types, TypeScript and Vite build | PASS |
| Backend and frontend Linux image builds | PASS |

Locked synchronization, Ruff, Python packaging and a fresh I database/HTTP smoke
also passed. The complete PostgreSQL suites use explicit, separate test services;
a local run that skips missing databases is not equivalent to this acceptance.
One upstream Starlette/AnyIO deprecation warning remains.

The [integration handoff](config/integration-handoff.md) records exact producer
commits, commands, scope and branch verification. [E's runtime evidence](e2e/runtime-checks.md)
records eight actual Chrome/API/PostgreSQL flows, queue isolation, graceful Linux
restart and isolated restore on its stated candidate. Those historical screenshots
are not relabeled as a newer browser run. [V01-TODO.md](V01-TODO.md) is the delivery board.

## Current delivery and remaining gates

Independently accepted code is `239baa69b06bf9ede8c71391d12a2cb89e1a1064` on
`songconmaisaix31-design/oil-v01-i`. Independent E review and
[CI 34669549557](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34669549557)
confirm 375 core and 237 integration tests passed, with zero failures/errors/skips.
The unchanged R16 regressions, all 13 factory PostgreSQL cases and preserved
denial/session regressions pass;
23 frontend tests, generated schema, TypeScript/Vite, shell and both Linux image
builds also pass. I's focused full Ruff check and Python packaging passed.
[Deployment CI 34669549519](https://github.com/songconmaisaix31-design/oil-agent/actions/runs/34669549519)
passed 70 overlapping preparation cases and actual Nginx configuration/key loading
in a network-isolated container. This is synthetic code/preparation acceptance;
real trial network, TLS trust, callbacks and phone receipt remain untested.

Earlier failures and exact producer commits remain in the integration/E reports.
Final report/governance adoption does not change this application code. The unique
[V01-TODO.md](V01-TODO.md) separates missing implementation, missing external
authorization and implemented paths awaiting real tests. Actual source/model/Feishu
calls, product tokens and product-call cost are zero; development-agent billing
was not collected.

The referenced original PRD and source-report documents were unavailable; the
provided development plan defines the current scope. Real source/model access,
business policies and recipients, authorized customer quote samples, Feishu
tenant/SSO/phone checks, deployment/TLS/off-host probes, production recovery,
load/SLA validation, seven-day source comparison and fourteen-day operation remain
uncompleted. Default startup has no source subscription; trial data requires
explicit scope and configuration. No production acceptance is claimed. This
candidate does not execute trades.
