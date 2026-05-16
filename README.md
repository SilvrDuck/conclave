# conclave

Consensus-driven, orchestrator-free platform for building microservice projects with autonomous AI agents.

See [spec/](spec/) for the authoritative v2 specification. North star: [spec/00-vision.md](spec/00-vision.md).

## Quick start

```bash
bash kickstart.sh        # brings the platform up
# open http://forum.conclave.local
bash teardown.sh         # stops everything (state preserved on volumes)
```

## Repo layout

```
libs/conclave-core/        shared events, models, bus + db clients
services/observer/         FastAPI: Operator + Observation contexts, Forum API
services/mcp-{senate,coms,decisions,state,pods}/  one MCP server per bounded context
services/forum/            React + Vite + Tailwind + Radix + ReactFlow
pods/                      pod templates (code / adopted)
infra/                     docker-compose, postgres init, traefik, otel, tempo configs
tests/                     e2e + smoke
```

## Development

```bash
uv sync                    # install all python workspace members
pnpm install               # install frontend
pnpm dev:forum             # run forum standalone
pytest                     # all python tests
```
