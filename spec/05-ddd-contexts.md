# 05 — Domain-Driven Design: bounded contexts & aggregates

**Tool**: DDD Strategic Design.
**Aim**: name the bounded contexts, the aggregates inside each, the
ubiquitous language, and the relationships between contexts.

Events come from [02-event-storming](02-event-storming.md). JTBDs from
[01-jtbd](01-jtbd.md). Where this spec calls out a hot-spot
("🟥 see ES"), follow the link back to that map.

---

## Ubiquitous language

Standardised across UI, code, MCP tool names, prompts, ADRs. Pruned
per [03-prototype-audit](03-prototype-audit.md) L8.

| Term | Meaning | What it replaces |
|------|---------|------------------|
| **Forum** | The operator dashboard. | (kept from v1) |
| **Augustus** | The human operator persona. | (kept from v1) |
| **Pod** | One agent + the one service it manages, end-to-end. | (kept from v1) |
| **Code pod** | A pod whose service is code the agent wrote. | new |
| **Adopted pod** | A pod whose service is an OSS image; the agent runs as a privileged sidecar. | new |
| **Service** | The thing a pod manages (HTTP API, DB, queue, …). | (kept from v1) |
| **Charter** | The agent's role definition + system-prompt content. | (kept from v1) |
| **Proclamation** | Augustus's high-level direction. Numbered (I, II, …). | (kept from v1) |
| **Direction** | A pod's currently-active goal (proclamation or council outcome). | new (replaces "mandate") |
| **Senate** | The governance context. Holds proposals + ballots. | (kept) |
| **Proposal** | A request for a collective decision. Has a *kind* and a *strategy*. | (kept) |
| **Ballot** | One agent's vote on one proposal. | (kept) |
| **Strategy** | The rule by which ballots resolve to an outcome. Four built-ins. | (kept) |
| **Council** | A named multi-agent thread. May be private (DM-shaped). | (kept) |
| **Message** | An entry in a council. | new (replaces "chatroom message") |
| **Decision** | The sealed record of a proposal outcome or a council closure. Was "ADR" in v1. | replaces "ADR" / "Tabularium" |
| **Endpoint** | An observed HTTP route on a pod's service. | (kept) |
| **Annotation** | A pod-authored description of one of its endpoints. | (kept) |
| **Call** | An observed HTTP request from one pod to another (from OTel). | new (replaces "caller graph") |
| **Operator** | Augustus's plane-B role. | new (replaces "user") |
| **Architect** | The plane-A persona designing conclave. Never appears in the runtime. | new |

Removed: `Tabularium`, `iusiurandum`, `S·P·Q·R`, `decree`, `mandate`,
`exile district`, `founder` (as a permanent role).

---

## Bounded contexts

Conclave decomposes into **seven** bounded contexts. Each has its own
ubiquitous language, one or more aggregates, and well-defined inbound
events / outbound commands.

```
                        ┌────────────────────────────┐
                        │       OPERATOR             │
                        │   (Forum + read APIs)      │
                        └──────┬─────────────────────┘
                               │ reads
            ┌──────────────────┼──────────────────────┐
            │                  │                      │
            ▼                  ▼                      ▼
   ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │   SENATE        │  │   COUNCIL        │  │   OBSERVATION    │
   │  proposals &    │  │  meetings, DMs,  │  │  call graph,     │
   │  ballots        │  │  messages        │  │  endpoints,      │
   │                 │  │                  │  │  pod health      │
   └──────┬──────────┘  └────────┬─────────┘  └──────────────────┘
          │                      │                      ▲
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                                 ▼
                       ┌──────────────────────┐
                       │   DECISIONS          │
                       │  sealed records      │
                       └──────────────────────┘
                                 │
                                 │ governs
                                 ▼
                       ┌──────────────────────┐
                       │   POD LIFECYCLE      │
                       │  spawn, image, role  │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │   AGENT EXECUTION    │
                       │  charter, prompts,   │
                       │  agent trace         │
                       └──────────────────────┘
```

### C1 — Operator

The Augustus-facing context. Holds the proclamation queue, the
operator's DMs, and the read-models for the four perspectives.

| Aggregate | Identity | Invariants |
|---|---|---|
| **Proclamation** | `proclamation_seq` (monotonic) | Text is immutable. Has a status (open / completed). Tied to a derived placeholder decision when applicable. |
| **OperatorInbox** | Augustus singleton | Holds pending votes (J8), nudge requests, stuck-tray entries. |

Inbound: `IssueProclamation`, `SendDirectMessage`, `EditCharter`,
`CastBallot` (for the rare imperial vote).
Outbound: `ProclamationIssued`, `DirectMessageFromUser`, `CharterEdited`.

### C2 — Senate

Holds the proposals, ballots, and the strategy-evaluation logic.
This is **the platform's whole point** — the test surface for
collective-intelligence rules.

