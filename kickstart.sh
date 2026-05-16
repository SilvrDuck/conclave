#!/usr/bin/env bash
# Bring the conclave platform up. Idempotent — re-running does not wipe state.
#
# What this does, in order:
#   1. Verify docker + compose are available.
#   2. Add forum/api hostnames to /etc/hosts (with sudo) if missing.
#   3. `docker compose --profile conclave up -d --build`.
#   4. Wait for /healthz on the observer.
#
# Failure modes are surfaced loudly. No retry loops.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${REPO_ROOT}/infra/compose.yaml"

red()   { printf '\033[31m%s\033[0m\n' "$*" >&2; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
blue()  { printf '\033[34m%s\033[0m\n' "$*"; }

# ── 1. tooling ──────────────────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || { red "docker not found"; exit 1; }
docker compose version >/dev/null 2>&1 \
    || { red "docker compose plugin not found (need v2)"; exit 1; }

# ── 2. hostnames ────────────────────────────────────────────────────────
ensure_host_entry() {
    local host="$1"
    if ! grep -qE "^[^#]*\b${host}\b" /etc/hosts 2>/dev/null; then
        blue "adding 127.0.0.1 ${host} to /etc/hosts (sudo required)"
        echo "127.0.0.1 ${host}" | sudo tee -a /etc/hosts >/dev/null
    fi
}
ensure_host_entry forum.conclave.local
ensure_host_entry api.conclave.local

# ── 3. bring stack up ───────────────────────────────────────────────────
# Plumb host paths into mcp-pods so it can bind-mount Claude creds + the
# project dir into the pods it spawns. Compose interpolates ${VAR} from
# the caller's environment, so we export here.
export HOST_PROJECT_DIR="${REPO_ROOT}"
export HOST_CLAUDE_CREDENTIALS="${HOME}/.claude/.credentials.json"
export HOST_CLAUDE_VERSIONS="${HOME}/.local/share/claude/versions"

blue "starting conclave platform (this may take a minute on first build)"
docker compose -f "${COMPOSE_FILE}" --profile conclave up -d --build

# ── 4. wait for observer health ─────────────────────────────────────────
blue "waiting for observer /healthz …"
for i in {1..30}; do
    if curl -fsS http://localhost:8000/healthz >/dev/null 2>&1; then
        green "observer healthy"
        break
    fi
    if [[ "$i" -eq 30 ]]; then
        red "observer did not become healthy in 60s"
        docker compose -f "${COMPOSE_FILE}" ps
        exit 1
    fi
    sleep 2
done

green "conclave is up. open http://forum.conclave.local"
