# Controlled trial deployment contract

Preparation only. No provider request, firewall installation, network creation,
container start, public port, certificate purchase or phone exercise is approved
by this document. Business inputs stay in the coordinator's unique V01-TODO.md;
this file documents deployment mechanics and limits, not another approval board.
The production factory remains unsupported. Use the accepted I candidate only.

The existing AB/D clients disable ambient proxies. AB resolves an allowed host,
pins its public address and retains Host/SNI plus certificate validation. This
preparation therefore uses explicit host-to-public-IPv4 pins, with a dedicated
Linux bridge and host firewall allowing those addresses on TCP 443 only.
It does not add a proxy, modify adapters or weaken their URL/TLS checks.

## Offline preparation

Run `uv run --locked python scripts/controlled_trial.py prepare --pins /absolute/project/pins.json
--output-dir /absolute/project/new-preparation` on one line. The output directory
must be new; existing files are never overwritten. No process, DNS request or
network operation runs. An empty `{}` pin map generates deny-all egress. Never
copy synthetic test IPs into a real trial.

The nonsecret JSON map may contain only the enabled existing adapter hosts:
`mcp.jin10.com`, `api.openai.com`, `accounts.feishu.cn`, `open.feishu.cn`.
Each needs one explicitly approved current public IPv4 address. No CIDR,
wildcard, automatic DNS refresh, IPv6 or alternative provider is supported.
The exact set must match enabled capabilities; identity uses both Feishu hosts.
An address change requires stop, reviewed replacement pins/rules and a new
pre-start check, not an automatic fallback or increased budget.

Two artifacts are generated: `trial-pins.yaml`, containing only nonsecret hosts,
and `trial-firewall.sh`, containing commands for separate host-operator review.
The script does not execute those commands. They create dedicated chains and
refuse existing chains/bridge rather than flushing or deleting unknown rules.
After authorized installation, the exact rules and first-position hooks are
checked in DOCKER-USER, FORWARD and INPUT. Only the two trial bridges match;
unrelated forwarding/firewall rules are not rewritten. Input to the host from
these bridges is rejected except established replies. IPv6 is disabled and
external recursive DNS fallback is loopback-only; Docker service-name resolution
provides the internal `postgres` name.

On an approved Linux Docker host using its iptables backend, install the reviewed
firewall first. Only then may an operator create the dedicated empty network:

```sh
docker network create --driver bridge \
  --label oil-agent.scope=e-controlled-trial \
  --opt com.docker.network.bridge.name=oil-e-trial-eg \
  oil-agent-e-trial-egress
```

This command was NOT EXECUTED. Confirm the chosen host has no conflicting bridge
or project and that IPv6 is disabled. The checker requires the exact name,
driver, label, bridge option, IPv4-only state and no attached containers. The
overlay never creates an unrestricted egress network by itself. Docker Desktop,
nftables backends and firewall managers which reorder the required hooks are
not accepted by this preparation. Recheck after any host/firewall change.

This is IP/port enforcement, not independent Layer-7 hostname enforcement:
shared CDN addresses can serve other hosts. Existing fixed host/TLS validation
remains essential. Packet-level DNS/IPv6/egress denial has not been tested on a
live host; configuration tests do not establish that assurance.

## TLS and existing application inputs

Use an explicit project injection file outside Git with restrictive host access.
Do not print `docker compose config`, container environment, OAuth query strings,
request bodies, Authorization/Cookie headers or TLS private keys. The checker
parses resolved Compose configuration in memory and emits generic errors only.
Keep the file local to the approved project; there is no credential discovery.

| Existing/new input | Exact deployment mapping |
| --- | --- |
| `OIL_DATABASE_URL`, `OIL_POSTGRES_PASSWORD` | Matching new credentials; `postgresql+psycopg://oil_e_trial:<injected>@postgres:5432/oil_e_trial`; separate `oil-agent-e-trial_trial-data` volume, no published PostgreSQL port |
| `OIL_PUBLIC_ORIGIN` | Exact approved HTTPS origin; local listener only `127.0.0.1:18443`; no public DNS/ingress is activated |
| New `OIL_TRIAL_TLS_CERT_FILE`, `OIL_TRIAL_TLS_KEY_FILE` | Explicit absolute project file paths; read-only mounts without auto-created host paths; key readable by gateway UID 101 only as needed |
| Existing `OIL_FEISHU_REDIRECT_URI` | Exact registered same-origin SPA redirect; the JSON session endpoint is not the browser redirect URL |
| Message callback | Approved origin plus `/api/v1/callbacks/ack`; raw body and signature headers retained, no rewrite/caching |
| Existing source/model/identity/send flags, permissions, budget and fixed secret variables | Unchanged C/I contract; defaults remain disabled/dry-run; per-recipient/revision/runtime authorization still applies |
| `OIL_DATA_PROVENANCE`, `OIL_FIXTURE_DATASET` | Overlay selects `trial` / literal `null`; it never relabels existing fixture data or reuses the old database |

