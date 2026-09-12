#!/bin/sh
# Explicit future operator action; never invoked by preparation/default check.
set -eu
if [ "$#" -ne 6 ]; then
  echo "Usage: trial-start.sh PINS_JSON PINS_OVERLAY HTTPS_ORIGIN CERT_FILE KEY_FILE ENV_FILE" >&2
  exit 2
fi
oil_trial_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# TLS/config/firewall/network failure must occur before the first Compose up.
uv run --locked --project "$oil_trial_dir" python "$oil_trial_dir/scripts/controlled_trial.py" \
  check --pins "$1" --pins-overlay "$2" --origin "$3" --tls-cert "$4" \
  --tls-key "$5" --env-file "$6"
exec docker compose --env-file "$6" --project-name oil-agent-e-trial \
  --profile controlled-trial --file "$oil_trial_dir/deploy/compose.yaml" \
  --file "$oil_trial_dir/deploy/compose.e-trial.yaml" --file "$2" \
  up --detach --no-build --pull never
