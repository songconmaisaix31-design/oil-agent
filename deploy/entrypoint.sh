#!/bin/sh
set -eu

# Initialization is explicit and serialized by the Compose init service.
# Runtime commands are owned by C, never reimplemented by deployment scripts.
case "${1:-}" in
  api)
    shift
    exec python -m uvicorn "${OIL_ASGI_FACTORY:-oil_agent.bootstrap:create_app}" \
      --factory --host 0.0.0.0 --port 8000 --no-access-log "$@"
    ;;
  init)
    python -m oil_agent.runtime.cli migration
    python -m oil_agent.runtime.cli queue-schema
    exec python -m oil_agent.runtime.cli recover
    ;;
  worker|migration|queue-schema|recover)
    exec python -m oil_agent.runtime.cli "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
