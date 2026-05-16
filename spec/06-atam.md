# 06 — ATAM: Quality Attribute Trade-offs

**Tool**: ATAM (Architecture Tradeoff Analysis Method, SEI).
**Aim**: name the quality attributes that matter, write concrete
scenarios, score v1 against them, and document the v2 choices that
trade them against each other. This is where the spec set says *what
we are willing to give up*.

## The quality attributes that matter for v2

Listed in priority order. Each has at least one scenario in §2.

| # | QA | Why it matters for v2 |
|---|----|------------------------|
| QA1 | **Watchability** | The architect's #1 retro ask. If Augustus can't see what's happening, the platform's value collapses. The deliverable IS the watchability. |
| QA2 | **OSS-leverage** | Architect's "production-shaped, no quick-and-dirty, avoid custom stuff like hell." Custom code is a liability. |
| QA3 | **Pluggability** | The platform's structural promise (≥2 candidates per slot). v1 mostly skipped exercising this; v2 must keep abstractions honest. |
| QA4 | **Operability** | Augustus has to be able to bring the stack up and down, watch it, course-correct. No custom CLI beyond `docker compose --profile conclave up` (see [07-c4](07-c4.md) §Deployment view). |
| QA5 | **Many-agent scale** | ~6–10 pods comfortable. Senate strategies don't exercise with N=1. |
| QA6 | **Modifiability** | The architect needs to add a new strategy, a new pod kind, a new MCP tool without rewriting the world. |
| QA7 | **Robustness** | Pods crash, agents hang, OSS containers fail. Stack survives, restarts gracefully, doesn't lose project state. |
| QA8 | **Cost** | Augustus's plan / Claude usage shouldn't blow up. Model dial to Haiku / Sonnet-low-effort. |
| QA9 | **Performance** | Last-priority. The slow path is *agent thinking* (seconds–minutes); platform reactivity (<200 ms perceived) is plenty. |

Notably absent (deliberate, see [00-vision](00-vision.md) non-goals):
- **Security / auth / authz** — not in v2 alpha.
- **Multi-tenancy** — not in v2 alpha.
- **Hard SLAs / latency budgets** — see QA9.

## Scenarios (the testable form of each QA)

A scenario is *(source, stimulus, environment, artifact, response,
response measure)*. Compressed below.

### QA1 — Watchability

| ID | Scenario | Response measure |
|---|---|---|
| W1 | Augustus opens the Forum mid-run. He must be able to identify the live call edges between pods. | Within 5 s of opening: the graph view shows every pod that has made at least one call in the past 60 s, with the edge animated. |
| W2 | A pod has been "thinking" for 3 minutes. Augustus opens its drawer. | He sees the live token stream of the current turn, the current tool call (if any), and a "thinking since HH:MM" stamp. |
| W3 | A council is convened. Augustus opens it. | He sees all messages, in order, with sender names. New messages appear within 1 s of being posted. |
| W4 | A proposal is opened. Augustus sees the senate band. | The cartouche shows kind, summary, strategy, current ballots (per voter, with status), and deadline countdown. |
| W5 | Augustus has been away an hour. He opens the digest. | A grouped chronological digest of named events (admissions, decisions, deployments) is readable in under 60 s. |

### QA2 — OSS-leverage

| ID | Scenario | Response measure |
|---|---|---|
| O1 | The platform team needs HTTP call graphs between pods. | We rent OpenTelemetry + Tempo + an off-the-shelf collector. Custom code: the ingest reader (~one file) and the graph view (React Flow). |
| O2 | The platform team needs durable message replay for councils. | We use NATS JetStream streams + KV. No custom message store. |
| O3 | The platform team needs hostname-based routing for pods. | Traefik with file-mode dynamic config. No custom proxy. |
| O4 | The platform team needs an agent CLI with session resume. | Claude Code, as-is. No fork. |

### QA3 — Pluggability

