# 04 — Wardley Map

**Tool**: Wardley Mapping (Simon Wardley).
**Aim**: place every conclave component on the
*user-need → genesis → custom → product → commodity* axis so we know
where to invest custom effort and where to lean on OSS.

> Anchor user need (top of every chain): **Augustus directs a swarm of
> agents to build, run, and evolve a microservice app, while watching
> them think and reason together.**

Two reading conventions used below:

- The map is presented as a list of **chains** (user-need →
  component → component → …), each chain annotated with each
  component's **evolutionary stage** in brackets:
  `G` genesis · `C` custom-built · `P` product (rentable) ·
  `Co` commodity (utility-grade).
- After the chains, a **moves** table records what the v2 effort is
  *actually doing* on the map: building, buying, or replacing.

## The map (as chains)

### Chain 1 — Direct & sense health

```
Augustus
  └─ Operator dashboard [C]                     ← custom: this is the product
       ├─ Graph renderer (React Flow) [P]
       ├─ Component library (Radix + Tailwind) [P]
       ├─ Browser runtime [Co]
       └─ Server-sent events [Co]
```

The dashboard *is* the product. Its rendering substrate (React Flow,
Radix, Tailwind) is product-grade OSS we rent without modifying.

### Chain 2 — Watch one agent think

```
Augustus
  └─ Operator dashboard [C]
       └─ Agent-trace surface [C]
            ├─ OpenLLMetry SDK [P]              ← OTel semantic conv for LLMs
            ├─ OTel collector [P]
            ├─ Trace store (Tempo / Jaeger) [P]
            └─ LLM provider (Claude API) [Co]
```

We *don't* write a tracing pipeline. We render someone else's traces.

### Chain 3 — Witness meetings

```
Augustus
  └─ Operator dashboard [C]
       └─ Council thread view [C]
            └─ Council aggregate (Postgres + JetStream stream) [P/Co]
                 ├─ NATS JetStream [P]
                 └─ Postgres [Co]
```

NATS JetStream gives durable, replayable streams; chat *is* the
stream. The "thread view" is a projection, not a separately written
store.

### Chain 4 — Issue a proclamation, see a placeholder

```
Augustus
  └─ Operator dashboard [C]
       └─ Proclamation surface [C]
            └─ Observer service [C]
                 └─ Postgres [Co]
```

The smallest custom thing — `POST /proclaim` writes a row, emits a
broadcast. Observer is the only place we write platform state.

### Chain 5 — A swarm of agents emerges

```
Augustus
  └─ Pods (one per service) [C]
       ├─ Code pods [C-arrangement of products]
       │    ├─ Per-pod Dockerfile (agent-authored) [C, per pod]
       │    ├─ Claude Code CLI [P]               ← agent backend
       │    ├─ MCP client (in Claude Code) [P]
       │    ├─ Auto-instrumentation (OTel, OpenLLMetry) [P]
       │    └─ Reload tooling per language (uvicorn / nodemon / air) [P]
       │
       └─ Adopted pods [C-arrangement]
            ├─ Main container: OSS image (postgres:16, qbittorrent, meilisearch …) [P or Co]
            └─ Sidecar: Claude Code + privileged exec on main [C]
```

The agent backend (Claude Code) is the most important rental. Service
substrate is whatever OSS image the agent picks. **We don't ship a
base image** — see [03-prototype-audit](03-prototype-audit.md) L3.

### Chain 6 — Pods coordinate

```
Pods
  └─ MCP surface (one or a few servers) [C]
       ├─ Senate (proposals + ballots) [C]
       │    └─ Postgres [Co]
       │
       ├─ Council/coms (meetings + DMs) [C]
       │    └─ NATS JetStream + Postgres [P/Co]
       │
       ├─ Decisions (sealed ADRs) [C]
       │    └─ Postgres + markdown rendering [Co + P]
       │
       └─ State (read model) [C]
            └─ Postgres (read replicas / views) [Co]
```

The MCP surface IS the custom contract. Its backings are commodity.

### Chain 7 — Real call edges

```
Pods (running services)
  └─ Service-to-service HTTP [Co]
       └─ Per-pod auto-instrumentation [P]
            └─ OTel collector [P]
                 └─ Trace store (Tempo / Jaeger) [P]
                      └─ Observer ingests spans [C]
```

We do *not* roll our own bus-tap call graph (v1 did, badly). OTel +
Tempo do this; observer just queries the trace store.

