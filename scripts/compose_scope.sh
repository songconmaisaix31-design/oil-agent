#!/bin/sh
# Shared scope check for the E-only backup and isolated restore commands.
set -eu
OIL_SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OIL_REPO_DIR=$(CDPATH= cd -- "$OIL_SCRIPT_DIR/.." && pwd)

oil_compose() {
  docker compose --env-file "$OIL_REPO_DIR/deploy/compose.env" \
    --project-name oil-agent-e --file "$OIL_REPO_DIR/deploy/compose.yaml" "$@"
}

oil_check_postgres_scope() {
  oil_container=$(oil_compose ps --quiet postgres)
  if [ -z "$oil_container" ]; then
    echo "Refusing operation: the E PostgreSQL service is not running" >&2
    exit 1
  fi
  oil_project=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$oil_container")
  oil_service=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}' "$oil_container")
  if [ "$oil_project" != oil-agent-e ] || [ "$oil_service" != postgres ]; then
    echo "Refusing operation: PostgreSQL container ownership does not match E" >&2
    exit 1
  fi
}
