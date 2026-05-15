#!/usr/bin/env bash
# Kickstart a brand-new Conclave project from a blank slate.
#
# Wipes any running stack + volumes, re-scaffolds /tmp/conclave-demo via the
# wizard, brings the platform up *without* any pods, starts the host-side
# pod spawner, launches the founder pod, and sends the mandate.

set -euo pipefail

CONCLAVE_DIR="${CONCLAVE_DIR:-/home/thibault/code/conclave}"
PROJECT_ROOT="${PROJECT_ROOT:-/tmp/conclave-demo}"
MANDATE="${MANDATE:-Build a tiny TODO API with auth and a one-page frontend. Use as many pods as the senate deems necessary.}"
FOUNDER="${FOUNDER:-founder}"

cd "$CONCLAVE_DIR"

echo "[kickstart] tearing down any running stack…"
docker compose -f infra/compose.yaml down -v 2>&1 | tail -3 || true

echo "[kickstart] killing stale spawner if any…"
pkill -f "scripts/pod_spawner.py" 2>/dev/null || true

echo "[kickstart] wiping $PROJECT_ROOT…"
rm -rf "$PROJECT_ROOT"
mkdir -p "$PROJECT_ROOT"

echo "[kickstart] scaffolding fresh project via wizard…"
(
  cd platform
  uv run conclave-wizard init --quickstart \
    --project-root "$PROJECT_ROOT" \
    --founder-name "$FOUNDER" \
    --mandate "$MANDATE" \
    --github-token "$(gh auth token 2>/dev/null || echo '')" \
    --telegram-chat-id "${TELEGRAM_CHAT_ID:-107650898}" \
    > /dev/null
)

cp "$CONCLAVE_DIR"/{iusiurandum,primitives,voting-strategies,charter-template}.md "$PROJECT_ROOT"/
cp -r "$CONCLAVE_DIR/personae" "$PROJECT_ROOT/personae"

(
  cd "$PROJECT_ROOT"
  git init -q -b main
  git add -A
  git -c user.email=conclave@local -c user.name=conclave commit -q -m "init"
)

echo "[kickstart] building platform + pod images (cached layers should be fast)…"
docker compose -f infra/compose.yaml build observer 2>&1 | tail -2
docker build -f infra/pod.dockerfile -t conclave-pod:0.1 . 2>&1 | tail -2

echo "[kickstart] bringing up the platform (no pods yet)…"
PROJECT_ROOT="$PROJECT_ROOT" docker compose -f infra/compose.yaml up -d \
  bus observer senate-ledger mcp-coms mcp-senate mcp-decisions mcp-state forum-ui

echo "[kickstart] waiting for senate-ledger healthy…"
until curl -sf http://localhost:8001/healthz > /dev/null; do sleep 1; done

echo "[kickstart] launching pod spawner in background…"
mkdir -p "$PROJECT_ROOT/.conclave"
(
  cd platform
  PROJECT_ROOT="$PROJECT_ROOT" nohup uv run python scripts/pod_spawner.py \
    --project-root "$PROJECT_ROOT" \
    --docs-root "$PROJECT_ROOT" \
    > "$PROJECT_ROOT/.conclave/spawner.log" 2>&1 &
  echo "$!" > "$PROJECT_ROOT/.conclave/spawner.pid"
)
echo "[kickstart] spawner PID: $(cat "$PROJECT_ROOT/.conclave/spawner.pid")"

echo "[kickstart] launching founder pod…"
PROJECT_ROOT="$PROJECT_ROOT" docker compose -f infra/compose.yaml up -d founder

echo "[kickstart] waiting for founder Pi to attach…"
until docker logs conclave-founder 2>&1 | grep -q "harness.ready"; do sleep 1; done

echo "[kickstart] sending mandate…"
(
  cd platform
  uv run python scripts/wake_founder.py --pod "$FOUNDER" "$MANDATE"
)

cat <<EOF

[kickstart] ✓ everything is up. To watch:

  docker compose -f infra/compose.yaml logs --follow --tail=50 founder
  tail -f $PROJECT_ROOT/.conclave/spawner.log
  open http://localhost:5173                  # Forum UI
  curl localhost:8001/proposals | jq          # senate state
  curl localhost:8001/adrs      | jq          # ADRs
  curl localhost:8000/state/members | jq      # admitted pods

Send more goals:
  ./platform/.venv/bin/python platform/scripts/wake_founder.py "<new goal>"

Stop everything:
  kill \$(cat $PROJECT_ROOT/.conclave/spawner.pid)
  docker compose -f infra/compose.yaml down -v
EOF
