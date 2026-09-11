#!/bin/sh
# Usage: sh scripts/backup.sh /approved/private/new-file.dump
# E-only synthetic rehearsal; does not authorize production data access.
set -eu
umask 077
if [ "$#" -ne 1 ]; then
  echo "Usage: backup.sh /approved/private/new-file.dump" >&2
  exit 2
fi
case "$1" in /*) ;; *) echo "An explicit absolute backup path is required" >&2; exit 2 ;; esac
oil_backup=$1
. "$(dirname -- "$0")/compose_scope.sh"
oil_check_postgres_scope

# Exclusive creation preserves every pre-existing file, including symlinks.
set -C
exec 3>"$oil_backup"
if ! oil_compose exec -T postgres pg_dump --username=oil_e_test \
    --dbname=oil_e_test --format=custom --no-owner --no-acl >&3; then
  echo "Backup failed; incomplete output retained for inspection" >&2
  exit 1
fi
exec 3>&-
if ! oil_compose exec -T postgres pg_restore --list <"$oil_backup" >/dev/null; then
  echo "Backup archive inspection failed; output retained" >&2
  exit 1
fi
echo "Backup created and archive listing checked; restore acceptance is separate"