| Aggregate | Identity | Invariants |
|---|---|---|
| **Proposal** | `proposal_id` | Has exactly one kind, one strategy, one proposer, one set of eligible voters (computed at open time), one deadline. Outcome is `open` until the strategy returns a concrete value. |
| **Ballot** | (`proposal_id`, `voter`) | A voter has at most one ballot per proposal. Ballots are immutable once cast. |
| **Strategy** | name | Pure function `(ballots, eligible, context) → outcome \| open`. Four built-ins (majority / supermajority / consensus_omnium / sortition); plug-in shape (see [04-wardley](04-wardley.md) chain 6). |

Inbound: `ProposeAdmission`, `ProposeExile`, `ProposeContractChange`,
`ProposeCompletion`, `CastBallot`, `TickDeadline` (from a reactor).
Outbound: `ProposalOpened`, `BallotCast`, `ProposalClosed(outcome)`.

🟥 (from ES) — N=1 trivial pass is the strategy returning approved when
the proposer is the only eligible voter. **No special-case code path.**

🟥 (from ES) — Deadline closer reactor closes any open proposal whose
deadline has elapsed, per the strategy's timeout policy (default:
treat absent voters as abstain, apply quorum).

### C3 — Council (meetings + DMs)

Multi-agent threads. DMs are the private 2-party degenerate case.

| Aggregate | Identity | Invariants |
|---|---|---|
| **Council** | `council_id` | Has a topic, a participants list, a private flag, an open/closed status, a closing summary (when closed). |
| **Message** | (`council_id`, `seq`) | Append-only within a council. Sender is one of the participants OR Augustus (for DMs to a pod). |

Inbound: `ConveneCouncil`, `PostMessage`, `CloseCouncil`.
Outbound: `CouncilOpened`, `MessagePosted`, `CouncilClosed(summary)`.

🟥 (from ES) — Augustus posts only in 1-on-1 councils (DMs). Public
councils are read-only for him.

### C4 — Decisions

Sealed records. The audit trail.

| Aggregate | Identity | Invariants |
|---|---|---|
| **Decision** | `decision_id` (`adr-NNNN` for legacy) | Has a title, body, affected pods, an originating reference (one of: proposal, council, proclamation), a status (placeholder / sealed), a sealed-at timestamp once sealed. Body must be non-empty when sealed. |

Inbound: `CreatePlaceholder`, `SealDecision(body)`.
Outbound: `DecisionPlaceholderCreated`, `DecisionSealed`.

🟥 — Sealing rejects empty / template bodies. v1 had empty stone
tablets; v2 enforces a non-trivial body invariant.

### C5 — Observation

The read-model writer. The only context that *writes* state about
"what is happening" — everyone else reads.

| Aggregate | Identity | Invariants |
|---|---|---|
| **PodState** | `pod_id` | Last known runtime status (running / stopped / not-yet-spawned), last agent state (thinking / idle / blocked-for), display role, container info. Updated only by reactors / OTel ingest, never by agents directly. |
| **Endpoint** | (`pod_id`, `method`, `path`) | Captured by OTel ingest. Has an optional annotation (pod-authored). |
| **Call** | id | A single observed call: src pod, dst pod, endpoint, latency, status, time. Derived from OTel spans. |
| **AgentTrace** | (`pod_id`, `turn_id`) | Live token stream + tool calls for one agent turn. Owned by the OpenLLMetry-backed store. |

Inbound: `IngestOTelSpan`, `RegisterPod`, `PodHealthChanged`.
Outbound: `EndpointObserved`, `CallObserved`, `PodMarkedStuck`.

### C6 — Pod Lifecycle

Spawning, naming, image management.

| Aggregate | Identity | Invariants |
|---|---|---|
| **Pod** | `pod_id` (stable) | Has a mutable `display_role`. Has an `image_strategy` (`code` or `adopted`). Code pods have a per-pod Dockerfile; adopted pods reference an OSS image + sidecar mount specs. A pod can change its image-strategy via a senate proposal (kind: `image_swap`). |
| **Spawn** | `spawn_id` | A single attempt to bring a pod up. Records inputs (image, sidecar, network) and outcomes (running, failed, retry-count). |

Inbound: `SpawnPod`, `AdmitPod`, `ExilePod`, `RenamePod`, `SwapPodImage`.
Outbound: `PodContainerStarted`, `PodAdmitted`, `PodExited`,
`PodRenamed`, `PodImageSwapped`.

🟥 (from ES) — The adopted-pod sidecar pattern lives entirely in this
context. The main container (the OSS image) and the sidecar (the
agent) are part of one `Pod` aggregate.

🟥 — Rename: stable id stays; `display_role` is mutated and the change
is an event on the activity feed.

### C7 — Agent Execution

The agent's per-pod execution context: charter, system-prompt
assembly, model selection, agent trace.

