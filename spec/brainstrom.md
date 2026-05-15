# Conclave — Design Document

**Status**: Draft, alpha-targeting
**Name**: Conclave (the system); the control-tower UI is called the Forum
**Audience**: builders of the system, and the agents themselves once it exists

---

## 1. Vision

Conclave is a consensus-driven, orchestrator-free platform for building microservice projects with autonomous AI agents. A user states a goal; a founder agent spawns; the founder proposes peers; the peers vote; together they design, build, and ship a working multi-service system. No supervisor, no router, no central coordinator decides anything — every decision affecting more than one agent is the outcome of a vote or a meeting.

The platform is dumb infrastructure that *records* what agents do and gives them the primitives to coordinate. The agents are the only intelligence.

### Core principles

- **Symmetry** — bootstrap is a vote, completion is a vote, contract changes are meetings producing ADRs, member removal is a vote. No special code paths anywhere. Founder = first member. User = async peer.
- **Observed truth over declared truth** — the platform observes reality (bus traffic, inter-pod calls, container liveness) and asks agents to annotate it. Nothing critical depends on hand-authored manifests that can drift from running code.
- **MCP as the agent-platform contract** — every agent-platform interaction is an MCP tool call. No custom shell primitives.
- **Pluggability at every external boundary** — transport, repo host, CI/CD, doc backend, CLI runtime, observability, notification, runtime/IaC. Each slot ships ≥2 candidates in alpha to prove the abstraction is real.
- **Stateless platform, stateful project** — runtime owns no durable data. Project state lives in monorepo + doc backend. Platform rebuildable from `conclave.config.yaml` + the project's two stores.
- **Existing tooling over custom code** — Postgres, OpenTelemetry, NATS, Terraform, Loki. Glue, not invention.

### Non-goals (alpha)

Auth/authz. Cost governance beyond user budgets. Cross-pod integration tests as a platform feature. Live mid-flight stack swaps. RAG over decisions. Multi-tenant Conclave.

---

## 2. The architecture in one diagram

```
                                        ┌─────────────────────────┐
                                        │   User (async peer)     │
                                        │  ─────────────────────  │
                                        │  email · telegram · UI  │
                                        └────────┬────────────────┘
                                                 │
                                                 ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐    ┌─────────────────────┐
   │  Pod A   │  │  Pod B   │  │  Pod C   │    │     Forum UI        │
   │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │    │  (pure read +       │
   │ │ CLI  │ │  │ │ CLI  │ │  │ │ CLI  │ │    │   2 user writes:    │
   │ └──┬───┘ │  │ └──┬───┘ │  │ └──┬───┘ │    │   • goal/mandate    │
   │ ┌──▼───┐ │  │ ┌──▼───┐ │  │ ┌──▼───┐ │    │   • charter edits)  │
   │ │harnes│ │  │ │harnes│ │  │ │harnes│ │    └─────────┬───────────┘
   │ └──┬───┘ │  │ └──┬───┘ │  │ └──┬───┘ │              │
   └────┼─────┘  └────┼─────┘  └────┼─────┘              │
        │  MCP        │  MCP        │  MCP               │ reads MCPs
        ▼             ▼             ▼                    ▼
   ╔════════════════════════════════════════════════════════════════╗
   ║                  MCP SURFACE  (the only contract)              ║
   ║   ┌────────┐   ┌─────────┐   ┌───────────┐   ┌─────────┐       ║
   ║   │  coms  │   │ senate  │   │ decisions │   │  state  │       ║
   ║   └───┬────┘   └────┬────┘   └─────┬─────┘   └────┬────┘       ║
   ╚═══════╪═════════════╪══════════════╪══════════════╪════════════╝
           │             │              │              │
       adapter       adapter        adapter        adapter
           │             │              │              │
           ▼             ▼              ▼              ▼
       ┌───────┐    ┌────────┐    ┌──────────┐    ┌──────────┐
       │ NATS  │    │ Senate │    │GH Issues │    │ Observer │
       │  or   │    │ ledger │    │   or     │    │ Postgres │
       │ Redis │    │(FastAPI│    │ Obsidian │    │          │
       │       │    │+SQLite)│    │  vault   │    │          │
       └───┬───┘    └────────┘    └──────────┘    └─────┬────┘
           │                                            │
           │   (observer also subscribes to bus,        │
           │    to record chatroom rosters & history)   │
           └────────────────────────────────────────────┤
                                                        │
        ┌───────────────────────────────────────────────┤
        │     additional observer ingest sources        │
        │   ┌─────────────────────────────────────────┐ │
        │   │  Traces: OpenTelemetry/Tempo            │◄┤
        │   │      OR Linkerd service mesh            │ │
        │   └─────────────────────────────────────────┘ │
        │   ┌─────────────────────────────────────────┐ │
        │   │  Container runtime API (docker / k8s)   │◄┘
        │   └─────────────────────────────────────────┘
        └─────────────────────────────────────────────────

  Logs (raw stdout) ─► stdout-tailed-by-UI  OR  Loki+Grafana   ────► Forum UI
```

**Read it as**: agents talk to MCP servers, never to backends directly. MCP servers stand on adapters. Adapters can be swapped without agents noticing. The observer is the only thing that *writes* to the state Postgres; everyone else reads. The UI is downstream of everything and orchestrates nothing.

---

## 3. The three layers

What's source code, what's running, what's the project itself? Crucially separable.

