# 03 — Prototype Audit (lessons from v1)

**Tool**: Prototype Feature Audit (keep / change / remove / unknown).
**Aim**: extract every architectural and functional lesson v1 taught
us, so v2 starts on a clean branch *with the lessons but without the
code*.

> Ground rule: **no code snippets, no file paths to copy from.** Only
> architectural / functional learnings. Anything that would steer v2's
> code-shape back toward v1's is excluded by design.

The audit is grouped by subsystem. Each row uses one of:

- **KEEP** — the *idea* survives, even if the implementation must
  be re-done with OSS.
- **CHANGE** — the idea survives but the shape must shift in a stated
  direction.
- **REMOVE** — drop entirely, including from the spec set.
- **UNKNOWN** — still uncertain; needs a downstream decision.

---

## Architecture-wide lessons (read these before the table)

These are the meta-lessons. If v2 violates them, we are repeating
v1's mistakes.

### L1 — "Generic" abstractions you build once aren't generic

v1 created 9 adapter slots (bus / cli / docs / runtime / trace / log /
notify / repo / ci), each with ≥2 candidates. We *implemented* most
of the candidates and *exercised* almost none of them. The result was
extra interfaces that constrained the actually-used implementation
while never being swapped in anger. **Lesson**: pluggability is an
*output* of having shipped two implementations driven by real demand,
not an input. Pick the best OSS for each slot at v2 alpha; design the
adapter only when a second implementation actually arrives.

### L2 — Hand-rolled coordinators are the wrong size for this

The v1 spawner was a host-side script polling docker ps every few
seconds and watching the bus, with manual port allocation. The
observer was a custom projection of NATS taps into a SQLite cache.
Both reimplemented things OSS already does well: container
orchestration, message-stream replay, time-series projection. v2's
budget for coordinator code is "the glue between OSS components", not
"the coordinator."

### L3 — A pod is not a base image

v1 baked Python+ffmpeg+a workspace-runner into the pod image so every
pod had to be a Python service. The architect's v2 reframing: a pod
is *an agent managing a service*, where the service may be code-the-
agent-wrote (same container) or an OSS image-the-agent-adopted
(sidecar with root). This widens conclave from "Python microservice
demo" to "the agent picks the right tool — Postgres, qbittorrent,
meilisearch, whatever — and wears the manager's hat on it." Every v1
file in `infra/pod-skills/` etc. should be reconsidered in this light.

### L4 — The senate's job is to be tested, not to be lean

v1 trimmed the senate toward "lean / trivial passes" because most
proposals had one voter. That was treating the symptom (few voters)
not the cause (few pods). v2 must run with enough pods that all four
strategies fire interestingly. The senate is the platform's whole
point — it exists to let Augustus *play* with collective-intelligence
rules. Anything that demotes the senate is a regression.

### L5 — The platform must be watchable

v1 had decent state APIs but no live agent transcript, no real call
graph, no meeting transcripts in the UI. The retro made this the #1
ask. v2's quality is measured not by what the agents produce but by
how legible their work is to a human watching them. **Watchability is
a feature, not polish.**

### L6 — Pi-as-CLI was structurally fragile

