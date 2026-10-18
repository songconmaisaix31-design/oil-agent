#!/bin/sh
# Host-level health check for cron/uptime probes. Prints one line per signal.
set -eu

cd "$(dirname "$0")"
FAIL=0

if ! curl -fsS --max-time 5 http://127.0.0.1:8000/readyz >/dev/null; then
  echo "API_READYZ_FAIL"
  FAIL=1
else
  echo "API_READYZ_OK"
fi

for service in ingest urgent normal; do
  state=$(docker compose -f compose.production.yaml ps --format '{{.Health}}' "$service" 2>/dev/null || true)
  if [ "$state" = "healthy" ]; then
    echo "WORKER_${service}_OK"
  else
    echo "WORKER_${service}_FAIL state=${state:-unknown}"
    FAIL=1
  fi
done

STATUS=$(docker compose -f compose.production.yaml ps --format '{{.Name}} {{.Status}}')
echo "$STATUS"
exit "$FAIL"