```
╔═══════════════════════════════════════════════════════════════════╗
║  LAYER 3 ─ PLATFORM SOURCE     (the tool's own repo, this thing)  ║
║  ─────────────────────────────────────────────────────────────    ║
║  • IaC templates  (compose / terraform / k3d)                     ║
║  • MCP server implementations & adapters                          ║
║  • Observer service                                               ║
║  • Senate ledger service                                          ║
║  • Wizard + Forum UI (pixel-art frontend)                         ║
║  • Harness (per-pod sidecar)                                      ║
║  • Persona library                                                ║
╚═══════════════════════════════════════════════════════════════════╝
                            │
                            │  generates IaC · runs services
                            ▼
╔═══════════════════════════════════════════════════════════════════╗
║  LAYER 2 ─ PLATFORM RUNTIME     (ephemeral · container-borne)     ║
║  ─────────────────────────────────────────────────────────────    ║
║                                                                   ║
║   N pod containers ──┐                                            ║
║                      ├── bus (NATS|Redis)                         ║
║   Forum UI ──────────┤                                            ║
║                      ├── observer + Postgres                      ║
║   wizard ────────────┤                                            ║
║                      ├── senate ledger                            ║
║                      │                                            ║
║                      ├── trace pipeline (OTel|mesh)               ║
║                      └── log pipeline (stdout|Loki)               ║
║                                                                   ║
║   destroy and rebuild any time — no durable data here             ║
╚═══════════════════════════════════════════════════════════════════╝
                            │
                            │  reads/writes via MCP
                            ▼
╔═══════════════════════════════════════════════════════════════════╗
║  LAYER 1 ─ PROJECT STATE     (durable · user-owned · portable)    ║
║  ─────────────────────────────────────────────────────────────    ║
║                                                                   ║
║   Monorepo (git)            │   Doc backend (pluggable)           ║
║   ────────────              │   ─────────────────────             ║
║   • code (per pod)          │   • ADRs                            ║
║   • charters                │   • council transcripts             ║
║   • endpoint annotations    │   • mandates / goal history         ║
║   • conclave.config.yaml       │   • completion records              ║
║   • generated IaC           │   • exile rationales                ║
║   • shared/ libs & skills   │                                     ║
║                             │                                     ║
║   GitHub  OR  GitLab        │   GH Issues  OR  Obsidian vault     ║
╚═══════════════════════════════════════════════════════════════════╝
```

**The invariant**: destroying Layer 2 is fine; rebuild from Layer 1 + Layer 3. Destroying Layer 1 destroys the project. Layer 3 is shared infrastructure across all projects.

---

## 4. Anatomy of a pod

Every agent is identical in structure. Two processes inside the container, three things mounted, four MCPs reached over the network.

```
                       ╭────────── pod container ──────────╮
                       │                                    │
                       │   ┌────────────────────────────┐   │
                       │   │           CLI              │   │
                       │   │   (Claude Code | Pi)       │   │
                       │   │   ──────────────────       │   │
                       │   │   speaks MCP natively      │   │
                       │   │   --resume keeps context   │   │
                       │   └──────────────┬─────────────┘   │
                       │                  │ stdin/stdout    │
                       │                  ▼                 │
                       │   ┌────────────────────────────┐   │
                       │   │         Harness            │   │
                       │   │   ─────────────────────    │   │
                       │   │   • spawn/idle CLI         │   │
                       │   │   • inbox poll (bus topic) │   │
                       │   │   • dual-write annotations │   │
                       │   │   • MCP server wiring      │   │
                       │   │   • mount enforcement      │   │
                       │   └────────────┬───────────────┘   │
                       │                │                   │
   filesystem mounts   │                │                   │
                       │     ┌──────────┴─────────┐         │
                       │     │                    │         │
                       │     ▼                    ▼         │
                       │  ┌────────┐         ┌────────┐     │
                       │  │ pods/  │  rw     │ shared/│  rw │
                       │  │ self/  │         │        │     │
                       │  └────────┘         └────────┘     │
                       │                                    │
                       │  ┌────────┐                        │
                       │  │/conclave/ │  ro                    │
                       │  └────────┘                        │
                       │                                    │
                       ╰────────────────┬───────────────────╯
                                        │ network (MCP)
                                        ▼
                       ┌────────────────────────────────┐
                       │   coms · senate · decisions    │
                       │   state · (events inbound)     │
                       └────────────────────────────────┘
```

**What's in `pods/self/`** (read-write by this pod only, container-isolated from other pods):

```
pods/alice/
├── charter.md            # the agent's system prompt (free-form, peer-authored)
├── endpoints.md          # endpoint annotations (dual-written by harness)
├── README.md             # what this pod does, peer-readable
├── workspace/            # service code: source of truth for the running service
├── skills/               # pod-local skills (peer-readable, monorepo default)
└── libs/                 # pod-local libs (peer-readable)
```

**What's in `shared/`** (read-write by every pod; monorepo-level coordination):

```
shared/
├── skills/               # cross-pod skills (relocated here by senate vote)
├── libs/                 # cross-pod code (same logic)
└── infra-refs/           # cross-pod constants/refs (rare)
```

**What's in `/conclave/`** (read-only platform reference, mounted from Layer 3):

```
/conclave/
├── primitives.md         # canonical MCP reference for agents
├── personae/             # Cicero.md, Cato.md, … (experimental mode)
└── voting-strategies.md  # what each strategy does, when to use
```

---

## 5. The MCP surface — exhaustive

