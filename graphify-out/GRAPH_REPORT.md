# Graph Report - .  (2026-05-16)

## Corpus Check
- 190 files · ~55,478 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1223 nodes · 2015 edges · 73 communities (57 shown, 16 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 326 edges (avg confidence: 0.72)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Domain Models (pydantic)|Domain Models (pydantic)]]
- [[_COMMUNITY_Config + Slot Enums|Config + Slot Enums]]
- [[_COMMUNITY_Event Stream|Event Stream]]
- [[_COMMUNITY_CLI Adapters (PiClaude)|CLI Adapters (Pi/Claude)]]
- [[_COMMUNITY_In-Memory Bus|In-Memory Bus]]
- [[_COMMUNITY_Harness Dual-Write|Harness Dual-Write]]
- [[_COMMUNITY_Test Fakes|Test Fakes]]
- [[_COMMUNITY_Bus Protocol|Bus Protocol]]
- [[_COMMUNITY_Compose  k3d Runtime|Compose / k3d Runtime]]
- [[_COMMUNITY_Voting Strategies|Voting Strategies]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 72|Community 72]]

## God Nodes (most connected - your core abstractions)
1. `AdapterNotImplementedError` - 37 edges
2. `InMemoryBus` - 23 edges
3. `PiCli` - 21 edges
4. `utc_now()` - 20 edges
5. `Credentials` - 18 edges
6. `MandateIn` - 17 edges
7. `ObserverDeps` - 17 edges
8. `compilerOptions` - 17 edges
9. `InMemoryDocs` - 16 edges
10. `compilerOptions` - 16 edges

## Surprising Connections (you probably didn't know these)
- `platform/README.md (placeholder)` --placeholder_for--> `Conclave primitives — MCP reference`  [AMBIGUOUS]
  platform/README.md → primitives.md
- `Pluggability slots (≥2 backends per slot)` --semantically_similar_to--> `Intentionally absent components`  [INFERRED] [semantically similar]
  spec/brainstrom.md → primitives.md
- `mcp-coms service` --implements--> `coms MCP server (conversation)`  [INFERRED]
  infra/compose.yaml → primitives.md
- `NATS bus service` --transport_for--> `coms MCP server (conversation)`  [INFERRED]
  infra/compose.yaml → primitives.md
- `mcp-senate service` --implements--> `senate MCP server (collective decisions)`  [INFERRED]
  infra/compose.yaml → primitives.md

## Hyperedges (group relationships)
- **Persona library — 12 Roman style overlays** — personae_cicero, personae_cato, personae_cassius, personae_brutus, personae_crassus, personae_seneca, personae_pliny, personae_tacitus, personae_antony, personae_augustus, personae_gracchus, personae_vesta, concept_persona_library [EXTRACTED 1.00]
- **MCP surface (4 servers + events stream)** — primitives_coms, primitives_senate, primitives_decisions, primitives_state, primitives_events_stream, primitives_mcp_surface [EXTRACTED 1.00]
- **Four voting strategies ship in alpha** — voting_strategies_majority, voting_strategies_supermajority, voting_strategies_consensus_omnium, voting_strategies_sortition, voting_strategies [EXTRACTED 1.00]

## Communities (73 total, 16 thin omitted)

### Community 0 - "Domain Models (pydantic)"
Cohesion: 0.05
Nodes (75): BaseModel, Strongly-typed identifiers used across the platform.  These are deliberately pla, Core platform types: config, ids, models, events. Pure data — no IO., Adr, AgendaItem, AgendaSection, AgendaSnapshot, Ballot (+67 more)

### Community 1 - "Config + Slot Enums"
Cohesion: 0.06
Nodes (54): BusSlot, CISlot, CliSlot, ConclaveConfig, DocsSlot, Limits, LogSlot, NotifyConfig (+46 more)

### Community 2 - "Event Stream"
Cohesion: 0.06
Nodes (46): AgendaUpdated, AnnotationRequested, _BaseEvent, ContractChangeProposed, CouncilInvited, DirectMessage, EventEnvelope, EventType (+38 more)

### Community 3 - "CLI Adapters (Pi/Claude)"
Cohesion: 0.07
Nodes (31): AdapterError, CliSession, CLI runtime adapter — slot 6. Pi (wired) or Claude Code (stub).  The harness dri, Opaque handle to a running CLI process + its session id for --resume., Claude Code CliAdapter — stub.  The alpha wires Pi only. This stub satisfies the, _drain_stdout(), PiCli, PiStartupError (+23 more)