| Aggregate | Identity | Invariants |
|---|---|---|
| **Charter** | `pod_id` (singleton per pod) | Versioned markdown. Reads from disk on every wake. Edits produce a `CharterEdited` event + a new version. |
| **AgentSession** | (`pod_id`, `session_id`) | The CLI agent's session (Claude Code's `--resume`-able session). Maps 1:1 to one pod's identity. |

Inbound: `EditCharter`, `StartAgentSession`, `ResumeAgentSession`.
Outbound: `CharterEdited`, `AgentSessionStarted`,
`AgentTurnStarted`, `AgentTurnEnded` (latter two emitted by
auto-instrumentation, observed by C5).

🟥 (from ES) — Charter merges vs replaces: v1 overwrote; v2 treats
charters as versioned. The agent reads the latest version on wake.

---

## Context map (relationships)

Using DDD's standard relationship vocabulary.

```
                  ┌──────────────────────────────────────────┐
                  │                                          │
                  │   Operator  ──U/D────► Senate           │
                  │             ──U/D────► Council          │
                  │             ◄──read── Observation       │
                  │                                          │
                  │   Senate    ───OHS───► Decisions        │
                  │             ──U/D────► Pod Lifecycle    │
                  │                       (admit / exile /  │
                  │                        image swap)      │
                  │                                          │
                  │   Council   ───OHS───► Decisions        │
                  │             ◄──pub─── Observation       │
                  │                                          │
                  │   Pod Life. ──U/D────► Agent Exec.      │
                  │             ◄──pub─── Observation       │
                  │                                          │
                  │   Agent Exec ──pub──► Observation       │
                  │                                          │
                  └──────────────────────────────────────────┘
```

Legend:

- **U/D** Upstream/Downstream: downstream conforms to upstream's
  language and model.
- **OHS** Open Host Service: the upstream publishes a stable public
  contract (events) that any downstream may consume.
- **pub** publishes events read by another context's read-model
  builder.

Notes on key relationships:

- **Senate is upstream of Decisions** (OHS): Senate publishes
  `ProposalClosed` events; Decisions consumes them and seals records.
- **Council is upstream of Decisions** (OHS): same shape, for
  closing-council summaries.
- **Pod Lifecycle is downstream of Senate** (U/D): admissions, exiles,
  and image-swaps are *outcomes of senate proposals*, never imperatives.
- **Observation is published by C5; everyone reads it via read-models**:
  no other context writes to Observation's tables.
- **Operator reads everything**: the Forum's UI is purely a read
  consumer except for `IssueProclamation`, `SendDirectMessage`,
  `EditCharter`, `CastBallot` — its four write commands.

---

## Aggregates → MCP surface mapping (preview)

This previews the MCP servers in [07-c4](07-c4.md), so the contexts
and the surface align.

| Bounded context | MCP server(s) | Tools (illustrative) |
|---|---|---|
| Operator | (none, direct REST) | (Forum talks HTTP/SSE, not MCP) |
| Senate | `senate` | `propose_*`, `cast_ballot`, `list_open_proposals`, `outcome` |
| Council | `coms` | `convene_council`, `post_message`, `close_council`, `dm` |
| Decisions | `decisions` | `read`, `list`, `search`, `seal` |
| Observation | `state` (read-only) | `members`, `endpoints`, `callers_of`, `calls_to`, `traces`, `health` |
| Pod Lifecycle | `pods` (NEW, vs v1) | `register_self`, `rename_self`, `propose_image_swap` |
| Agent Execution | (none, agent-internal) | charter on disk, sessions in CLI |

So **6 MCP servers** total. v1's 4 collapse-and-expand: `coms`,
`senate`, `decisions`, `state` stay (matched to contexts); `pods` is
new (rename / image-swap / register-self surface for the
self-organising mesh).

---

## Anti-corruption layers

Two places where conclave reads OSS contracts; both need a thin ACL
so OSS upgrades don't ripple into our domain.

1. **OTel ingest → Observation read-models.** We don't want OTel
   semantic conventions leaking into our `Call` / `Endpoint` types.
   ACL: an ingest layer maps OTel attributes to our domain language.
2. **Claude Code session → AgentExecution.** Claude Code's session
   format may change. ACL: AgentSession aggregate stores only what we
   need (pod_id, session_id, last_seen), not the raw session bytes.

---

## Why this is right-sized

- Seven contexts, each ~1 aggregate. Aligns with the seven phases of
  [02-event-storming](02-event-storming.md).
- Two of the seven (Operator, Pod Lifecycle) are new since v1 — they
  are where v1's pain was structural (the UI was one big tab grab,
  pod orchestration was a host-side script).
- Decisions is a thin downstream of Senate + Council — it owns no
  policy, just the durable record.
- Observation is purely a read-model writer, fed by published events
  from every other context plus OTel. This matches v1's spirit
  ("observer is the only writer of state") with stronger boundaries.