A subprocess speaking newline-delimited JSON over stdio has known
failure modes (oversized lines, half-flushed writes, "agent busy" on
concurrent prompts, charter only via spawn-time flag). v1 hit all of
them. v2 stays with Claude Code as the CLI (architect's call) so the
JSON-RPC transport pain partly returns — but with a CLI that's
actively maintained, native MCP support, real `--resume`, and a
streaming API. Harden the transport once, properly, and don't paper
over silent-death modes.

### L7 — "Quick and dirty" defaults cost more than they save

v1 chose SQLite to skip Postgres. We then spent days fighting locks
and patching with WAL + busy_timeout + asyncio.Lock. v2 starts with
the production substrate (Postgres) so the cost is paid once.

### L8 — Naming has a maintenance cost

Tabularium, iusiurandum, S·P·Q·R, decree — each Latin term we shipped
became friction. Some Roman names landed (Forum, Senate, Council);
many didn't. The lesson is "theme through visuals, prune vocabulary
that's harder than what it labels."

---

## The audit table

### Domain & governance

| v1 thing | Verdict | Lesson / direction for v2 |
|---|---|---|
| Proclamation (Augustus's word) | KEEP | Stays as the operator's primary verb. v2 numbers them by sequence, archives them with their derived decisions. |
| Senate (formal proposals + ballots + strategies + sealed decisions) | KEEP | This is the platform's whole point. Push for many pods so all four strategies fire. |
| Four voting strategies (majority, supermajority, consensus_omnium, sortition) | KEEP | First-class. Strategy choice is part of the experiment, not an implementation detail. |
| Sealed ADR per closed proposal | KEEP | Decision audit trail. Rename the surface ("decisions") but the artifact stays. |
| Clay → stone ADR placeholder | CHANGE | The placeholder gave instant feedback, *but* it became "empty tablets nobody sealed." v2 only creates a placeholder when a closing action is committed (e.g. a council convened to design X). Otherwise no placeholder until there's a real proposal. |
| Council / chatroom (named multi-agent threads) | KEEP | First-class meeting object. v2 puts these on the UI as readable threads, not as "lines on a stage." |
| Direct messages (DM) | CHANGE | Was an afterthought. v2 models a DM as a 2-party council, same aggregate, with a `private=true` flag. |
| Exile (proposing to remove a pod) | CHANGE | Kept but never used in v1's demo. v2 keeps the *idea* (so the senate can fire on it for testing), but ships only when a real demo path uses it. |
| Revival (bringing back an exiled pod) | REMOVE | Not exercised; speculative. Defer to a later version. |
| Personas (Cicero / Cato / etc.) | REMOVE | Cute, built, never used in earnest. Cut from v2 alpha. |
| Founder as a privileged role | REMOVE | First pod = first member, no special bootstrap path. It renames itself per its mandate (e.g. `frontend`). |

### Agent / pod model

| v1 thing | Verdict | Lesson / direction for v2 |
|---|---|---|
| One agent, one service | KEEP | Strongest principle from v1. Don't dilute. |
| Pod base image with Python + ffmpeg baked in | REMOVE | The agent picks the right image. See L3. |
| `pods/<self>/workspace/` as the service code | CHANGE | Keep for *code pods*. For *adopted pods*, the workspace is the configuration / volume binding to the adopted image, not the code. |
| Workspace runner sidecar (watches `server.py`/`main.py`/`app.py`) | REMOVE | Replaced by per-pod Dockerfile + standard reload tooling (`uvicorn --reload`, `nodemon`, `air` for Go). The agent picks. |
| Agent renames itself on role assignment | CHANGE | New: stable pod-id + mutable display-role. Renames are events on the activity feed. |
| Charter as a markdown file in the pod | KEEP | The agent's system prompt lives in repo, versioned, editable. |
| Charter delivered via spawn-time flag | REMOVE | Charter is read by the agent from disk on every wake; edits don't require respawn. |
| Iusiurandum (founder oath) at the repo root | CHANGE | The *content* of the oath (priorities, agility rules) becomes part of every pod's *system prompt assembly*, not a separate file with Latin in the name. |
| Agenda (`doing` / `next` / `blocked_on`) | UNKNOWN | The idea is right (peers see what you're up to). v1 baked it into a markdown file nobody updated. v2 needs to ask: does the agent maintain this in a tool the platform reads, or is it inferred from the agent's recent token stream? Defer to [05-ddd-contexts](05-ddd-contexts.md). |
| Adopted-image pods (e.g. Postgres, qbittorrent) | NEW | Major v2 addition. See L3. Agent in sidecar with privileged access on the main container. |
| Skills / shared/skills directories | REMOVE | Never exercised. Defer until needed. |

### Platform services

| v1 thing | Verdict | Lesson / direction for v2 |
|---|---|---|
| Four separate MCP servers (coms / senate / decisions / state) | CHANGE | Each was a thin FastAPI wrapper over an HTTP call. v2 collapses to fewer MCP surfaces (probably one per bounded context — see [05-ddd-contexts](05-ddd-contexts.md)). One MCP server per *aggregate cluster*, not one per CRUD slice. |
| Observer service (the read-model writer) | KEEP | The role is right. v2 implementation leans on Postgres + LISTEN/NOTIFY + JetStream consumers rather than a custom projection engine. |
| Senate ledger (proposal+ballot store) | KEEP | The role is right; collapsed into the same Postgres instance. |
| Two separate SQLite databases | REMOVE | Single Postgres, per-service schemas. See L7. |
| Bus tap into a custom messages table | REMOVE | Replaced by NATS JetStream durable streams — the chat *is* the stream. |
| Spawner (host-side Python polling docker ps) | REMOVE | Replaced by Docker Compose profiles + Traefik for routing (orchestration plug-and-play; see [04-wardley](04-wardley.md)). |
| Per-pod host port mapping by counter (8800/8801/…) | REMOVE | Replaced by Traefik hostname-based routing (`frontend.conclave.local` etc.). |
| Per-pod live token stream surface | NEW | Required by J4 (witness one agent thinking). Backed by the agent-observability stack ([04-wardley](04-wardley.md)). |
| Call-graph from a bus tap on a fake `coms.send` event | REMOVE | Replaced by OpenTelemetry auto-instrumentation in every pod. Real call edges, not synthesised. |
| Reactivity measurement (T3, p95 < 2s) | REMOVE | Optimisation theatre — the slow path is agent thinking time, not transport. Don't ship a budget unless we'll act on it. |

### UI

| v1 thing | Verdict | Lesson / direction for v2 |
|---|---|---|
| Tab structure (Forum / Senate / Tabularium / Council / Wizard) | REMOVE | Tabs named after backend modules. Replaced by four *job-shaped perspectives*: Glance / Witness / Try / Direct. |
| Hand-rolled SVG stage (pods as marble figures) | REMOVE | 1188-line component. Replaced by React Flow for the graph + Tailwind/Radix for everything else. |
| Pod sprite art (clay vs stone, gold halo, …) | CHANGE | Visual cues for state survive but on React-Flow custom-node renderers, not bespoke SVG. |
| Activity ticker on the side | KEEP | Useful in glance perspective. Same data, lighter component. |
| Charter editor as a textarea | CHANGE | Pre-loads current charter; shows diff before commit. |
| Exile district as its own view | REMOVE | Folded into the per-pod drawer. Exiled pods move to a tray, don't get their own page. |
| First-run wizard view | REMOVE | Bootstrap is zero-config (`docker compose --profile conclave up` — see [07-c4](07-c4.md) §Deployment view). Wizard returns later if needed. |
| Interconnection / click-through-the-graph | NEW | Required. Every entity in the UI is a clickable node that reaches its neighbours. |
| Live token stream view in pod drawer | NEW | See J4. |
| Council / meeting thread view | NEW | See J5. |
| Apps launcher | NEW | See J6. |
| DM pod from UI | NEW | See J7. |
| Stuck tray | NEW | See J9. |

### Infrastructure / OSS substrate

| v1 thing | Verdict | Lesson / direction for v2 |
|---|---|---|
| NATS as the bus | KEEP | v2 uses NATS JetStream (durable streams, replay, KV) so the bus *is* the chat store. No custom projection. |
| FastAPI for the platform services | KEEP | Sensible default. |
| Pydantic models | KEEP | |
| SWR for the frontend data | KEEP | |
| Zod for runtime parsing | KEEP | |
| Vite + React | KEEP | |
| Tailwind | NEW | Wasn't in v1. v2 baseline. |
| Radix primitives | NEW | Wasn't in v1. v2 baseline for drawers, dialogs, dropdowns, tabs. |
| React Flow | NEW | Graph rendering. |
| OpenTelemetry (auto-instrumented in every pod) | NEW | Call edges, latencies, error spans. |
| OpenLLMetry (OTel semantic conventions for LLM calls) | NEW | Token streams, tool calls, prompt versions. Same OTel pipeline as HTTP traces. |
| Postgres single instance | NEW | Replaces v1's SQLite-x2. Per-service schemas. |
| Docker Compose + Traefik | NEW | Replaces v1's custom spawner. Compose profiles for opt-in pods; Traefik for hostname routing. |
| Claude Code CLI as agent backend | CHANGE | Replaces Pi v1. Same subprocess shape but maintained transport. |
| Loki / stdout logging | KEEP (loose) | Either works for v2 alpha; OTel logs is also fine via the same collector. |
| Obsidian / GitHub Issues for docs | CHANGE | Decisions go into the same Postgres + a markdown rendering pipeline. GH Issues mirror as a later candidate. |

### Tests / dev workflow

| v1 thing | Verdict | Lesson / direction for v2 |
|---|---|---|
| Pytest unit tests per adapter | KEEP | Pattern is right. |
| `test_e2e_in_process.py` | KEEP | In-process e2e is the right shape. |
| Smoke tests directory | UNKNOWN | Was empty in v1. Either delete or fill. |
| `measure_reactivity.py` | REMOVE | Optimisation theatre, see above. |
| Playwright MCP-driven UI verification | KEEP | Worked well for v1 acceptance. Same pattern for v2. |

### Bootstrap & ops

| v1 thing | Verdict | Lesson / direction for v2 |
|---|---|---|
| `kickstart.sh` zero-config bash | REMOVE | v2 entry point is `docker compose --profile conclave up` (see L6 — Pi-as-CLI was structurally fragile; no script intermediary). |
| CLI wizard (`conclave-wizard`) | REMOVE for v2 alpha | Brings back as a polish item in a later version. Not in the alpha scope. |
| Frontend wizard view | REMOVE | See L8 / J-anti. The wizard has no place on a running instance. |
| `infra/compose.yaml` as the canonical IaC | CHANGE | Stays the format. Platform services live behind the `conclave` profile; each pod is its own `pod-<role>` profile spun up on demand by the pods MCP-server. |

---

## v2 hard-won lessons (the "if you forget anything, remember these")

1. **OSS first.** Every layer where an OSS substrate exists, we use it.
2. **Many pods, or no senate to test.** Plan for ~6–10 pods in the
   Spotify demo, not 2.
3. **Pod ≠ image.** Agent picks the service shape; code or adopted.
4. **Watchability is the deliverable.** Live token streams, meeting
   minutes, call graph, all visible.
5. **Real Postgres, real reverse proxy, real OTel.** No quick-and-dirty
   substitutes.
6. **The conversation is the headline.** Not the ballot, not the ADR
   text — the *meeting* leading to the ADR.
7. **Prune Latin.** Forum / Senate / Council / Augustus stay.
   Tabularium / iusiurandum / S·P·Q·R / decree go.
8. **The first pod renames itself.** No permanent "founder."
9. **Don't ship a budget you won't enforce.** Reactivity p95 was
   theatre.
10. **Don't pre-build slot-2 adapters.** Build slot-1 well; slot-2
    arrives when a real demand does.
