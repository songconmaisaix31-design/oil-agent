#!/bin/sh
# Send the full evidence appendix for today's report as a Feishu file.
# Installed as: 5 8 * * * /opt/oil-agent/deploy/send-detail.sh
set -eu

cd "$(dirname "$0")/.."
docker compose -f deploy/compose.production.yaml exec -T api \
  python scripts/send_report_detail.py "$@"
