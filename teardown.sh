#!/usr/bin/env bash
# Stop conclave. State (postgres, nats, tempo volumes) is preserved.
# For a clean wipe pass --hard to also remove named volumes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${REPO_ROOT}/infra/compose.yaml"

HARD=0
for a in "$@"; do
    [[ "$a" == "--hard" ]] && HARD=1
done

if [[ "$HARD" == 1 ]]; then
    docker compose -f "${COMPOSE_FILE}" --profile "*" down -v
    rm -f "${REPO_ROOT}/infra/traefik/dynamic/"*.yml 2>/dev/null || true
else
    docker compose -f "${COMPOSE_FILE}" --profile "*" down
fi
