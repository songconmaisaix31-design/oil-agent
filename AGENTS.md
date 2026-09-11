# Oil Agent execution protocol

Read `V01-TODO.md` and the user-supplied development plan before work. The plan is
the business source of truth. Preserve Python/FastAPI, PostgreSQL, Procrastinate,
bounded LangGraph processing and React/Vite. Do not build an agent scheduler.

- The coordinator writes only this file, README.md and V01-TODO.md. Technical
  foundation work is explicitly delegated to C; integration to a separate I agent.
- Four long-lived tracks: AB ingestion/intelligence/reporting, C contracts/backend,
  D channels/mobile, E verification/deployment. Each has one Orca worker, worktree,
  branch, recorded base SHA and exclusive write paths listed in V01-TODO.md.
- Read anywhere in this repository; edit only assigned paths. Request cross-track
  changes through the coordinator. Do not spawn additional workers.
- Each verified increment must be committed and pushed to the existing origin.
  Never force push, overwrite public history, delete unknown work or expose secrets.
- Use English in code and technical artifacts, Chinese for user-facing discussion.
- Production sending is disabled by default. No paid service, account login,
  guessed commercial endpoint, customer message or deployment is authorized here.
  Never read, print, copy or store existing secret values.
- Fixtures remain labeled and isolated. API acceptance is not phone receipt;
  dry-run is not production; PostgreSQL concurrency cannot be verified by SQLite.
- UTC-aware storage, Decimal prices, explicit evidence, original publisher grouping,
  transactional checkpoints/outbox and per-recipient per-revision authorization are
  mandatory. Unknown delivery outcomes must not be blindly retried.
- Test core paths and build before completion claims. Report failures and skipped
  external validation. Do not weaken tests to obtain a passing result.
- Send structured handoff with actual commit, paths, commands/results, limitations
  and contract requests. Follow the live Orca lifecycle preamble exactly.

User authorization for ordinary development, tests, commits and pushes to this
existing repository persists; do not ask again for routine reversible work.