| ID | Scenario | Response measure |
|---|---|---|
| P1 | The architect wants to swap NATS for Redis Streams. | A second adapter behind the same interface boots when the YAML config flips. No agent / dashboard code touched. |
| P2 | The architect wants to swap Postgres for a managed RDS. | Connection string in YAML; no schema rewrites. |
| P3 | The architect wants to swap Traefik for Caddy. | Re-implement the proxy adapter; everything else untouched. |

Note: per [03-prototype-audit](03-prototype-audit.md) L1, we don't
*build* the second adapter at alpha — only the interface, ready for
when a second arrives.

### QA4 — Operability

| ID | Scenario | Response measure |
|---|---|---|
| Op1 | Augustus wants to start the stack on a fresh machine. | `docker compose --profile conclave up` → operational stack in < 90 s post-cache. |
| Op2 | Augustus wants to stop the stack. | `docker compose down` → all conclave containers stopped, project state preserved. |
| Op3 | Augustus wants to wipe the project. | A documented two-command teardown that doesn't require deleting volumes by hand. |
| Op4 | Augustus discovers a pod stuck. | One click "restart pod" in the UI. |

### QA5 — Many-agent scale

| ID | Scenario | Response measure |
|---|---|---|
| MA1 | The Spotify demo spawns 8 pods. | All 8 boot within 60 s; UI graph renders without lag. |
| MA2 | A `consensus_omnium` vote with 5 affected voters runs. | All 5 are wakeable, ballots collected, proposal closes. |
| MA3 | A `sortition` vote draws 3 random voters from 8 admitted pods. | The draw is shown in the UI cartouche; only drawn voters are eligible. |

### QA6 — Modifiability

| ID | Scenario | Response measure |
|---|---|---|
| M1 | The architect adds a new voting strategy. | One file (strategy module) + one config entry. No senate-core changes. |
| M2 | The architect adds a new proposal kind. | One enum value + one optional payload schema. No UI rewrite. |
| M3 | The architect changes how charters are rendered. | One template + the agent CLI's system-prompt assembly. |

### QA7 — Robustness

| ID | Scenario | Response measure |
|---|---|---|
| R1 | A pod's container is killed. | Within 5 s: pod node turns red on the graph; activity ticker shows the event; pod survives a docker-start to return to its session. |
| R2 | The stack is restarted (`compose down` then `up`). | All admitted pods, decisions, proclamations, charters, agendas survive; agent sessions resume via Claude Code `--resume`. |
| R3 | A proposal's deadline passes. | Deadline reactor closes it per strategy. No "open forever" proposals. |
| R4 | A Postgres write fails (transient). | The bus event is retried; no state inconsistency between read-models and the source-of-truth tables. |

### QA8 — Cost

| ID | Scenario | Response measure |
|---|---|---|
| C1 | An hour-long demo uses agents whose work doesn't need to be beautiful. | Pods run with Haiku or Sonnet-low-effort if dialed down. The platform exposes the dial per pod. |
| C2 | An agent gets into a tool-call loop. | Per-pod token budget triggers a "stuck" event and pauses the pod (J9). |

### QA9 — Performance

| ID | Scenario | Response measure |
|---|---|---|
| Pf1 | An OTel span emits on a pod-to-pod call. | Visible on the call-graph within 2 s. (No tighter SLA — agent thinking dominates.) |

## Tradeoff matrix (where attributes pull against each other)

