#!/bin/sh
# Usage: sh scripts/restore-isolated.sh /approved/private/file.dump oil_e_restore_SUFFIX
# Restores only into a newly created database; no overwrite, clean, drop or sending.
set -eu
if [ "$#" -ne 2 ]; then
  echo "Usage: restore-isolated.sh /approved/private/file.dump oil_e_restore_SUFFIX" >&2
  exit 2
fi
case "$1" in /*) ;; *) echo "An explicit absolute backup path is required" >&2; exit 2 ;; esac
if [ ! -f "$1" ] || [ -L "$1" ]; then
  echo "A regular, trusted backup file is required" >&2
  exit 2
fi
case "$2" in oil_e_restore_?*) ;; *) echo "Restore target must have the oil_e_restore_ prefix" >&2; exit 2 ;; esac
case "$2" in *[!a-z0-9_]*) echo "Invalid restore database name" >&2; exit 2 ;; esac
if [ "${#2}" -gt 63 ]; then
  echo "Restore database name is too long" >&2
  exit 2
fi
oil_backup=$1
oil_restore=$2
. "$(dirname -- "$0")/compose_scope.sh"
oil_check_postgres_scope
oil_compose exec -T postgres pg_restore --list <"$oil_backup" >/dev/null
# createdb fails atomically if the target already exists. Never continue on failure.
oil_compose exec -T postgres createdb --username=oil_e_test \
  --owner=oil_e_test --template=template0 "$oil_restore"
if ! oil_compose exec -T postgres pg_restore --username=oil_e_test \
    --dbname="$oil_restore" --exit-on-error --single-transaction --no-owner --no-acl <"$oil_backup"; then
  echo "Restore failed; new isolated target retained for inspection" >&2
  exit 1
fi
echo "Isolated database restored; application state reconciliation is still required"
