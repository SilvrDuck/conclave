# 02 — Event Storming

**Tool**: Event Storming (Brandolini).
**Aim**: timeline of what happens in a conclave run. Drives the domain
model in [05-ddd-contexts](05-ddd-contexts.md) and the architecture in
[07-c4](07-c4.md).

> Conventions used below:
> - 🟠 **Event** (something that happened, past tense)
> - 🔵 **Command** (a request that may cause events)
> - 🟣 **Policy / reactor** (when X event, then Y command)
> - 🟡 **Read model** (what a UI/persona reads)
> - 🟥 **Hot spot** (open question; flagged for downstream specs)
> - 🟦 **External actor**

Code-level details belong nowhere on this map.

---

## Macro timeline of one conclave run

```
  bootstrap        ─►  proclamation 1   ─►  membership churn  ─►  council/build  ─►  app deployed  ─►  ...
        │                  │                       │                    │                  │
        │             [J1 issue]               [J5 witness]        [J5 J7]            [J6 try]
        │
   stack-up
```

The same micro-flows repeat per proclamation. v1's bug was treating
"first proclamation" as special; v2 treats N=1 as a degenerate case
of N.

---

## Phase 0 — Stack bootstrap

| | |
|---|---|
| 🟦 architect | runs `docker compose --profile conclave up` |
| 🔵 command | `bootstrap stack with defaults` (no custom CLI; the compose profile *is* the command) |
| 🟠 events | `StackProvisioned`, `BusReady`, `StoreReady`, `MeshReady`, `ProxyReady`, `ObserverReady` |
| 🟡 read model | "platform is healthy" badge in glance perspective |
| 🟥 hot spot | idempotency — a re-run of the compose profile must not wipe project state. State lives in mounted volumes; service containers are stateless. (See [03-prototype-audit](03-prototype-audit.md) L6 — v1's kickstart.sh had a "wipe everything" sledgehammer; v2 has no such script.) |

Nothing here involves agents yet. The architect's plane (A) is the only
actor.

---

## Phase 1 — First proclamation

The trigger that puts agents on the map.

| | |
|---|---|
| 🟦 Augustus | types a feature-shaped goal in the operator UI |
| 🔵 command | `IssueProclamation(text)` |
| 🟠 events | `ProclamationIssued(seq, text, issued_at)` · `DecisionPlaceholderCreated(adr_id, title)` |
| 🟣 policy | on `ProclamationIssued` and no pod exists → `SpawnFirstPod(role=tbd)` |
| 🟣 policy | on `ProclamationIssued` and ≥1 pod exists → broadcast to all admitted pods' inbox |
| 🟡 read model | proclamation timeline (witness perspective) |

The first pod is *not* named "founder" forever. It bootstraps under a
neutral handle and **renames itself** the moment its role is decided
(see Phase 2).

---

## Phase 2 — A pod arrives

A pod is *one agent managing one service*. The service is either
custom-code-the-agent-writes or an adopted-OSS-image-the-agent-manages.

| | |
|---|---|
| 🔵 command | `SpawnPod(role, image_strategy)` |
| 🟠 events | `PodContainerStarted(pod, image, mode)` · `AgentBooted(pod, agent_kind)` · `PodCharterLoaded(pod, charter)` |
| 🟣 policy | on `AgentBooted` → wake agent with proclamation + initial agenda |
| 🟠 events | `AgentRenamedSelf(pod, new_role)` *(emitted within the first agent turn when the role becomes clear)* |
| 🟡 read model | pod node appears on the forum graph |
| 🟥 hot spot | rename mid-life: when an agent's role evolves, can it rename itself again? Once and done feels too strict; arbitrary renames break references. Probable answer: each pod has a stable id + a mutable display-role. |

Two pod shapes coexist:

- **Code pod** — agent and the service code share one container. Image
  is whatever the agent's chosen language demands (Python+FastAPI,
  Node+Express, …). Built from a per-pod Dockerfile.
- **Adopted pod** — main container is an OSS image (`postgres:16`,
  `linuxserver/qbittorrent`, `meilisearch:1.x`). The agent runs in a
  **sidecar container** in the same pod, mounted with privileged access
  (Docker socket / `exec` rights / service API) so it can operate the
  service. The agent's identity, charter, agendas live in the sidecar.

