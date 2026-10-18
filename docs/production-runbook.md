# Oil Agent production deployment runbook (single Linux host)

This runbook targets one Ubuntu 24.04 host (2 vCPU / 4 GB / 40 GB SSD) in a
region without mainland ICP requirements (Hong Kong or Singapore). Phase 1 is
push-only: Feishu private messages; no public web ingress, no login, no callback.

## 1. Host preparation

```sh
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git ufw
# Docker Engine + compose plugin from the official repository
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"   # re-login afterwards
sudo ufw default deny incoming
sudo ufw allow OpenSSH
sudo ufw enable
```

Enable a 2 GB swap file on a 4 GB host, and keep the host timezone in UTC
(report times are converted with the application's `Asia/Shanghai` setting).

## 2. Code and secrets

```sh
sudo mkdir -p /opt/oil-agent && sudo chown "$USER" /opt/oil-agent
git clone https://github.com/songconmaisaix31-design/oil-agent.git /opt/oil-agent
cd /opt/oil-agent
```

Create `deploy/production.env` from `deploy/.env.production.example`
(`chmod 600`). Fill:

- `OIL_DATABASE_URL` with the same database password as `OIL_POSTGRES_PASSWORD`
- provider keys (`OIL_EIA_API_KEY`, `OIL_GNEWS_API_KEY`, `OIL_DEEPSEEK_API_KEY`)
- `OIL_FEISHU_APP_SECRET`
- the four generated JSON fields from `scripts/build_live_config.py`

Create `deploy/.env` for Compose interpolation only:

```sh
printf 'OIL_POSTGRES_PASSWORD=%s\n' 'THE-SAME-DB-PASSWORD' > deploy/.env
chmod 600 deploy/.env deploy/production.env
```

Generate the permission/rules JSON on a trusted machine (or on the host before
injecting secrets) and keep the spec in a private directory:

```sh
uv run --locked python scripts/build_live_config.py \
  --spec private/live-spec.json --output-dir private/generated
```

## 3. Build and start

```sh
cd /opt/oil-agent
docker compose -f deploy/compose.production.yaml build
docker compose -f deploy/compose.production.yaml up -d
docker compose -f deploy/compose.production.yaml ps
./deploy/healthcheck.sh
```

The `init` service runs migrations, the Procrastinate schema and recovery once;
API and the three workers start only after it succeeds. API is bound to
`127.0.0.1:8000` for local health checks only.

## 4. First delivery and schedule

```sh
# Provision approved identities, select recipients and set 08:00 Shanghai.
uv run --locked python scripts/ops_config.py set --report-time 08:00 --recipients self
uv run --locked python scripts/ops_config.py show

# One real report delivery through the production factory (safe to re-run).
docker compose -f deploy/compose.production.yaml run --rm api \
  python scripts/feishu_self_test.py
```

If the host runs the app only in containers, run the ops commands inside the
`api` image as shown above so they see the container environment.

## 5. Backups, health and monitoring

```sh
# Nightly at 03:15 host time
( crontab -l 2>/dev/null; echo '15 3 * * * /opt/oil-agent/deploy/backup.sh >> /var/log/oil-agent-backup.log 2>&1' ) | crontab -
# Every five minutes
( crontab -l 2>/dev/null; echo '*/5 * * * * /opt/oil-agent/deploy/healthcheck.sh >> /var/log/oil-agent-health.log 2>&1' ) | crontab -
```

Copy `/var/backups/oil-agent/*` off-host (object storage or another machine).
Test a restore quarterly:

```sh
docker compose -f deploy/compose.production.yaml stop api ingest urgent normal
./deploy/restore.sh /var/backups/oil-agent/oil-agent-YYYYMMDDTHHMMSSZ.dump.gz
```

Alerting: forward `/var/log/oil-agent-health.log` failures to the operator
(Feishu webhook or the cloud provider's alarm on a missing heartbeat).

## 6. Upgrade and rollback

```sh
cd /opt/oil-agent
git pull --ff-only
docker compose -f deploy/compose.production.yaml build
docker compose -f deploy/compose.production.yaml up -d
./deploy/healthcheck.sh
```

Rollback: `git checkout <previous-sha>`, rebuild, `up -d`; restore the database
only when a migration is not backward compatible.

## 7. Seven-day acceptance checklist

Run the read-only evidence query each morning:

```sh
docker compose -f deploy/compose.production.yaml exec -T api \
  python scripts/soak_status.py --days 7
```

Record each day: report message id and Shanghai send time, source request counts,
model tokens, delivery states (accepted/unknown), worker health, backup file and
checksum. Source health `ok` means the last fetch succeeded; the checkpoint's
`gap_state` still records coverage uncertainty. Acceptance requires seven
consecutive days with the 08:00 report accepted, zero unauthorised recipients and
zero duplicate sends (UNKNOWN outcomes stay durable and are never blind-retried).
