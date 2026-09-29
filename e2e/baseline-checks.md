# E-BASELINE validation receipt

Status: **REVIEW for this bounded increment**. Corpus consistency passed; none of
the T01-T28 application/runtime acceptance cases has executed. This is not an
end-to-end application, deployment or production receipt.

- Branch: `songconmaisaix31-design/oil-v01-e`.
- Verified clean starting base: `f5d5face60c160e70a7565498a6da54ed33c15fd`.
- Tested artifact/code commit: `62bd7d699bd39e02586d616796f34f6d22dc45f7`.
- Final verification completed at `2026-09-11T18:16:12Z`
  (`2026-09-12T02:16:12+08:00`). Scenario clocks are synthetic and unrelated to this
  measured execution time.
- Environment: Windows PowerShell, Python 3.13.13, Ruff 0.15.20. Standard library
  validator; no dependency installation, database, browser, model or Docker run.
- Source/product usage in this increment: zero source requests, zero product model
  calls, zero customer/test messages. These do not count development-agent usage
  or the authorized Git push as product usage.
- Read-only C observation: foundation commit
  `558010bee164f2161a0928384eb6aac36e001c07` and Python contract files existed later
  in the run; not merged or tested in this E checkout.

## Delivered paths and actual checks

| Path | Content |
| --- | --- |
| `fixtures/scenarios/v01.json` | Fixed synthetic T01-T28 stimuli, provenance, evidence references, expectations and pending acceptance classifications |
| `fixtures/scenarios/README.md` | Corpus format, variant expansion, adaptation and evidence boundaries |
| `scripts/validate_scenario_corpus.py` | Runnable standard-library consistency validator; no application simulation |
| `docs/runbook.md` | Source/identity/phone/longitudinal gates, isolation, backup/restore, rollback and redaction procedures |
| `e2e/baseline-checks.md` | This verification receipt, added after the tested artifact commit |

| Executed command/check | Actual result |
| --- | --- |
| `python --version` | Python 3.13.13; exit 0 |
| `python -B scripts/validate_scenario_corpus.py` | Exit 0: 28 fixed synthetic cases consistent |
| `ruff check --isolated --select E,F,I,UP,B,ASYNC --target-version py313 --line-length 100 --no-cache scripts/validate_scenario_corpus.py` | All checks passed; exit 0 |
| In-memory negative checks below | 12 corruptions rejected; compile passed; missing-file CLI exit 1 as expected; parent exit 0 |
| `git diff --cached --check` before artifact commit; `git diff HEAD --check` after it | Exit 0; no whitespace errors |
| Path review | All changes confined to assigned E paths; no root config or business code |

The corpus checker reported overlapping gate counts: `automated_local=14`,
`automated_postgresql=13`, `external_manual=10`. These are planned gate counts,
not passed tests. Its output explicitly says all 28 application cases are NOT
EXECUTED. An initial checker run found a symbolic disconnect phase named as a
timestamp; the field was corrected to `disconnect_phase`. Initial Ruff findings
were corrected before the artifact commit; final checks above passed without
weakened assertions.

The host has no `py` launcher in this terminal; the initial `py -3.13 --version`
probe failed. `python` resolves to the installed Python 3.13.13 and is the tested
command. No environment workaround or root dependency/configuration change was
needed. Coordinator requested a lightweight finish and no additional Docker
services; none were started. Port 55434/Compose `oil-agent-e` remain reserved for a
future dispatch, with availability and ownership to be checked immediately before
use.

## Reproduce the negative checks

From the repository root in PowerShell, this operates on in-memory copies only;
it does not mutate frozen inputs or create temporary files:

```powershell
@'
import copy
import json
import runpy
import subprocess
import sys
from pathlib import Path
m = runpy.run_path('scripts/validate_scenario_corpus.py')
base = m['read_corpus'](Path('fixtures/scenarios/v01.json'))
assert m['validate'](base) == []
mutations = [
 ('missing_case', lambda c: c['cases'].pop()),
 ('wrong_order', lambda c: c['cases'].reverse()),
 ('lost_fixture_label', lambda c: c['cases'][0]['inputs'][0].update(is_fixture=False)),
 ('unsafe_sending', lambda c: c['defaults'].update(production_sending=True)),
 ('broken_reference', lambda c: c['cases'][0]['expectations'][0].update(evidence_refs=['old#/missing'])),
 ('naive_time', lambda c: c['cases'][0].update(clock_at='2026-09-12T04:00:00')),
 ('float_price', lambda c: c['cases'][10]['inputs'][0]['payload']['base'].update(value=7000.1)),
 ('unknown_provenance', lambda c: c['cases'][0]['inputs'][0].update(provenance_ref='missing')),
 ('false_runtime_pass', lambda c: c['cases'][0]['acceptance'][0].update(status='PASS')),
 ('removed_postgresql_gate', lambda c: c['cases'][12]['acceptance'][0].update(category='automated_local')),
 ('removed_phone_gate', lambda c: c['cases'][23]['acceptance'][0].update(category='automated_local')),
]
for name, mutate in mutations:
 candidate = copy.deepcopy(base)
 mutate(candidate)
 assert m['validate'](candidate), name
try:
 json.loads('{"is_fixture":true,"is_fixture":false}', object_pairs_hook=m['unique_object'])
except ValueError:
 pass
else:
 raise AssertionError('duplicate_json_key')
compile(Path('scripts/validate_scenario_corpus.py').read_text(encoding='utf-8'), 'validator', 'exec')
failed = subprocess.run([sys.executable, '-B', 'scripts/validate_scenario_corpus.py', '--corpus', 'fixtures/scenarios/absent-negative-check.json'], capture_output=True, text=True)
assert failed.returncode == 1
assert failed.stderr.strip() == 'FAIL: unable to read valid corpus JSON'
print('PASS: valid corpus; 12 negative mutations rejected; script compiles; missing-file CLI exits 1')
'@ | python -B -
```