### Community 4 - "In-Memory Bus"
Cohesion: 0.05
Nodes (25): Bus / transport adapter — slot 2.  Backs `coms` MCP and the harness inbox loop., Subscription, InMemoryBus, _InMemSub, In-memory bus — for tests and the founder-only quickstart path.  Real semantics:, Process-local pub/sub. Topics with `*` are not supported — exact match only., Used for request/reply. Topic gets exactly one responder., _client() (+17 more)

### Community 5 - "Harness Dual-Write"
Cohesion: 0.06
Nodes (26): parse_agenda(), agenda.md parser.  Format (per spec §4.1):      ## doing     - [alice-42] pagina, DualWriter, Dual-write: filesystem (git commit) + observer ingest.  The harness watches `pod, EndpointEntry, _finalize(), parse_endpoints(), endpoints.md parser. One section per HTTP endpoint; free-form annotation body. (+18 more)

### Community 6 - "Test Fakes"
Cohesion: 0.05
Nodes (13): _FakeBus, _FakeCI, _FakeCli, _FakeDocs, _FakeLog, _FakeNotify, _FakeRepo, _FakeRuntime (+5 more)

### Community 7 - "Bus Protocol"
Cohesion: 0.04
Nodes (14): BusAdapter, Async pub/sub with at-least-once delivery for inbox topics., Request/reply on `topic`. Adapter MUST enforce timeout (no unbounded wait)., CliAdapter, Push one event into the CLI's stdin (or via MCP, depending on impl)., LogAdapter, Log adapter — slot 7b. Streams per-pod stdout to the Forum UI., Loki LogAdapter — stub for alpha. See `stdout` for the wired pair. (+6 more)

