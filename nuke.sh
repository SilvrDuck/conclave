#!/usr/bin/env bash
# Tear down the entire conclave platform and wipe all transient state.
#
# Use between realize → analyze → nuke passes (spec/08 §14). After this,
# `./kickstart.sh` brings up a virgin stack with zero pods.
#
# What this removes:
#   - every container started under the conclave compose project
#   - every named volume (postgres_data, nats_data, tempo_data)
#   - every rendered pods/<id>/ dir (kept: pods/_template, pods/_adopted_template)
#   - every conclave-pod-* container that escaped compose tracking
#
# This script intentionally does not touch:
#   - the prebuilt conclave/pod-template image (rebuild is cheap; keeping it
#     saves ~60s on the first pod spawn of the next pass)
#   - /etc/hosts entries
#   - your local git checkout

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${REPO_ROOT}/infra/compose.yaml"

red()   { printf '\033[31m%s\033[0m\n' "$*" >&2; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
blue()  { printf '\033[34m%s\033[0m\n' "$*"; }

command -v docker >/dev/null 2>&1 || { red "docker not found"; exit 1; }

blue "compose down -v (containers + volumes, all profiles)"
docker compose -f "${COMPOSE_FILE}" --profile "*" down -v --remove-orphans || true

blue "killing any straggler conclave-pod-* containers"
stragglers="$(docker ps -aq --filter 'name=conclave-pod-' || true)"
if [[ -n "${stragglers}" ]]; then
    docker rm -f ${stragglers}
fi

blue "removing rendered pod dirs (pods/pod-*)"
# Two ownership layers: mcp-pods chowns the rendered shell to the host
# user at spawn time, but the pod container itself runs as root and the
# files it writes at runtime (workspace, charter edits) end up root-owned.
# Try a plain rm first; on failure spawn an alpine:3 sidecar as root.
shopt -s nullglob
rendered=("${REPO_ROOT}"/pods/pod-*)
shopt -u nullglob
if [[ ${#rendered[@]} -gt 0 ]]; then
    if ! rm -rf "${rendered[@]}" 2>/dev/null; then
        blue "  (docker fallback — pod writes are root-owned)"
        docker run --rm -v "${REPO_ROOT}/pods:/p" alpine:3 sh -c 'rm -rf /p/pod-*'
    fi
fi

green "stack nuked. run ./kickstart.sh to start a fresh pass."
