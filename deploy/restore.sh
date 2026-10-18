#!/bin/sh
# Disaster recovery only. Stop producers first, then restore an explicit backup:
#   docker compose -f compose.production.yaml stop api ingest urgent normal
#   ./restore.sh /var/backups/oil-agent/oil-agent-YYYYMMDDTHHMMSSZ.dump.gz
set -eu

if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  echo "Usage: $0 <backup.dump.gz>" >&2
  exit 2
fi

cd "$(dirname "$0")"
BACKUP=$1
if [ -f "$BACKUP.sha256" ]; then
  sha256sum -c "$BACKUP.sha256"
fi
gzip -t "$BACKUP"
# The pipeline advances the restore regardless of the destructive --clean step.
gunzip -c "$BACKUP" | docker compose -f compose.production.yaml exec -T postgres \
  pg_restore -U oil_prod -d oil_prod --clean --if-exists --no-owner
docker compose -f compose.production.yaml start api ingest urgent normal
echo "RESTORE_OK $BACKUP"