Either way, the agent is the only thing that talks to the platform.

---

## Phase 3 — Senate: admitting the pod

The first thing any new pod does is bind itself to the senate.

| | |
|---|---|
| 🔵 command | `ProposeAdmission(charter, strategy)` |
| 🟠 events | `ProposalOpened(proposal_id, kind=admit, proposer, strategy)` · `VoteOpenInbox(voter, proposal_id)` (one per eligible voter) |
| 🔵 command | `CastBallot(proposal_id, voter, choice, comment?)` |
| 🟠 events | `BallotCast(...)` · `ProposalClosed(proposal_id, outcome)` |
| 🟣 policy | on `ProposalClosed(outcome=approved, kind=admit)` → `SealDecision(adr_id, summary)` and `PodAdmitted(pod)` |
| 🟣 policy | on `ProposalClosed(outcome=approved, kind=admit)` → `BroadcastMembership(pod)` to all peers' inbox |
| 🟡 read model | senate band cartouche (witness perspective) with strategy, ballots, deadline |

The four voting strategies (`majority`, `supermajority`,
`consensus_omnium`, `sortition`) are first-class — they are *the point
of the platform*, not overhead.

🟥 hot spot — **N=1 trivial pass**. A single-voter admission auto-passes.
v1 made this a special case; v2 should treat it as the strategy
naturally evaluating to "approved when proposer is the only eligible
voter."

🟥 hot spot — **deadlines**. v1 had proposals sitting forever past
their deadline. v2 needs a deadline reactor that closes any proposal
on a timer.

---

## Phase 4 — Council: making cross-cutting decisions

The interesting part. Agents disagree, talk, converge.

| | |
|---|---|
| 🔵 command | `ConveneCouncil(topic, participants)` |
| 🟠 events | `CouncilOpened(council_id, topic, participants)` |
| 🔵 command | `PostMessage(council_id, from_pod, body)` |
| 🟠 events | `MessagePosted(council_id, from_pod, body, sent_at)` |
| 🟣 policy | on `MessagePosted` → deliver `MessageReceived` to every participant's inbox |
| 🔵 command | `CloseCouncil(council_id, summary)` |
| 🟠 events | `CouncilClosed(council_id, summary, decisions: [adr_id?])` |
| 🟣 policy | on `CouncilClosed` with a sealed decision → `SealDecision(adr_id, body=summary)` |
| 🟡 read model | thread view (witness perspective); call-edge on the forum graph while open |

Councils may close without producing a decision (just gossip / status
sync). They may also be the substrate that *enables* a senate proposal
later (debate first, ballot after).

🟥 hot spot — **DMs vs councils.** A DM is structurally a 2-participant
council that never opens publicly. v2 should model both with one
aggregate to keep the storming honest.

🟥 hot spot — **Augustus's voice.** Augustus can read every council but
cannot post in one. Per J7 he can DM a pod, which the agent receives
as an inbox event with provenance `from_user`. That's structurally a
1-on-1 council Augustus *can* speak in.

---

## Phase 5 — Build: agents ship services

This is the meat. The system *becomes* something users could open.

| | |
|---|---|
| 🟦 pod agent | edits files in its workspace OR config of its adopted service |
| 🟠 events | `ServiceCodeChanged(pod, files)` · `EndpointObserved(pod, method, path)` |
| 🟣 policy | on `EndpointObserved` and no annotation → `RequestAnnotation(pod, endpoint)` to the pod's inbox |
| 🔵 command | `AnnotateEndpoint(pod, endpoint, description)` |
| 🟠 events | `EndpointAnnotated(pod, endpoint, body)` |
| 🟦 service | runs, accepts traffic |
| 🟠 events | `CallObserved(src_pod, dst_pod, endpoint, latency)` (from OTel spans) |
| 🟡 read model | call edges on the forum graph; endpoint table in the pod drawer |

