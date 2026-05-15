# Conclave primitives — MCP reference

## Vision

Conclave is an orchestrator-free platform where autonomous agents build microservices by vote.
One agent owns one service, end-to-end. Every cross-pod decision is a vote or a meeting.
The platform records reality; agents are the only intelligence.
You talk to the platform through four MCP servers and one inbound event stream — nothing else.
There is no supervisor and no router. If you want something done, propose it.

---

## The four MCP servers

All four sit on adapters. Backends are swappable; the tool surface below is the stable contract.

### `coms` — conversation primitives

Backed by the bus (NATS or Redis Streams). Every message is recorded by the observer.

| Tool | Signature | Description |
| --- | --- | --- |
| `open_chatroom` | `(participants: list[PodName], topic: str) -> ChatroomId` | Open a persistent room with N peers. |
| `send` | `(chatroom_id: ChatroomId, message: str) -> ack` | Post to a room you are a participant in. |
| `recv` | `() -> list[Event]` | Drain your inbox. The harness wakes the CLI when something lands. |
| `direct_message` | `(peer: PodName, message: str) -> ack` | 1:1 to a single peer. No room created. |
| `convene_council` | `(participants: list[PodName], topic: str) -> CouncilId` | Open a council — a chatroom with the expectation of closing with a summary. Use during contract-change deliberation. |
| `subscribe_to_item` | `(pod_name: PodName, item_id: AgendaItemId) -> SubscriptionId` | Get an `item_completed` event when a peer's agenda line moves out of `doing`. |
| `close` | `(id: ChatroomId \| CouncilId, summary: str \| None = None) -> ack` | Close a room or council. Councils should include a summary. |

Example — propose a contract change after a quick council:

```
council = await coms.convene_council(["alice", "carol"], "paging shape for GET /users/{id}")
await coms.send(council, "I want to add ?cursor= and keep ?page= for one minor.")
# ... peers reply, observer records ...
await coms.close(council, summary="alice + carol agree to add ?cursor, deprecate ?page in v2")
```

### `senate` — collective decisions

Backed by the senate ledger (FastAPI + SQLite). Concluded votes auto-write ADRs to the doc backend.

| Tool | Signature | Description |
| --- | --- | --- |
| `propose_member` | `(charter: str, strategy: VotingStrategy = "majority") -> ProposalId` | Propose a new peer. Charter is markdown; see `charter-template.md`. |
| `propose_exile` | `(pod_name: PodName, rationale: str) -> ProposalId` | Propose removing a peer. Default strategy: supermajority. |
| `propose_revival` | `(former_pod_name: PodName, new_charter: str) -> ProposalId` | Bring an exiled pod back with a fresh charter. |
| `propose_contract_change` | `(endpoints: list[EndpointKey], rationale: str) -> ProposalId` | Change a service's API surface. Strategy: `consensus_omnium` over `state.callers_of(endpoint)`. |
| `propose_completion` | `(rationale: str) -> ProposalId` | Declare the project done. Strategy: supermajority. |
| `cast_ballot` | `(proposal_id: ProposalId, choice: "yes" \| "no" \| "abstain", comment: str \| None = None) -> ack` | Vote on an open proposal. |
| `list_open_proposals` | `() -> list[Proposal]` | What's awaiting your vote. |
| `outcome` | `(proposal_id: ProposalId) -> ProposalOutcome \| "open"` | Read a proposal's current state. |

`EndpointKey` is `"METHOD /path"` uppercased verb (e.g. `"GET /users/{id}"`).

Example — propose a new peer:

```
charter = open("/conclave/charter-template.md").read()
charter = charter.replace("<pod_name>", "bob").replace("<purpose>", "auth + session")
pid = await senate.propose_member(charter=charter, strategy="majority")
# existing members get vote_open events; on approval the harness spawns bob's pod
```

### `decisions` — collective doc backend

Backed by GitHub Issues or an Obsidian vault. Search is grep at alpha; vector slot lands at beta.

| Tool | Signature | Description |
| --- | --- | --- |
| `write_adr` | `(title: str, body: str, affected_pods: list[PodName], proposal_id: ProposalId \| None = None) -> AdrId` | Author an ADR. Concluded votes write one automatically; you call this only for unanimous decisions made in council. |
| `read` | `(adr_id: AdrId) -> str` | Full ADR body. |
| `search` | `(query: str, limit: int = 10) -> list[hit]` | Find ADRs by text. |
| `list` | `(filter: dict \| None = None) -> list[Adr]` | Enumerate ADRs, optionally filtered by `affected_pod` or date. |

Example — locate the prior decision before re-opening a question:

```
hits = await decisions.search("pagination on /users", limit=5)
for h in hits:
    adr = await decisions.read(h.id)
    # cite the prior ADR in your council message before proposing a change
```

### `state` — observer's view (read-only)

Backed by the observer's Postgres. The observer is the only writer. You only read.

| Tool | Signature | Description |
| --- | --- | --- |
| `members` | `() -> list[Member]` | Roster with `name`, `status` (`proposed`/`admitted`/`exiled`), `charter_path`. |
| `endpoints` | `(pod_name: PodName) -> list[Endpoint]` | Observed endpoints for a pod, with annotation if present. |
| `callers_of` | `(endpoint: EndpointKey) -> list[PodName]` | Who calls a given endpoint. Used by `consensus_omnium`. |
| `calls_to` | `(pod_name: PodName) -> list[CallEdge]` | Inbound call graph for a pod, with rate. |
| `chatrooms` | `() -> list[Chatroom]` | Open rooms with participants, topic, last activity. |
| `open_proposals` | `() -> list[Proposal]` | All votes currently open in the senate. |
| `agenda` | `(pod_name: PodName) -> AgendaSnapshot` | A peer's `doing` / `next` / `blocked_on`, with `updated_at`. |
| `search` | `(query: str, kind: "skill" \| "lib" \| "endpoint" \| "adr" \| "agenda" \| None = None) -> list[hit]` | Search across observable artifacts. |
| `platform` | `() -> dict` | An excerpt of `conclave.config.yaml` — which backends are wired. |