## Runtime acceptance matrix: NOT EXECUTED

Each input and expectation is in `fixtures/scenarios/v01.json` under the matching
`case_id`. Actual result, execution command, tested runtime commit/environment and
time are **not available** for these pending application cases. This baseline's
consistency command cannot populate those fields. Future execution must record
each variant and its actual evidence separately.

| Case | Intended acceptance | Actual / limitation |
| --- | --- | --- |
| T01 old news | Local automated | NOT EXECUTED; AB assessment pending integration |
| T02 plan/denial | Local automated | NOT EXECUTED; assertion classification |
| T03 reprints | Local automated | NOT EXECUTED; original-publisher grouping |
| T04 independent evidence | PostgreSQL | NOT EXECUTED; persisted revision/outbox lifecycle |
| T05 correction | PostgreSQL | NOT EXECUTED; original-recipient authorization and correction |
| T06 false merge | Local automated | NOT EXECUTED; facility/event association |
| T07 time/closed market | Local automated | NOT EXECUTED; clock/scheduling behavior |
| T08 paging | PostgreSQL | NOT EXECUTED; paging/checkpoints/gaps |
| T09 revision/restart | PostgreSQL | NOT EXECUTED; replay/recovery |
| T10 model failure | Local automated | NOT EXECUTED; bounded stub and evidence validation |
| T11 quote basis | Local + external | NOT EXECUTED; comparator and authorized quote sample |
| T12 stale metrics | Local automated | NOT EXECUTED; report snapshot rendering |
| T13 transactions | PostgreSQL | NOT EXECUTED; independent-connection fault injection |
| T14 queue isolation | PostgreSQL + external | NOT EXECUTED; workers/load test and real latency |
| T15 sending retry | PostgreSQL | NOT EXECUTED; concurrent leases/channel behavior |
| T16 UNKNOWN send | PostgreSQL + external | NOT EXECUTED; recovery and verified platform reconciliation |
| T17 callback identity | PostgreSQL + external | NOT EXECUTED; signed raw callbacks and tenant identity |
| T18 ack/upgrade | PostgreSQL | NOT EXECUTED; per-recipient/revision authorization |
| T19 report schedule | PostgreSQL | NOT EXECUTED; durable date/timezone uniqueness |
| T20 quota/authentication | Local + external | NOT EXECUTED; failure adapter and actual provider contract |
| T21 injection | Local automated | NOT EXECUTED; application side-effect spies |
| T22 network/files | Local automated | NOT EXECUTED; guarded transport/file parsers |
| T23 web permissions | Local + external | NOT EXECUTED; real API/browser and actual SSO |
| T24 phone states | External/manual | NOT EXECUTED; no authorized real phones/accounts tested |
| T25 restore/rollback | PostgreSQL + external | NOT EXECUTED; app/schema/Compose and approved target |
| T26 monitoring/redaction | Local + external | NOT EXECUTED; runtime logger/probes and off-host outage test |
| T27 fixture isolation | PostgreSQL | NOT EXECUTED; integrated provenance/outbox/UI enforcement |
| T28 evidence/costs | Local + external | NOT EXECUTED; counters/citations and approved billing reconciliation |

Also NOT EXECUTED: application build, Compose build/start, remote CI, authorized
source-to-platform-to-phone chain, source comparison >=7 days and continuous
operation >=14 days. No SQLite-based concurrency claim, external delivery claim,
customer-data validation or production action is made.

## Handoff and contract dependencies

No cross-track edits or immediate contract-change requests. In the next dispatch,
map this scenario format to C's authoritative DTOs rather than copying DTOs here.
Obtain the integrated dependency-locked candidate and actual fixture seeding,
transaction fault, clock, worker, transport and verified identity entry points.
Then implement application integration/Compose in E-owned paths and retain the
same fixed expectations. Escalate missing fault hooks or model/channel boundaries
to the coordinator/owner; do not weaken cases or fabricate runtime evidence.

Public source licensing, real recipient/policy/budget/retention configuration,
Feishu tenant/identity, authorized quote material, phones, deployment/probe host
and longitudinal observation remain external gates. See
[the runbook](../docs/runbook.md) for the required evidence and operational steps.