The local TLS check verifies readable certificate/key pairing, current validity
and the exact DNS SAN. It does not establish public CA chain or phone trust.
An explicitly authored self-signed certificate is used only in automated tests.
Production/public trust and the externally reachable callback endpoint need the
approved operator's host/TLS setup and a separate actual phone/provider exercise.
The existing internal gateway has no external network attachment in this overlay.

Nginx access logging is off; error output is disabled because error lines can
include OAuth queries even with access logging disabled. Uvicorn retains its
existing `--no-access-log`. Container log rotation and resource limits remain
inherited. Collect only health/status, counters and redacted IDs for acceptance;
full application/host log redaction is not inferred from proxy settings.

## Pre-start gate and future operator action

The default script action is read-only `check`. Supply explicit `--pins`,
`--pins-overlay`, `--origin`, `--tls-cert`, `--tls-key` and `--env-file`. Missing
TLS or mismatched project/database/ports/pins/provenance refuses before firewall
or network acceptance. A missing/widened/inactive firewall or wrong/attached
network refuses. None of these checks makes a provider request.

Only after separate live-action authorization may an operator run:

```sh
sh scripts/trial-start.sh /absolute/project/pins.json \
  /absolute/project/new-preparation/trial-pins.yaml https://approved-origin \
  /absolute/project/cert.pem /absolute/project/key.pem /absolute/project/trial.env
```

Use real approved inputs, not the illustrative paths/origin above. This wrapper
requires every pre-start check to succeed before `up --detach --no-build --pull
never`. It does not change rules, create the network, seed users or obtain keys.
Prebuild the reviewed images separately. There is no automatic installation or
public ingress opening. The underlying Compose files are not an authorization
boundary against an operator deliberately bypassing the wrapper or changing them.

## Graceful stop and recovery

Before any operator stop, use filtered project inspection and verify full IDs,
Compose project/service/working-directory/config-file labels against this exact
new checkout and three Compose files. Never adopt the old `oil-agent-e` database
or any C/I container. Retain a redacted state/lease/counter snapshot and backup
under the separately approved trial database scope. Existing E backup scripts
remain bound to the old E database; do not widen their guards or reuse them here.

With the exact verified Compose selection and explicit injection file, stop
`gateway api ingest` to stop new work, then `normal urgent` with `stop --timeout
30`, and verify stopped states before stopping `postgres`. Preserve containers,
volumes, network and firewall; no `down`, `prune`, force removal or data deletion.
Do not report a graceful stop if it timed out or the daemon disappeared.

Resume requires `controlled_trial.py check-retained` with the same TLS/pins/
origin/explicit-injection arguments as `check`, plus seven repeated
`--container-id` arguments containing the full recorded IDs for postgres, init,
api, ingest, urgent, normal and gateway. The action is read-only: it requires all
seven to be cleanly stopped, unique services, exact project/config-file/working-
directory labels, matching environment, selected image ID/entrypoint, mounts,
ports, resource/privilege/DNS/IPv6 bounds and network IDs. Unknown attachments,
changed resources or an incomplete ID set refuse. It never lists or changes
unrelated resources and never detaches resources to bypass the cold-start check.
Configuration/secret comparisons stay in memory without printing their values.

After this revalidation and separate live-action approval, an operator starts
only PostgreSQL and runs C's existing `recover` with the same verified Compose
selection (`run --no-deps init recover`) while all workers remain stopped:
expired in-flight deliveries become UNKNOWN, and UNKNOWN requires reconciliation,
not manual retry or a new delivery row. No database checkpoint/outbox reset is
allowed. Preserve the recovery one-off container as evidence, then start the
already verified API/queue/gateway services. Automatic activation is not part of
the checker. Revalidate again if configuration/images/firewall/identities changed.
The existing PostgreSQL recovery tests remain the application evidence;
new-host stop/resume, backup/restore and physical-kill acceptance are NOT EXECUTED.

Official references checked for this preparation: Docker's
[iptables user-chain behavior](https://docs.docker.com/engine/network/firewall-iptables/),
[Compose override/reset semantics](https://docs.docker.com/reference/compose-file/merge/),
and [network DNS/custom-host behavior](https://docs.docker.com/engine/network/).
Compose `!override` requires 2.24.4 or newer; this workspace parsed with 5.1.4.
The checker handles Compose v2's false-bool omission and v5's explicit false
representation separately; explicit `create_host_path: true` stays rejected.