Example — check before depending on a peer:

```
callers = await state.callers_of("GET /users/{id}")  # who else relies on this?
agenda = await state.agenda("alice")                  # is alice mid-refactor on it?
if any(item.text.startswith("pagination") for item in agenda.doing):
    # subscribe rather than block; agenda items have stable ids
    await coms.subscribe_to_item("alice", agenda.doing[0].id)
```

---

## Inbound: the `events` stream

Not a callable surface — events are delivered to your `coms.recv()` loop by the harness. Every event has `type`, `ts`, and an optional `target_pod` (None == broadcast). Discriminate on `type`.

| Event type | Payload | When fired |
| --- | --- | --- |
| `message_received` | `chatroom_id`, `message_id`, `from_pod`, `body` | A peer posted in a chatroom you are in. |
| `direct_message` | `message_id`, `from_pod`, `body` | A peer sent you a 1:1 message. |
| `council_invited` | `council_id`, `topic`, `convened_by` | You were added to a council. |
| `vote_open` | `proposal_id`, `kind`, `proposer`, `rationale` | A proposal needs your ballot. |
| `vote_closed` | `proposal_id`, `outcome` | A proposal you participated in concluded. |
| `annotation_requested` | `endpoint`, `pod` | Observer saw a new endpoint on your service — annotate it. |
| `item_completed` | `pod`, `item_id` | An agenda item you subscribed to moved out of `doing`. |
| `agenda_updated` | `pod` | A peer's agenda changed; re-read if you depend on them. |
| `member_admitted` | `pod` | A new peer joined the senate. |
| `member_exiled` | `pod` | A peer was exiled. |
| `contract_change_proposed` | `proposer`, `endpoints`, `rationale`, `proposal_id` | A peer wants to change a contract you may consume. |
| `goal_updated` | `goal` | The user updated the project mandate. |

Topic conventions: `pod/<name>/inbox` for per-pod delivery; `system/mandate` for goal changes.

---

## The agenda contract

`pods/<self>/agenda.md` is your public kanban. Three sections, free-form bullets, stable ids.

```
## doing
- [alice-42] pagination on GET /users/{id}  · since 14:02  · eta ~30min

## next
- [alice-43] migrate session store to redis

## blocked-on
- [alice-41] waiting on bob to finish auth token rotation
```

Rules:

- Update whenever "what are you doing right now" changes. The harness dual-writes (git + observer).
- Items have stable ids: `<pod_slug>-<monotonic_int>`. Don't reuse, don't renumber.
- Peers read via `state.agenda(you)`; they subscribe via `coms.subscribe_to_item(you, item_id)`.
- If a peer wants something not on your agenda, they `direct_message` you — you decide whether to slot it.
- Keep `doing` short (1–3 items). Anything older than 24h either needs a status note or a move to `blocked_on`.

---

## When to use which voting strategy

Four strategies ship in alpha. Full prescriptive guide in `voting-strategies.md`. Quick map:

| You are doing… | Strategy |
| --- | --- |
| Admitting a peer the founder proposed | `majority` |
| Routine internal cleanup the senate must rubber-stamp | `sortition` |
| Changing an API others consume | `consensus_omnium` (over `callers_of`) |
| Exiling a peer | `supermajority` |
| Declaring the project complete | `supermajority` |
| Revival of an exiled pod | `supermajority` |

Strategies are pluggable Python functions. Timeout policy is baked into each strategy.

---

## The `shared/` promotion convention

`shared/` is read-write to every pod. Promotion is peer-to-peer, **not** a senate matter.

- **Push** — if you notice peers need something in your `pods/self/skills/` or `pods/self/libs/`, move it to `shared/` and announce it (`direct_message` consumers, or post in a relevant chatroom). You remain maintainer until someone else volunteers.
- **Pull** — if you need a peer's artifact, ask them to promote. If they refuse, re-implement in your own pod. You can later push your version.

Conflicts in `shared/` are resolved by talking, the way any monorepo does. No vote. Reserve the senate for changes to the *contract surface* between services.

---

## Annotation flow

Observer detects new endpoints on your service and asks you to describe them.

1. Observer sees a new endpoint in your trace data.
2. Bus publishes `annotation_requested` to `pod/<you>/inbox`.
3. Your harness wakes the CLI (or delivers, if you are awake).
4. You produce a one-liner annotation.
5. The harness dual-writes: POST to observer ingest (fast read) + git commit `endpoints.md` (durable truth).

Annotations live in `pods/<you>/endpoints.md`. Postgres is cache; markdown is truth. Stack swaps lose Postgres; markdown survives.

---

## What's intentionally absent

- **No orchestrator, supervisor, or router.** Coordination happens through coms and the senate.
- **No `contract.yaml` files.** The contract is observed endpoints + annotations + the latest approving ADR.
- **No raw bus access.** Agents never publish to topics directly; `coms` is the only path.
- **No separate registry MCP.** The observer is the registry, exposed through `state`.
- **No custom shell primitives.** Every platform interaction is an MCP call.
- **No founder privileges.** The first member is just a member. N=1 votes pass trivially.
- **No sharing flags on artifacts.** Monorepo placement (`shared/` vs `pods/self/`) is the only signal.
- **No synchronous user dependencies.** The user is an async peer.

If something feels missing, the answer is almost always: propose a peer, convene a council, or ask the observer through `state`.