🟥 hot spot — **image swap mid-life.** An agent decides the catalogue
needs a real DB and adopts `postgres:16`. The platform must let it
clone its identity into a fresh adopted-pod (Docker volume preserved,
charter preserved) and exile the old code-pod. This is a
proposal-kind we didn't have in v1.

---

## Phase 6 — Contract change

A pod's API breaks. Downstream pods must agree before it ships.

| | |
|---|---|
| 🟣 policy | on `EndpointObserved` for a *changed* endpoint → `IdentifyCallers(endpoint)` |
| 🔵 command | `ProposeContractChange(endpoints, rationale, strategy=consensus_omnium)` |
| 🟠 events | `ProposalOpened(kind=contract_change, affected=[callers])` |
| 🟣 policy | callers may `ConveneCouncil(topic="shape of new contract")` before balloting |
| 🟠 events | `BallotCast` · `ProposalClosed(outcome)` |
| 🟣 policy | on `outcome=approved` → `SealDecision`; pod ships |
| 🟣 policy | on `outcome=rejected` → pod must converge (back to council) |

This phase exercises `consensus_omnium` — every affected caller must
say yes. It's the strategy v2 most wants to see fire.

---

## Phase 7 — Augustus interrupts

Mid-flight steering, not waiting for the senate.

| | |
|---|---|
| 🟦 Augustus | nudges a pod via DM (J7) |
| 🔵 command | `SendDirectMessage(from_user, pod, body)` |
| 🟠 events | `MessagePosted(... from=__user__)` delivered to pod inbox |
| 🟦 Augustus | edits a charter (rare, J8-adjacent) |
| 🔵 command | `EditCharter(pod, new_body)` |
| 🟠 events | `CharterEdited(pod, body, by=__user__)` |
| 🟣 policy | on `CharterEdited` → wake pod with `charter_updated` event |

🟥 hot spot — **charter edit semantics.** Replaces or merges? v1
overwrote, which lost agent-authored sections. v2 should treat
charters as versioned documents with a clear diff and a "current"
revision the agent reads on every wake.

🟥 hot spot — **kill / pause a pod.** Augustus has no graceful
"pause" today. Killing == exile, which is heavy.

---

## Phase 8 — Completion

A proclamation finishes when the senate says it does. Subsequent
proclamations grow / pivot the system.

| | |
|---|---|
| 🔵 command | `ProposeCompletion(rationale, strategy=supermajority)` |
| 🟠 events | full proposal lifecycle |
| 🟣 policy | on `outcome=approved` → `ProclamationCompleted(seq, adr_id, summary)` |

The system keeps running; the proclamation closes. Augustus can issue
a new one any time.

---

## Cross-cutting reactors

These don't sit in one phase; they run continuously. **Each reactor
lives in the process that owns the tables it mutates** (no cross-
context writes — see [05-ddd-contexts](05-ddd-contexts.md) and
[07-c4](07-c4.md)).

| Reactor | Trigger | Action | Lives in |
|---------|---------|--------|----------|
| **Deadline closer** | proposal_id ticks past deadline | emit `TickDeadline`; strategy closes the proposal per its timeout policy | **Senate** process |
| **Health watcher** | container disappears / OTel error span | set `PodState.runtime_status = stopped` on the forum | **Observer** |
| **Block detector** | pod thinking > N minutes / council silent > M minutes | set `PodState.agent_state = stuck`; the Augustus inbox read-model surfaces it | **Observer** |
| **Activity digester** | hourly | summarise the activity feed into a digest row (for J3) | **Observer** |

Every reactor is named, observable, and OSS-implementable (NATS
JetStream consumers / Postgres triggers / OTel collector pipelines).

---

## What this map proves

- The 9 JTBDs of [01-jtbd](01-jtbd.md) each correspond to legible UI
  reads of these events. No job dangles.
- Every event names a domain object (proclamation / pod / proposal /
  ballot / council / decision / endpoint / call / charter). Those
  objects are the aggregates in [05-ddd-contexts](05-ddd-contexts.md).
- The reactor list shows where we genuinely need *time*-driven logic
  (deadlines, health, blocks, digests) — those become scheduled jobs
  in [07-c4](07-c4.md).
- Every hot spot (🟥) is captured for resolution; none should slip
  into implementation un-decided.