### Community 8 - "Compose / k3d Runtime"
Cohesion: 0.12
Nodes (23): PodStatus, Runtime / IaC adapter — slot 1.  Owns the lifecycle of pod containers and the su, ComposeCommandError, DockerComposeRuntime, _empty_compose(), Docker Compose RuntimeAdapter — slot 1 alpha implementation.  Maintains an `infr, _service_def(), k3d + Terraform RuntimeAdapter — stub for alpha. (+15 more)

### Community 9 - "Voting Strategies"
Cohesion: 0.13
Nodes (36): VotingStrategy, approve(), consensus_omnium(), draw_sortition_panel(), evaluate(), majority(), open(), Voting strategies — pure functions over (ballots, voters, context) → result.  Ad (+28 more)

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (16): AdapterError, Commit, Mount, MountMode, Shared adapter primitives — mounts, processes, exceptions., Base class for adapter-layer errors., LocalGitRepo, NotImplementedError (+8 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (21): main(), conclave-mcp-coms — runs the coms MCP over streamable HTTP on PORT (default 8002, ComsDeps, coms MCP — conversation primitives. Backed by BusAdapter + observer ingest., new_chatroom_id(), new_council_id(), new_id(), new_message_id() (+13 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (26): ApiError, getJson(), postJson(), AdrSchema, AdrsOut, AgendaItem, AgendaItemSchema, AgendaOut (+18 more)

### Community 13 - "Community 13"
Cohesion: 0.13
Nodes (25): AgendaItemRow, Base, CallEdgeRow, ChatroomRow, EndpointRow, MemberRow, MessageRow, ProposalRow (+17 more)

### Community 14 - "Community 14"
Cohesion: 0.07
Nodes (28): dependencies, react, react-dom, swr, zod, devDependencies, eslint, @eslint/js (+20 more)

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (11): CIAdapter, CI/CD adapter — slot 4. Coupled with repo (GitHub→Actions, GitLab→GitLab CI)., WorkflowConclusion, WorkflowRun, GitHubActionsCI, _map_conclusion(), GitHubActionsCI — generates `.github/workflows/<pod>.yml` and writes via repo., GitLab CI adapter — stub for alpha. See `github_actions` for the wired pair. (+3 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (14): NotifyLevel, Notification adapter — slot 8. Outbound user-facing pings., EmailNotify, Email NotifyAdapter — stub for alpha. See `stdout` / `telegram` for wired pairs., Stdout NotifyAdapter — fallback when Telegram isn't configured., StdoutNotify, Telegram NotifyAdapter — degrades to stdout when token/chat-id absent., If `token` is None, every call falls through to StdoutNotify. (+6 more)

### Community 17 - "Community 17"
Cohesion: 0.15
Nodes (13): DeclarativeBase, _AdrRow, _apply_sqlite_pragmas(), _Base, SqliteDocs — DocsAdapter backed by a single SQLite file.  The senate-ledger and, busy_timeout lets concurrent writers (senate-ledger + mcp-decisions)     block p, SqliteDocs, _to_adr() (+5 more)

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (7): Trace adapter — slot 7a. Feeds observer's call-graph projection., SpanEvent, TraceAdapter, Linkerd TraceAdapter — stub for alpha. See `otel_tempo` for the wired pair., OtelTempoTrace, OTel-collector + Tempo TraceAdapter.  Pods export spans to the OTel collector at, _spans_from_trace()

### Community 19 - "Community 19"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 20 - "Community 20"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 21 - "Community 21"
Cohesion: 0.18
Nodes (17): Senate ledger (FastAPI + SQLite), Forum View redesign brainstorm, Clay→stone ADR placeholder pattern, Pi turn telemetry, Pod slide-out panel, Proclamation (Edictum) input, Senate band UI (proposal cartouches), Spawner seeding (founder + placeholder) (+9 more)

### Community 22 - "Community 22"
Cohesion: 0.17
Nodes (15): _email(), _gitlab_repo(), _k3d(), _linkerd(), _loki(), _obsidian(), Stub adapters: construct cleanly, raise AdapterNotImplementedError on use, satis, _redis() (+7 more)

### Community 23 - "Community 23"
Cohesion: 0.17
Nodes (10): listMembers(), Member, ITEMS, Nav(), Props, ViewKey, VIEWS, rootEl (+2 more)

### Community 24 - "Community 24"
Cohesion: 0.19
Nodes (4): AdapterNotImplementedError, Raised by stub adapters. Catchable as either AdapterError or NotImplementedError, RedisStreamsBus, GitLabRepo

### Community 25 - "Community 25"
Cohesion: 0.22
Nodes (15): Charter template, ADR (Architecture Decision Record), Charter (pod system prompt), Persona library (style overlays), Iusiurandum — founder's oath, Brutus persona, Cato persona, Cicero persona (+7 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (13): type, url, type, url, mcpServers, coms, decisions, senate (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.26
Nodes (5): GitHubIssuesDocs, _id_to_number(), _number_to_id(), GitHub-Issues-backed DocsAdapter.  Each ADR is a GitHub issue with the `adr` lab, _to_adr()

### Community 28 - "Community 28"
Cohesion: 0.16
Nodes (4): ObserverClient, client(), _FakeObserverClient, End-to-end-ish tests for the senate ledger over its HTTP surface.  Uses InMemory

### Community 29 - "Community 29"
Cohesion: 0.15
Nodes (10): Bus, DEFAULTS, Doc, Logs, Notify, Repo, Runtime, Trace (+2 more)

### Community 30 - "Community 30"
Cohesion: 0.18
Nodes (13): callers_of (call graph), Contract change proposal, EndpointKey (METHOD /path), Forum UI (Roman pixel-art frontend), Observer service (Postgres-backed), Forum UI dev service, Observed truth over declared truth, Cassius persona (+5 more)

### Community 31 - "Community 31"
Cohesion: 0.21
Nodes (13): Project completion proposal, Exile (pod removal), Proposal (senate vote), Revival (exiled pod restoration), Founder bootstrap (N=1 vote), Symmetry (no founder privileges), Antony persona, senate MCP server (collective decisions) (+5 more)

### Community 32 - "Community 32"
Cohesion: 0.22
Nodes (7): InMemoryDocs, InMemoryDocs: CRUD + search + per-pod filter., test_inmemory_satisfies_protocol(), test_list_filters_by_pod_and_sorts_recent_first(), test_read_missing_returns_none(), test_search_matches_title_or_body(), test_write_read_round_trip()

### Community 33 - "Community 33"
Cohesion: 0.17
Nodes (11): args, command, env, type, mcpServers, chrome-devtools, playwright, args (+3 more)

### Community 34 - "Community 34"
Cohesion: 0.24
Nodes (8): Adr, getJsonSenate(), listAdrs(), listOpenProposals(), Proposal, ActivityPanel(), Event, snapshot()

### Community 35 - "Community 35"
Cohesion: 0.24
Nodes (7): Chatroom, listChatrooms(), Props, StoneTablet(), Council(), PLACEHOLDER_ADRS, Tabularium()

### Community 36 - "Community 36"
Cohesion: 0.2
Nodes (3): ClaudeCodeCli, test_claude_code_satisfies_cli_adapter_protocol(), test_claude_code_start_raises_not_implemented()

### Community 37 - "Community 37"
Cohesion: 0.31
Nodes (5): AgendaSnapshot, drawDomus(), hashString(), spritePosition(), Forum()

### Community 38 - "Community 38"
Cohesion: 0.36
Nodes (8): session_scope(), Repository layer against in-memory aiosqlite., test_mark_item_completed_removes_from_doing(), test_record_call_and_callers_of(), test_replace_agenda_replaces_atomically(), test_upsert_chatroom_round_trip(), test_upsert_endpoint_first_call_is_new(), test_upsert_member_is_idempotent()

### Community 39 - "Community 39"
Cohesion: 0.53
Nodes (9): NATS bus service, Founder pod container, mcp-coms service, mcp-decisions service, mcp-senate service, mcp-state service, Observer service, Senate ledger service (+1 more)

### Community 40 - "Community 40"
Cohesion: 0.22
Nodes (9): First-100-lines mandate, Harness (per-pod sidecar), Pod (agent + service container), User as Emperor (Augustus), Augustus persona, Agenda contract (doing/next/blocked-on), Endpoint annotation flow, Dual-write pattern (Postgres cache + markdown truth) (+1 more)

### Community 42 - "Community 42"
Cohesion: 0.36
Nodes (8): Chatroom, Council (chatroom with summary), Crassus persona, Gracchus persona, Vesta persona, coms MCP server (conversation), shared/ promotion convention, Council line drawing (active comms)

### Community 43 - "Community 43"
Cohesion: 0.29
Nodes (4): main(), conclave-mcp-decisions — runs the decisions MCP over streamable HTTP., DecisionsDeps, decisions MCP — ADR write / read / search / list. Backed by DocsAdapter.

### Community 45 - "Community 45"
Cohesion: 0.25
Nodes (3): conclave-mcp-senate — runs the senate MCP over streamable HTTP., senate MCP — proposals + ballots. Thin client over the senate ledger., SenateDeps

### Community 47 - "Community 47"
Cohesion: 0.29
Nodes (3): In-memory DocsAdapter — tests and lightweight founder-only quickstart., ObsidianVaultDocs — stub for alpha. See `github_issues` / `inmemory` for wired p, SenateProxyDocs — DocsAdapter that delegates to senate-ledger's /adrs REST.  Thi

### Community 49 - "Community 49"
Cohesion: 0.33
Nodes (3): GitLabCI, _gitlab_ci(), test_gitlab_ci_raises()

### Community 52 - "Community 52"
Cohesion: 0.53
Nodes (4): container_running(), handle_vote_closed(), launch_pod_container(), seed_pod_skeleton()

### Community 53 - "Community 53"
Cohesion: 0.4
Nodes (5): CLAUDE.md project instructions, Everything async constraint, Dev philosophy, Tooling rules, Working style

### Community 56 - "Community 56"
Cohesion: 0.5
Nodes (3): enabledMcpjsonServers, permissions, allow

### Community 58 - "Community 58"
Cohesion: 0.5
Nodes (4): Pluggability slots (≥2 backends per slot), Three-layer architecture (project/runtime/source), Intentionally absent components, Conclave vision: orchestrator-free, vote-driven

### Community 59 - "Community 59"
Cohesion: 0.83
Nodes (3): get(), main(), post()

## Ambiguous Edges - Review These
- `Conclave primitives — MCP reference` → `platform/README.md (placeholder)`  [AMBIGUOUS]
  platform/README.md · relation: placeholder_for

## Knowledge Gaps
- **265 isolated node(s):** `type`, `command`, `args`, `env`, `type` (+260 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Conclave primitives — MCP reference` and `platform/README.md (placeholder)`?**
  _Edge tagged AMBIGUOUS (relation: placeholder_for) - confidence is low._
- **Why does `InMemoryBus` connect `In-Memory Bus` to `Community 57`, `Community 11`, `Community 28`, `Harness Dual-Write`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Why does `Subscription` connect `In-Memory Bus` to `Community 24`, `Bus Protocol`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Why does `AdapterNotImplementedError` connect `Community 24` to `Community 36`, `Community 10`, `Community 16`, `Community 49`, `Community 50`, `Community 51`, `Community 54`, `Community 55`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `AdapterNotImplementedError` (e.g. with `.connect()` and `.close()`) actually correct?**
  _`AdapterNotImplementedError` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `InMemoryBus` (e.g. with `Subscription` and `main()`) actually correct?**
  _`InMemoryBus` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `PiCli` (e.g. with `CliSession` and `run()`) actually correct?**
  _`PiCli` has 11 INFERRED edges - model-reasoned connections that need verification._