#!/bin/sh
# Run bounded recovery after a host reboot, once the API container is available.
# Installed as: @reboot sleep 20 && /opt/oil-agent/deploy/reboot-recover.sh ...
set -eu

cd "$(dirname "$0")/.."
for _attempt in $(seq 1 30); do
  if docker compose -f deploy/compose.production.yaml exec -T api \
      python -m oil_agent.runtime.cli recover >/dev/null 2>&1; then
    echo "RECOVER_OK $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    exit 0
  fi
  sleep 10
done
echo "RECOVER_FAILED $(date -u +%Y-%m-%dT%H:%M:%SZ)" >&2
exit 1
