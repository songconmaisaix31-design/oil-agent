#!/bin/sh
# Nightly logical backup with a 14-day local retention window.
# Schedule on the host, e.g. 03:15 Shanghai: 15 3 * * * /opt/oil-agent/deploy/backup.sh
set -eu

cd "$(dirname "$0")"
BACKUP_DIR=${OIL_BACKUP_DIR:-/var/backups/oil-agent}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
TARGET="$BACKUP_DIR/oil-agent-$STAMP.dump.gz"

mkdir -p "$BACKUP_DIR"
docker compose -f compose.production.yaml exec -T postgres \
  pg_dump -U oil_prod -d oil_prod --format=custom \
  | gzip -9 > "$TARGET"
gzip -t "$TARGET"
sha256sum "$TARGET" > "$TARGET.sha256"
find "$BACKUP_DIR" -name 'oil-agent-*.dump.gz*' -mtime +13 -delete
echo "BACKUP_OK $TARGET $(stat -c %s "$TARGET") bytes"