Four servers, one inbound event stream. That's the entire contract.

```
                       ╔══════════════════════════════════╗
                       ║          MCP SURFACE             ║
                       ╠══════════════════════════════════╣
                       ║                                  ║
       ┌───────────────╫──► coms      conversation        ║
       │               ║                                  ║
       │  (outbound)   ╫──► senate    proposals & votes   ║
   agent calls         ║                                  ║
       │               ╫──► decisions doc backend         ║
       │               ║                                  ║
       └───────────────╫──► state     observer's view     ║
                       ║                                  ║
                       ║  ◄── events  (inbound stream)    ║
                       ║      ─────                       ║
                       ║      wake signals from harness   ║
                       ╚══════════════════════════════════╝
```

### `coms` — conversation primitives

```
open_chatroom(participants, topic)        → chatroom_id
send(chatroom_id, message)                → ack
recv()                                    → [events]
direct_message(peer, message)             → ack
convene_council(participants, agenda)     → council_id
close(chatroom_id | council_id, summary?)
```

Backed by the bus. Every conversation is recorded by the observer; the Forum UI subscribes live.

### `senate` — collective decisions

```
propose_member(charter, strategy="majority")        → proposal_id
propose_exile(pod_name, rationale)                  → proposal_id
propose_revival(former_pod_name, new_charter)       → proposal_id
propose_contract_change(endpoints, rationale)       → proposal_id
propose_completion(rationale)                       → proposal_id
cast_ballot(proposal_id, yes|no|abstain, comment?)
list_open_proposals()                               → [proposals]
outcome(proposal_id)                                → outcome | "open"
```

Backed by the senate ledger. Concluded votes write ADRs to the doc backend automatically.

### `decisions` — collective doc backend

```
write_adr(title, body, affected_pods, proposal_id?) → adr_id
read(adr_id)                                        → content
search(query, limit=10)                             → [hits]
list(filter?)                                       → [adrs]
```

Backed by GH Issues or Obsidian. Search is grep at alpha; vector search slots in at beta behind the same interface (slot 9).

### `state` — read-only system view

```
members()                          → [{name, status, charter_path}]
endpoints(pod_name)                → [{path, method, annotation?}]
callers_of(endpoint)               → [pod_names]
calls_to(pod_name)                 → [{caller, endpoint, rate}]
chatrooms()                        → [{id, participants, topic, last_active}]
open_proposals()                   → [proposals]
search(query, kind?)               → [hits]   # skill | lib | endpoint | adr
platform()                         → conclave_config_excerpt
```

Backed by the observer's Postgres. **Read-only**: agents never write here. The observer is the only writer.

### Inbound: `events`

Not a callable MCP — a subscription delivered to the agent's recv loop by the harness.

```
message_received       │  vote_open             │  council_invited
goal_updated           │  annotation_requested  │  member_admitted
member_exiled          │  contract_change_proposed
```

### What's intentionally absent

```
✗ raw bus access (agents never publish to topics directly)
✗ separate registry MCP (observer IS the registry; surfaced via state)
✗ contract.yaml files maintained by agents (endpoints observed + annotated)
✗ custom shell primitives (everything is MCP)
✗ orchestrator / router / supervisor service
```

---

## 6. The observer — single most important component

```
                  ╔═════════════════════════════════════╗
                  ║          OBSERVER                   ║
                  ║                                     ║
        ┌────────►║  ┌─────────────────────────────┐    ║
        │         ║  │  Ingest layer (adapters)    │    ║
   bus  │  taps   ║  └─────────────────────────────┘    ║──┐
   subs ─────────►║                │                    ║  │
                  ║                ▼                    ║  │ pushes
        ┌────────►║  ┌─────────────────────────────┐    ║  │ annotation
   OTel │  pulls  ║  │  Projection engine          │    ║  │ requests
   traces────────►║  │   (events → relational)     │    ║  │ via bus
                  ║  └─────────────┬───────────────┘    ║  │ inbox
        ┌────────►║                │                    ║  │
   docker        ║                ▼                     ║  │
   liveness──────►║  ┌─────────────────────────────┐    ║──┘
                  ║  │     Postgres                │    ║
                  ║  │   members │ endpoints │     │    ║
                  ║  │   calls   │ chatrooms │     │    ║
                  ║  │   votes   │ annotations│    │    ║
                  ║  └─────────────┬───────────────┘    ║
                  ║                │                    ║
                  ║                ▼                    ║
                  ║  ┌─────────────────────────────┐    ║
                  ║  │  state MCP server           │    ║
                  ║  │   (read-only outward)       │    ║
                  ║  └─────────────────────────────┘    ║
                  ╚═════════════════════════════════════╝
                                   │
                                   │
                                   ▼
                            ┌──────────────┐
                            │ pods + UI    │
                            │ read state   │
                            └──────────────┘
```

### Annotation flow (observer ⇄ agent)

```
   observer detects new endpoint
            │
            ▼
   bus.publish(topic="pod/alice/inbox",
               event="annotation_requested",
               subject="GET /users/{id}")
            │
            ▼
   harness recv loop picks it up
            │
            ▼
   ┌─────────────────────────────┐
   │ alice awake?                │
   │   yes → deliver to CLI      │
   │   no  → wake CLI (--resume) │
   └─────────────┬───────────────┘
                 │
                 ▼
   CLI produces annotation
                 │
                 ▼
   harness dual-writes:
     1. POST observer ingest        ──►  Postgres (fast read via state.endpoints)
     2. git commit endpoints.md     ──►  monorepo (durable, survives stack swap)
```