| Tradeoff | One side | Other side | v2 choice | Why |
|---|---|---|---|---|
| **T1** Postgres vs SQLite | Postgres heavier dev footprint | SQLite simpler local | Postgres | QA7 (robustness, no lock contention) and QA2 (production-shaped) win over local-footprint comfort. v1 paid for the wrong choice for days. |
| **T2** OTel everywhere vs custom bus-tap | OTel adds collector + Tempo to the stack | Custom is lighter | OTel | QA1 (watchability — real call edges) and QA2 (OSS) trump operational footprint. The custom v1 approach was wrong. |
| **T3** React Flow vs hand-rolled SVG | React Flow constrains visual style | SVG max freedom | React Flow | QA6 (modifiability) and QA2 win. We can theme React Flow custom nodes; we can't rebuild 1188 lines per UI change. |
| **T4** ≥2 candidates per slot upfront vs build-when-needed | Pre-built proves the abstraction | Pre-built is dead code | Build-when-needed (lean) | QA2 + QA6. v1's 18 unused adapters were a liability. Keep the *interface* tidy; ship the *second* implementation when real demand shows. |
| **T5** Adopted pods (sidecar with root) vs code-only pods | Adopted pods are more powerful, but the sidecar has privileges | Code-only is simpler, less power | Both | QA1, QA5 win. The Spotify demo benefits from adopting `postgres:16` for catalog data instead of agents writing a fragile DB. Sidecar privileges are scoped to the main container only — not a network-wide concern. |
| **T6** Claude Code CLI vs in-process Agent SDK | CLI brings subprocess pain, but ships now | SDK is in-process, more visibility but more glue | CLI (architect's call) | QA2 (rent the CLI), QA8 (model dial available). Subprocess pain is real but bounded — see [03-prototype-audit](03-prototype-audit.md) L6. |
| **T7** Many MCP servers (one per CRUD slice) vs few (one per context) | More servers = clearer boundaries | More servers = more processes, more wiring | Few (one per bounded context) | QA6 (modifiability), QA2 (less custom). [05-ddd-contexts](05-ddd-contexts.md) lands on 6 servers. |
| **T8** Wizard UI vs zero-config bash | Wizard is friendlier but is a UI to maintain | Bash is brutal but fast | Zero-config bash, wizard deferred | QA4 for the architect; Augustus rarely bootstraps. Wizard returns later. |
| **T9** Hard latency SLAs vs none | SLAs force responsiveness but become theatre | No SLA means quiet regressions | None for v2 | QA9 deprioritised; the slow path is agent thinking. v1's p95 = 1.8 ms measurement was theatre. |

## Sensitivities (single decisions that make or break a QA)

A "sensitivity point" is one architectural decision that, if changed,
breaks an entire quality attribute.

- **S1 — OTel auto-instrumentation in every pod**: if we don't bake
  this into the pod template, QA1 (watchability) collapses to "see
  pods, not see what they do."
- **S2 — Single Postgres**: if we revert to SQLite, QA7 (robustness)
  fails again with lock contention.
- **S3 — Adopted-pod sidecar pattern**: if pods are forced to be code,
  QA5 (many-agent scale demonstrations) becomes harder — agents must
  reimplement what OSS images already do.
- **S4 — Senate exposes strategies as a user surface**: if strategies
  are hidden behind config, QA8 (cost) and the whole platform-as-
  test-bed framing dies.
- **S5 — Charter read on every wake** (not flag-baked at spawn): if
  edits force a respawn, QA4 (operability) regresses and J7 (course-
  correct) breaks.

## Risks (things that could still go wrong despite the trade-offs)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Claude Code CLI changes its session format mid-development | Medium | High | ACL in AgentExecution context ([05-ddd-contexts](05-ddd-contexts.md)). |
| OTel auto-instrumentation produces too much noise | Medium | Medium | Per-pod sampling config; UI throttles call edges by recency. |
| Adopted-pod sidecar permission model is misconfigured (agent escapes scope) | Medium | High | Mount only the main container's docker socket / API; do not mount the host docker socket. Audit per-pod. |
| Augustus DMs become a backdoor for "I'll just tell `frontend` to do everything" | Medium | Medium | DM is rate-limited / acknowledged; behaviour visible on the timeline. Augustus seeing his own override pattern is itself a feature. |
| Many-pod scale exposes JetStream throughput limits | Low | Medium | Stream config sized for ~50 pods; if hit, swap candidate adapter behind the same interface. |
| The pod template becomes a god-component | Medium | Medium | Code pods and adopted pods are separately templated; no shared bloat. |

## What this spec says about future ATAM rounds

ATAM is iterative. Re-run when:

- A new QA emerges (e.g. security, when multi-tenant comes back into
  scope).
- A sensitivity point is challenged (e.g. someone proposes ditching
  OTel).
- A risk hits (e.g. Claude Code changes session format).