### Chain 8 — Pods come up, get a hostname

```
Spawn command
  └─ Container orchestrator [P]              ← Docker Compose (alpha)
       ├─ Compose profiles per pod [P]
       └─ Reverse proxy [P]                  ← Traefik
            └─ Hostname routing (pod-name.conclave.local) [P]
```

This replaces v1's host-side spawner script + port counter. **All
product, no custom orchestrator.**

### Chain 9 — Activity digest, block detection, deadline closing

```
Augustus's read models
  └─ Reactors (scheduled jobs) [C]
       ├─ Postgres rows + triggers [Co]
       └─ NATS JetStream consumers [P]
```

Tiny scheduled jobs (1 cron, a few stream consumers). Not their own
service — owned by the observer.

## Evolution: where things live and where they're moving

```
        Genesis    Custom    Product (rentable)         Commodity (utility)
        │          │         │                          │
        │          │         │                          │
        │       [Pod = agent + service]
        │          │         │                          │
[Pod renames itself]         │                          │
        │          │         │                          │
        │   [Operator dashboard]                        │
        │          │         │                          │
        │   [Senate / Council / Decisions logic]        │
        │          │         │                          │
        │          │   [React Flow]   [Radix]   [Tailwind]
        │          │   [Claude Code CLI]  [MCP]
        │          │   [OpenLLMetry]  [OTel]  [Tempo]
        │          │   [NATS JetStream]  [Traefik]
        │          │   [Compose profiles]
        │          │         │                  [Postgres]
        │          │         │                  [Docker]
        │          │         │                  [SSE / HTTP]
```

## Moves the v2 effort is making

| # | Move | From → To | Why |
|---|------|-----------|-----|
| 1 | Adopt OpenTelemetry | custom bus-tap → product OTel | call edges should be real, not synthesised. v1 hand-rolled this and it was wrong. |
| 2 | Adopt React Flow | custom SVG stage → product graph lib | v1's 1188-line Forum.tsx was a wall. React Flow is purpose-built. |
| 3 | Adopt Traefik | custom port counter → product reverse proxy | Pods get hostnames, not 8800+N ports. |
| 4 | Adopt Compose profiles | custom spawner script → product orchestrator | Compose already does on-demand pod start. |
| 5 | Adopt Postgres single-instance | 2× SQLite → product RDBMS | v1 spent days fighting locks. |
| 6 | Adopt NATS JetStream | custom message projection table → product durable stream | Chat *is* the stream; no separate store. |
| 7 | Adopt OpenLLMetry / Langfuse | nothing → product agent-trace store | v1 had no agent observability; bugs went hours unnoticed. |
| 8 | Adopt Claude Code | custom Pi transport patches → product CLI | Pi was structurally fragile; Claude Code has native MCP + real `--resume`. |
| 9 | Cut adapter slots from 9 to ~4 | 9 slots × ≥2 candidates (mostly unused) → just what's exercised | Pluggability emerges; it's not designed up-front. |
| 10 | Drop personas, exile/revival, skills | speculative features → removed from alpha | Built in v1, never used. |
| 11 | Drop CLI + frontend wizards | two bootstrap UIs → one bash command | Augustus doesn't bootstrap. Architect runs one command. |
| 12 | Pod ≠ image | one base image → agent picks per pod (code or adopted) | Massive widening of what conclave can manage. |

## What we're *not* moving (deliberate stillness)

| Component | Why it stays where it is |
|-----------|---------------------------|
| Senate + 4 voting strategies | Custom. *This* is the product. The platform's reason for existing. |
| Council aggregate | Custom. Augustus's J5 hangs on this being legible. |
| Operator dashboard | Custom. There's no OSS thing that does this. |
| Charter as markdown in repo | Already commodity-grade (git). Don't move. |
| Decisions as sealed records | Already commodity (Postgres rows). Don't move. |

## What this map says about resourcing

- **Build**: operator dashboard, senate logic, council aggregate,
  observer ingest, MCP surface, pod arrangement (code vs adopted).
  These are conclave's unique value.
- **Rent**: every dependency above. No tweaks to OSS internals.
- **Don't build twice**: anything we built in v1 that the OSS column
  now covers (call graph, message store, orchestrator, port mapping,
  database substrate) gets removed and re-rented.

The custom column is small. If it grows, we are repeating v1.
