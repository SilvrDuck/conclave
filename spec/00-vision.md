# Conclave v2 — Vision

**Status**: authoritative for v2. North star above all sibling specs.

## What conclave is

Conclave is a **consensus-driven, orchestrator-free platform for building
microservice projects with autonomous AI agents** — and, equally, a
tool for **seeing precisely what those agents are doing**: their
debates, their dissent, the personality that surfaces in their
decisions. The platform stays general-purpose; *the demos* (Spotify
clone, design Uber, …) are validation scenarios, never something the
platform's design caters to.

> v2's deliverable is the **platform**, not whichever app the swarm
> builds. The validation scenarios are exercise weight, not the
> product.
>
> The product is the platform **and** the visibility it gives an
> architect into the swarm. Personality expressed in agent
> decisions — quoted council messages, dissenting votes, charter
> rewrites — is core surface area, not flavour text.

The mental model from v1 carries over and gets sharpened:

- A pod = one agent + the one service it manages, end-to-end.
- The agent is the only intelligence; the platform is dumb infrastructure
  that records and connects.
- Every cross-pod decision goes through the senate (or a council), with
  pluggable voting strategies. The senate exists **for the user to test
  collective-intelligence rules under realistic conditions** — that is
  the platform's whole point.
- The user (Augustus) sets the horizon via proclamations; nobody else
  decides anything in their name.

## What changes for v2 (deltas from v1)

These are the load-bearing reframings. Each gets a fuller treatment in
[03-prototype-audit](03-prototype-audit.md) and downstream specs.

1. **A pod is not bound to a base image.** It is an agent managing a
   service. The service can be **custom code the agent writes** (agent
   and code share one container, like v1) **or an off-the-shelf OSS
   image the agent adopts** (`linuxserver/qbittorrent`, `postgres:16`,
   `meilisearch`, …). For adopted services, the agent runs as a
   **privileged sidecar** with root on the main container — full
   operational authority. The agent can also *change its image* later
   (re-adopt a different stack) by cloning its identity into a new pod.

2. **Many agents, not few.** v1's senate didn't fire interestingly
   because there were never more than 2 voters. v2 must comfortably run
   ~6–10 pods so the four voting strategies actually exercise
   themselves. Spawning a pod must be cheap and reliable.

3. **The forum is a live architecture diagram, not a tableau.** Pods
   are services on a graph; edges are real OpenTelemetry-recorded HTTP
   calls; infra (DB, cache, bus) shows up as distinct nodes. Click any
   entity → see its neighbours, recurse. The UI itself is a navigable
   knowledge graph of the running system.

4. **Inter-agent meetings are first-class.** Councils, chatrooms, DMs
   are visible and readable in the UI as they happen. Decisions made
   together leave minutes. v1 had the bus but no surface for the
   conversation; v2 makes the conversation the headline.

5. **OSS over custom code, everywhere.** v1 hand-rolled too much
   (Forum.tsx at 1188 lines, pod_spawner.py polling docker ps, custom
   bus tap projecting to a custom table, two SQLite DBs fighting for
   locks). v2 picks the best OSS substrate at every layer and writes
   only the glue. Specific calls in [04-wardley](04-wardley.md).

6. **Production-shaped, not "quick and dirty".** Architect's words.
   No "fix later" defaults: single Postgres, real reverse proxy with
   hostname routing, real OTel pipeline, real agent-observability.

## Principles (carried from v1, still load-bearing)

- **Symmetry** — bootstrap is a vote, completion is a vote, contract
  changes produce ADRs, member removal is a vote. No special code paths
  anywhere. First pod = first member, not "founder forever."
- **One agent, one service** — a pod and its service are inseparable.
  No service has two owning agents; no agent owns two services. New
  service = new pod, proposed.
- **Observed truth over declared truth** — call graph from real OTel
  spans, not from hand-authored manifests. Service liveness from the
  container runtime, not from agent self-reports.
- **MCP as the agent-platform contract** — every agent-platform
  interaction is an MCP tool call. No custom shell primitives.
- **Pluggability at every external boundary** — each slot (bus, store,
  CLI, runtime, traces, …) is an adapter; alpha ships ≥2 candidates per
  slot so the abstraction is real, not theoretical. v1 mostly skipped
  this; v2 won't.
- **Stateless platform, stateful project** — runtime owns no durable
  data. Project state lives in monorepo + the configured doc backend.
- **Existing tooling over custom code.**

## Non-goals (v2)

- Auth / authz inside the platform.
- Cost governance beyond user budgets.
- Cross-pod integration tests as a platform feature.
- Live mid-flight stack swaps.
- Multi-tenant conclave.
- A polished scenario front-end (Spotify clone, Uber clone, …).
  We need each scenario to come up and exercise the platform; we
  don't need it to be beautiful.

## The v2 acceptance shape

Detailed criteria in [08-v2-acceptance](08-v2-acceptance.md). One-line
summary: the architect issues a feature-shaped proclamation (e.g.
"design Uber — riders, drivers, surge, one pod simulates the real
world"); a small swarm of agents discovers the service split,
debates it visibly in councils, ships a working multi-service
deployment, and Augustus can read the meeting minutes, see the live
call graph, click any node to traverse its neighbours, and try the
app. v2 ships only when the **realize → analyze → nuke** loop (§14
of 08) closes with zero platform-gap tasks filed in the analyze
phase.

If the architect at any point goes "I cannot tell what's happening" or
"why is this still custom code" — v2 isn't done.

## How to read these specs

| File | Purpose |
|------|---------|
| [00-vision](00-vision.md) | This file. North star. |
| [01-jtbd](01-jtbd.md) | Personas + jobs-to-be-done. What outcomes matter. |
| [02-event-storming](02-event-storming.md) | Domain timeline: events, commands, policies. |
| [03-prototype-audit](03-prototype-audit.md) | v1 lessons. keep / change / remove / unknown. |
| [04-wardley](04-wardley.md) | Component map. Core vs commodity vs replaceable. |
| [05-ddd-contexts](05-ddd-contexts.md) | Bounded contexts and aggregates. |
| [06-atam](06-atam.md) | Quality attribute trade-offs. |
| [07-c4](07-c4.md) | Target architecture: context → container → component. |
| [08-v2-acceptance](08-v2-acceptance.md) | What "done" looks like. |
| [archive/](archive/) | v1 specs, preserved for reference. Authoritative for v1 only. |

In conflicts: 00 wins over 08 wins over 07 ↔ 05 ↔ 06 ↔ 04 ↔ 02 ↔ 01 ↔ 03.
Archive is never authoritative.