**Why dual-write**: Postgres is cache (rebuildable). Markdown is truth (portable). Together they give fast reads and zero-loss migration.

### Cold-start

After a fresh deploy (or a stack swap), the observer's Postgres is empty. It bootstraps in this order:

```
1. Read conclave.config.yaml      ──►  know which backends are live
2. Read latest ADRs in doc      ──►  reconstruct member roster, last decisions
   backend
3. Read pods/*/charter.md       ──►  member metadata
4. Read pods/*/endpoints.md     ──►  endpoint annotations
5. Begin subscribing to bus,    ──►  live state catches up as traffic flows
   OTel, container runtime
```

Within seconds the senate is operational again, even though all "in-flight" state was lost. Decisions survived; gossip didn't.

---

## 7. Consensus mechanics

### Voting strategies (pluggable)

Strategies are Python functions: `(ballots, members, context) → outcome | "open"`. Timeout policy is baked into the strategy.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Strategy             │ When                  │ Behavior              │
├──────────────────────────────────────────────────────────────────────┤
│  majority             │ Routine, low-stakes   │ >50% yes, absent→abst │
│  supermajority        │ High-stakes (exile,   │ ≥2/3 + strict quorum  │
│                       │ completion)           │                       │
│  consensus_omnium     │ Contract changes      │ All affected unanimous│
│  sortition            │ Cheap routine         │ N random members vote │
└──────────────────────────────────────────────────────────────────────┘
```

Adding a strategy = one Python file + config entry. User configures per-decision-type defaults via wizard.

### Proposal lifecycle

```
agent calls senate.propose_*(...)
              │
              ▼
    ┌─────────────────────────────────────┐
    │ senate ledger:                      │
    │   create proposal                   │
    │   compute affected list             │
    │   (e.g., callers_of for contracts)  │
    │   emit vote_open events to voters   │
    └─────────────────┬───────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────┐
    │ voters wake, deliberate, ballot     │
    │                                     │
    │ (optionally convene_council         │
    │  during voting to discuss)          │
    └─────────────────┬───────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────┐
    │ strategy evaluates after every      │
    │ ballot:                             │
    │   - quorum reached & outcome clear? │
    │   - timeout reached?                │
    │ if not: still "open"                │
    └─────────────────┬───────────────────┘
                      │ outcome decided
                      ▼
    ┌─────────────────────────────────────┐
    │ senate ledger:                      │
    │   write ADR to decisions backend    │
    │   emit outcome events               │
    │   (admit member / start exile /     │
    │    record contract change / ...)    │
    └─────────────────────────────────────┘
