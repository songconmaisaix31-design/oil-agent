# Oil Agent

Local development candidate for refined-oil news monitoring, evidence review and
mobile alerts. Current acceptance covers original synthetic replay and dry-run
delivery. Licensed live monitoring, real Feishu identity/delivery and phone receipt
are not enabled or accepted.

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
`oil_agent.bootstrap:build_runtime`. It wires existing local services but creates
no users, recipients, source subscriptions or sample records. Login remains
unavailable until an authorized identity adapter is configured and verified.

See the [runbook](docs/runbook.md) for the Linux web gateway, full service startup,
explicit E-only synthetic browser rehearsal, database isolation and recovery.
The E rehearsal is a separate opt-in; its test sessions are not real authentication.
All task-created C/E/I test containers were stopped and retained at handoff.

## Verified candidate

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

## Remaining gates

The referenced original PRD and source-report documents were unavailable; the
provided development plan defines the current scope. Real source/model access,
business policies and recipients, authorized customer quote samples, Feishu
tenant/SSO/phone checks, deployment/TLS/off-host probes, production recovery,
load/SLA validation, seven-day source comparison and fourteen-day operation remain
uncompleted. The built-in source list is empty and quote/report paths remain
fixture-labeled. This candidate does not execute trades.