```

### Worked example: contract change

```
Bob ships code that alters his API
              │
              ▼
   observer detects endpoint change
              │
              ▼
   bus.publish(annotation_requested
               for bob's new endpoints)
              │
              ▼
   Bob's harness wakes Bob's CLI
              │
              ▼
   Bob annotates → dual-write
              │
              ▼
   Bob calls
   senate.propose_contract_change(
       endpoints=["GET /users/{id}"],
       rationale="adding pagination")
              │
              ▼
   ┌─────────────────────────────────┐
   │ senate auto-fetches consumers:  │
   │   state.callers_of(endpoint)    │
   │   → ["alice", "carol"]          │
   │ strategy = consensus_omnium     │
   └────────────┬────────────────────┘
                │
                ▼
   alice + carol wake; ballot
                │
                ▼
   alice wants to discuss:
      coms.convene_council(
        participants=[alice, bob, carol],
        agenda="paging shape")
                │
                ▼
   meeting happens · council closes
   with summary
                │
                ▼
   final ballots cast → outcome
                │
                ▼
   ADR written to decisions backend
   Bob ships
   observer sees new call patterns
```

No `contract.yaml` was authored or edited. The contract = observed endpoints + annotations + the most recent approving ADR.

### Member lifecycle

```
                ┌─────────────────────────────┐
                │  USER spawns founder        │
                │  (via Forum UI)             │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │  N=1: trivial vote passes   │
                │  (majority of one)          │
                └──────────────┬──────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │  founder proposes peer (charter)     │
            │  senate.propose_member               │
            └──────────────┬───────────────────────┘
                           │
                           ▼ (existing members ballot)
            ┌──────────────────────────────────────┐
            │  approved → harness spawns container │
            │  rejected → proposal closed          │
            └──────────────┬───────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────────────┐
            │  new pod registers with observer     │
            │  (heartbeat + first contract scrape) │
            │  member becomes votable              │
            └──────────────┬───────────────────────┘
                           │
                       ... time passes ...
                           │
                           ▼
            ┌──────────────────────────────────────┐
            │  conflict / failure?                 │
            │  any member can propose_exile        │
            │  (supermajority by default)          │
            └──────────────┬───────────────────────┘
                           │ approved
                           ▼
            ┌──────────────────────────────────────┐
            │  container stopped                   │
            │  pod dir moved pods/X → exile/X      │
            │  ADR records rationale               │
            └──────────────┬───────────────────────┘
                           │
                       ... maybe later ...
                           │
                           ▼
            ┌──────────────────────────────────────┐
            │  any member proposes_revival(X,      │
            │      new_charter)                    │
            │  vote includes exile history         │
            │  approved → new container, fresh CLI │
            │  reads /exile/X/ history             │
            └──────────────────────────────────────┘
```

---

## 8. Wake mechanism

A pod's CLI is not a long-running process. It runs only when there's work.

```
                  ┌────────────────────────────────────┐
                  │       bus topic: pod/alice/inbox   │
                  └─────────────────┬──────────────────┘
                                    │
                                    │ any event:
                                    │  - message_received
                                    │  - vote_open
                                    │  - council_invited
                                    │  - goal_updated
                                    │  - annotation_requested
                                    │  - self-timer fired
                                    ▼
                  ┌────────────────────────────────────┐
                  │   harness recv loop                │
                  │   (always running, cheap)          │
                  └─────────────────┬──────────────────┘
                                    │
                            ┌───────┴───────┐
                            │               │
                       CLI awake?       CLI idle?
                            │               │
                            ▼               ▼
                  ┌─────────────────┐  ┌─────────────────────┐
                  │ deliver event   │  │ CLI --resume <sid>  │
                  │ to recv         │  │ (warm restart)      │
                  └─────────────────┘  └────────┬────────────┘
                                                │
                                                ▼
                                       deliver event to recv
                                                │
                                                ▼
                                       agent does work
                                                │
                                                ▼
                                    ┌────────────────────────┐
                                    │ idle timer → CLI sleeps│
                                    │ (zero LLM tokens spent)│
                                    └────────────────────────┘
```

The harness is the only thing that knows whether the CLI is awake or asleep. Everything else (bus, observer, peers) just publishes events; the harness handles wake transparently.

---

## 9. Monorepo layout

```
project-repo/
│
├── conclave.config.yaml              # the wizard's output (single source of platform truth)
│
├── infra/
│   ├── compose.yaml               # generated, slot 1 = compose
│   │   OR
│   └── terraform/                 # generated, slot 1 = k3d|cloud
│       ├── main.tf
│       └── modules/
│
├── shared/
│   ├── skills/                    # cross-pod skills
│   ├── libs/                      # cross-pod code
│   └── infra-refs/                # shared constants/refs (rare)
│
├── pods/
│   ├── alice/
│   │   ├── charter.md             # system prompt + role + skill list
│   │   ├── endpoints.md           # observed endpoints + agent's annotations
│   │   ├── README.md              # peer-readable description
│   │   ├── workspace/             # service code (the actual app)
│   │   ├── skills/                # pod-local skills (peer-readable)
│   │   └── libs/                  # pod-local libs (peer-readable)
│   ├── bob/
│   │   └── ...
│   └── carol/
│       └── ...
│
└── exile/
    ├── dave/                      # former pod, code preserved
    │   └── ... (full history)
    └── erin/
        └── ...
```

**Note**: the doc backend is *not* part of the monorepo unless slot 5 = Obsidian (in which case `vault/` is also at the root, but managed by `decisions` MCP not by agents directly).

---

## 10. Pluggability matrix

The whole point of forcing ≥2 candidates per slot in alpha: one implementation = a hardcode pretending to be an abstraction.

```
┌─────┬────────────────────┬──────────────────────────┬─────────────────────────┐
│Slot │  Concern           │  Candidate A             │  Candidate B            │
├─────┼────────────────────┼──────────────────────────┼─────────────────────────┤
│  1  │ Runtime / IaC      │ Docker Compose           │ Terraform-provisioned   │
│     │                    │                          │ k3d                     │
├─────┼────────────────────┼──────────────────────────┼─────────────────────────┤
│  2  │ Bus / transport    │ NATS                     │ Redis Streams           │
├─────┼────────────────────┼──────────────────────────┼─────────────────────────┤
│  3  │ Repo host          │ GitHub                   │ GitLab                  │
├─────┼────────────────────┼──────────────────────────┼─────────────────────────┤
│  4  │ CI/CD              │ GitHub Actions           │ GitLab CI               │
│     │                    │ (coupled with slot 3)    │ (coupled with slot 3)   │
├─────┼────────────────────┼──────────────────────────┼─────────────────────────┤
│  5  │ Doc backend        │ GitHub Issues            │ Obsidian vault          │
│     │                    │ (API-backed)             │ (filesystem-backed)     │
├─────┼────────────────────┼──────────────────────────┼─────────────────────────┤
│  6  │ CLI runtime        │ Claude Code              │ Pi (MCP support TBV)    │
├─────┼────────────────────┼──────────────────────────┼─────────────────────────┤
│ 7a  │ Trace introspection│ OpenTelemetry SDK        │ Linkerd service mesh    │
│     │                    │ → Tempo                  │ (sidecar)               │
├─────┼────────────────────┼──────────────────────────┼─────────────────────────┤
│ 7b  │ Log aggregation    │ Stdout tailed by UI      │ Loki + Grafana          │
├─────┼────────────────────┼──────────────────────────┼─────────────────────────┤
│  8  │ User notification  │ Email (SMTP)             │ Telegram bot            │
└─────┴────────────────────┴──────────────────────────┴─────────────────────────┘

Beta slot:
┌─────┬────────────────────┬──────────────────────────┬─────────────────────────┐
│  9  │ Search / embedding │ OpenAI embeddings +      │ Sentence-transformers + │
│     │ (behind decisions  │ sqlite-vec               │ Chroma (local)          │
│     │  .search)          │                          │                         │
└─────┴────────────────────┴──────────────────────────┴─────────────────────────┘
```

### Adapter shape (illustrative, slot 2)

```
              ┌───────────────────────────────┐
              │   coms MCP server (stable)    │
              │   ──────────────────────      │
              │   open_chatroom / send /      │
              │   recv / direct_message / …   │
              └────────────┬──────────────────┘
                           │
                           ▼
              ┌───────────────────────────────┐
              │      BusAdapter (interface)   │
              │   publish(topic, payload)     │
              │   subscribe(topic, handler)   │
              │   ack / replay / etc          │
              └─────┬────────────────────┬────┘
                    │                    │
            implementations:      both implement same iface
                    │                    │
                    ▼                    ▼
            ┌──────────────┐      ┌──────────────┐
            │  NATS impl   │      │ Redis Streams│
            │  (push-mode) │      │ (pull-mode)  │
            └──────────────┘      └──────────────┘
```

Swap = config change. `conclave.config.yaml: bus: redis` instead of `nats`. No agent code touched.

---

## 11. The wizard

First-run experience and the surface that makes pluggability real.

```
┌────────────────────────────────────────────────────────────────────┐
│                       WIZARD — STEP 1                              │
│                  Where will this run?                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   ● Local Docker Compose         (zero deps, easy)                 │
│   ○ Local k3d  (terraform)       (more production-shaped)          │
│   ○ BYO Kubernetes cluster       (kubeconfig: ___________)         │
│   ○ Cloud — AWS / GCP            (beta — Terraform-provisioned)    │
│                                                                    │
│                                            [ Next → ]              │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                       WIZARD — STEP 2                              │
│                  Pick your stack                                   │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Bus            [ NATS         ▾ ]    ● Deploy   ○ BYO  __________ │
│  Repo host      [ GitHub       ▾ ]              ● BYO  token:____  │
│  CI/CD          [ GH Actions   ▾ ]    ● Deploy   ○ BYO             │
│  Doc backend    [ Obsidian     ▾ ]    ● Deploy   ○ BYO  vault:____ │
│  CLI runtime    [ Claude Code  ▾ ]    (always per-pod)             │
│  Traces         [ OTel + Tempo ▾ ]    ● Deploy   ○ BYO  endpoint:_ │
│  Logs           [ Stdout       ▾ ]    ● Deploy   ○ BYO             │
│  Notifications  [ Email        ▾ ]              ● BYO  SMTP:_____  │
│                                                                    │
│              [Test all connections]      [ ← Back   Next → ]       │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                       WIZARD — STEP 3                              │
│                  Credentials                                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   LLM API keys     ANTHROPIC_API_KEY: ___________________          │
│                    (other providers shown when relevant)           │
│                                                                    │
│   Repo token       GITHUB_TOKEN:      ___________________          │
│   Notify creds     SMTP_PASSWORD:     ___________________          │
│                                                                    │
│   stored in:   ● local .env   ○ secrets backend (beta)             │
│                                                                    │
│                                  [ ← Back     Launch ]             │
└────────────────────────────────────────────────────────────────────┘
```

**Quickstart button** on step 1 skips through with Local Demo defaults: Compose + NATS + GitHub + Obsidian + OTel/Tempo + stdout + Email. One LLM key away from running.

### Presets

```
┌──────────────────┬─────────────────────────────────────────────────┐
│  Local Demo      │  Compose · NATS · GitHub · Obsidian · OTel ·    │
│                  │  stdout · Email                                 │
├──────────────────┼─────────────────────────────────────────────────┤
│  Self-hosted     │  Terraform-k3d · NATS · GitLab · GitLab Issues  │
│                  │  · Linkerd · Loki/Grafana · Telegram            │
├──────────────────┼─────────────────────────────────────────────────┤
│  Cloud Hybrid    │  Terraform on AWS · managed NATS · GitHub ·     │
│  (beta)          │  GH Issues · AWS X-Ray · SES                    │
└──────────────────┴─────────────────────────────────────────────────┘
```

---

## 12. Stack migration (no live swap)

A project survives any stack change. The mechanism:

```
   ┌──────────────────────────┐
   │  conclave down              │   ←── tears down current runtime
   │  (Layer 2 destroyed)     │       project state untouched
   └────────────┬─────────────┘
                │
                ▼
   ┌──────────────────────────┐
   │  re-open wizard          │   ←── user picks new slot values
   │  edit conclave.config.yaml  │
   └────────────┬─────────────┘
                │
                ▼
   ┌──────────────────────────┐
   │  doc backend change?     │   ──no──┐
   │  yes → adapter.export_all│         │
   │        adapter.import_all│         │
   └────────────┬─────────────┘         │
                │ ◄───────────────────  ┘
                ▼
   ┌──────────────────────────┐
   │  IaC regenerated         │
   │  old infra/ wiped        │
   │  new infra/ committed    │
   └────────────┬─────────────┘
                │
                ▼
   ┌──────────────────────────┐
   │  conclave up                │
   │  containers provisioned  │
   │  observer cold-starts    │
   │  (reads ADRs + endpoints │
   │   from monorepo & docs)  │
   └────────────┬─────────────┘
                │
                ▼
   ┌──────────────────────────┐
   │  agents spawn into       │
   │  fresh containers        │
   │  read charters + ADRs    │
   │  resume work             │
   └──────────────────────────┘

   Lost:        in-flight chatroom messages, open vote ballots,
                CLI session caches
   Preserved:   every decision, charter, code, contract,
                endpoint annotation, ADR
```

The cut is principled: **agreements durable, gossip ephemeral**. This is how production systems work.

---

## 13. User as async peer

```
                       ┌──────────────────────────────┐
                       │           User               │
                       └───────┬──────────────┬───────┘
                               │              │
                  outbound: notify       inbound: act
                               │              │
                ┌──────────────┘              └──────────────┐
                ▼                                            ▼
        ┌───────────────┐                          ┌──────────────────┐
        │ notification  │                          │   Forum UI       │
        │ adapter       │                          │   ────────       │
        │ ─────────     │                          │  • write goal    │
        │ Email | TG    │                          │  • edit charter  │
        └───────┬───────┘                          │  • view forum    │
                │                                  └────────┬─────────┘
                │ pushes events                             │
                │  (vote open,                              │  writes
                │   ADR proposal,                           │
                │   contract change,                        ▼
                │   agent paged user)                ┌──────────────┐
                │                                    │ bus / monorepo│
                │                                    │ (immediate    │
                │                                    │  agent wake)  │
                ▼                                    └──────────────┘
        user reads, eventually
        writes back via UI
```

**Authority**: none in the chatroom — user is a peer. Force-paths are indirect (charter edit, goal update, restart). Preserves consensus-driven property genuinely, not performatively.

---

## 14. Forum UI surfaces

```
   ╔══════════════════════════════════════════════════════════╗
   ║                       FORUM UI                           ║
   ║                  (pixel-art Roman scene)                 ║
   ╠══════════════════════════════════════════════════════════╣
   ║                                                          ║
   ║   ┌─────────────────────────────────────────────────┐    ║
   ║   │   FORUM VIEW (default)                          │    ║
   ║   │   ─────────────                                 │    ║
   ║   │   • pixel-art city scene                        │    ║
   ║   │   • each pod = a domus                          │    ║
   ║   │   • agent sprites: idle/walking/speaking/sleep  │    ║
   ║   │   • chatrooms = clusters around stone tables    │    ║
   ║   │   • active votes = citizens at the Rostra       │    ║
   ║   │                                                 │    ║
   ║   │   data: state.* + bus subscriptions             │    ║
   ║   └─────────────────────────────────────────────────┘    ║
   ║                                                          ║
   ║   ┌─────────────────────────────────────────────────┐    ║
   ║   │   TABULARIUM                                    │    ║
   ║   │   ────────────                                  │    ║
   ║   │   • ADR archive (stone-tablet aesthetic)        │    ║
   ║   │   • filter by topic / pod / date                │    ║
   ║   │   data: decisions.list / .read / .search        │    ║
   ║   └─────────────────────────────────────────────────┘    ║
   ║                                                          ║
   ║   ┌─────────────────────────────────────────────────┐    ║
   ║   │   COUNCIL VIEW                                  │    ║
   ║   │   ────────────                                  │    ║
   ║   │   • live transcripts of chatrooms/councils      │    ║
   ║   │   data: bus subscription on chatroom topics     │    ║
   ║   └─────────────────────────────────────────────────┘    ║
   ║                                                          ║
   ║   ┌─────────────────────────────────────────────────┐    ║
   ║   │   CHARTER EDITOR                                │    ║
   ║   │   ────────────                                  │    ║
   ║   │   • edit any agent's system prompt              │    ║
   ║   │   • effective on next wake                      │    ║
   ║   │   action: git commit pods/X/charter.md          │    ║
   ║   └─────────────────────────────────────────────────┘    ║
   ║                                                          ║
   ║   ┌─────────────────────────────────────────────────┐    ║
   ║   │   EXILE DISTRICT                                │    ║
   ║   │   ──────────────                                │    ║
   ║   │   • former pods + their exile ADRs              │    ║
   ║   │   • revival button (proposes_revival)           │    ║
   ║   └─────────────────────────────────────────────────┘    ║
   ║                                                          ║
   ║   ┌─────────────────────────────────────────────────┐    ║
   ║   │   WIZARD (bootstrap + re-config)                │    ║
   ║   └─────────────────────────────────────────────────┘    ║
   ║                                                          ║
   ╚══════════════════════════════════════════════════════════╝

   The UI does no orchestration. If it dies, the senate continues.
   The UI does two writes:
     1. Goal/mandate → bus topic "system/mandate"
     2. Charter edit → git commit pods/X/charter.md
```

---

## 15. Personas (experimental mode)

A style overlay; never affects voting or capability.

```
   ┌──────────────────────────────────────────────────────────┐
   │  Agent system prompt assembly                            │
   │  ────────────────────────────                            │
   │                                                          │
   │   ┌────────────────────────────────────────┐             │
   │   │  /conclave/primitives.md (read-only)      │  ← always   │
   │   └────────────────────────────────────────┘             │
   │                       +                                  │
   │   ┌────────────────────────────────────────┐             │
   │   │  charter.md (proposer-written)         │  ← always   │
   │   └────────────────────────────────────────┘             │
   │                       +                                  │
   │   ┌────────────────────────────────────────┐             │
   │   │  /conclave/personae/{name}.md             │  ← optional │
   │   │  (Cicero | Cato | Cassius | Brutus |   │             │
   │   │   Crassus | Seneca | Pliny | Tacitus | │             │
   │   │   Antony | Augustus | Gracchus | Vesta)│             │
   │   └────────────────────────────────────────┘             │
   │                                                          │
   │   → composed prompt at CLI launch                        │
   └──────────────────────────────────────────────────────────┘
```

A toggle in the Forum disables personas mid-flight. Useful both as fun and as epistemic diversity — Cassius and Pliny catch different bugs in a proposed contract.

---

## 16. Modularity audit — counting moving parts

```
   ╔════════════════════════════════════════════════════════════╗
   ║  COMPONENTS IN A RUNNING CONCLAVE                          ║
   ╠════════════════════════════════════════════════════════════╣
   ║                                                            ║
   ║  Custom platform services:                                 ║
   ║    1.  Observer (FastAPI + Postgres)                       ║
   ║    2.  Senate ledger (FastAPI + SQLite or same Postgres)   ║
   ║    3.  Forum UI (frontend + thin backend)                  ║
   ║    4.  Harness (per-pod sidecar, identical instances)      ║
   ║                                                            ║
   ║  Chosen backends (per wizard):                             ║
   ║    5.  Bus            (NATS | Redis Streams)               ║
   ║    6.  Doc backend    (GH Issues | Obsidian)               ║
   ║    7.  Trace pipeline (OTel/Tempo | Linkerd)               ║
   ║    8.  Log pipeline   (stdout | Loki+Grafana)              ║
   ║    9.  Notification   (Email | Telegram)                   ║
   ║   10.  Repo host      (GitHub | GitLab)                    ║
   ║   11.  CI/CD          (GH Actions | GitLab CI)             ║
   ║   12.  Runtime / IaC  (Compose | k3d/Terraform)            ║
   ║                                                            ║
   ║  Per pod:                                                  ║
   ║   13.  Container with harness + CLI                        ║
   ║                                                            ║
   ╚════════════════════════════════════════════════════════════╝

   MCP surface:   4 servers · 1 inbound event stream
   Adapters:      one per slot, ≥2 implementations each
   Custom code:   ~ 3 services + harness + UI · everything
                  else is off-the-shelf
```

```
   ╔════════════════════════════════════════════════════════════╗
   ║  WHAT'S DELIBERATELY ABSENT                                ║
   ╠════════════════════════════════════════════════════════════╣
   ║   ✗  Orchestrator / supervisor / router                    ║
   ║   ✗  Separate registry service (observer covers it)        ║
   ║   ✗  Per-pod yaml manifests                                ║
   ║   ✗  Custom shell primitives (all MCP)                     ║
   ║   ✗  Sharing flags on artifacts (monorepo = shared)        ║
   ║   ✗  Founder privileges                                    ║
   ║   ✗  Synchronous user dependencies                         ║
   ║   ✗  Hard-coded backend choices                            ║
   ╚════════════════════════════════════════════════════════════╝
```

---

## 17. Open decisions

These don't block design-doc completion but need answers before implementation.

```
┌─────────────────────────────────────────────────────────────────┐
│  Pi-MCP verification (slot 6 candidate B)                       │
│  ─────────────────────────────────────                          │
│  Confirm: does target Pi CLI support MCP client natively?       │
│  If no: drop to Claude-Code-only at alpha, or swap candidate    │
│  B for Codex / Goose / Continue.                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Demo project (stresses the platform)                           │
│  ──────────────────────────────────                             │
│  Candidates:                                                    │
│    • TODO API (auth + frontend + persistence; 4-5 pods)         │
│    • URL shortener with analytics (3-4 pods)                    │
│    • Conclave-rebuild itself (dogfooding, but circular)         │
│  Recommendation: defer until skeleton works.                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Next deliverable                                               │
│  ────────────────                                               │
│    • Founder seed prompt (the iusiurandum)                      │
│    • MCP server signatures fleshed to MCP-tool definitions      │
│    • Repo skeleton + Compose first                              │
│    • Parallel (inverted-copilot)                                │
│  Recommendation: parallel.                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 18. Alpha scope summary

```
┌──────────────────────────────────────────────────────────────────┐
│  IN SCOPE                                                        │
├──────────────────────────────────────────────────────────────────┤
│  • 2 candidates per slot wired with adapter pattern              │
│    (slots 1, 2, 3, 4, 5, 7a, 7b, 8; slot 6 pending Pi verif)     │
│  • 4 MCP servers (coms, senate, decisions, state) + events       │
│  • 4 voting strategies                                           │
│  • Observer + Postgres + OTel ingest + annotation push           │
│  • Wizard with Quickstart preset                                 │
│  • Pixel-art Forum UI with read-only views                       │
│  • Personas as experimental toggle                               │
│  • Founder bootstrap as N=1 vote                                 │
│  • Restitutio for revived agents                                 │
│  • Project portability (monorepo + docs reconstruct any platform)│
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  OUT OF SCOPE (alpha)                                            │
├──────────────────────────────────────────────────────────────────┤
│  • Auth / authz                                                  │
│  • Cost governance beyond user budgets                           │
│  • Cross-pod integration tests as a platform feature             │
│  • Live mid-flight stack swap                                    │
│  • RAG over decisions (search is grep at alpha)                  │
│  • Cloud BYO presets                                             │
│  • Multi-project / multi-tenant Conclave                         │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  DEFERRED TO BETA                                                │
├──────────────────────────────────────────────────────────────────┤
│  • Slot 9: vector search behind decisions.search                 │
│  • Per-slot health-check semantics standardized                  │
│  • Audit log of charter edits                                    │
│  • Skill versioning (today: latest-commit-wins)                  │
│  • Persistent CLI session migration across stack swaps           │
└──────────────────────────────────────────────────────────────────┘
```
