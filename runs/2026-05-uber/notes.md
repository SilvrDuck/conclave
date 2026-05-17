# Pass-2 → Pass-4 — Design Uber

The realize → analyze → nuke loop ran four times on 2026-05-17. Pass-2
and pass-3 were diagnostic; pass-4 reached spec/08 §3 admission.

---

## Pass-2 (rev v2 + #36 + #38 + #39 + #40 + #42)

**Outcome**: agent's first turn returned `tokens_in=0 tokens_out=0`,
swarm stalled at boot.

Fixes filed and merged:
- **#98 (G18)** — Claude CLI requires `--verbose` with
  `--print --output-format=stream-json`; without it the subprocess
  exits silently rc=0.
- **#99 (G19)** — `SendDirectMessage` from Augustus never reached the
  recipient pod. `ComsService.post_message` now fans Augustus DMs out
  to `conclave.inbox.<recipient>` on core NATS so the pod's bootstrap
  inbox subscription actually fires.
- **#100 (G20)** — `/ingest/pod-activity` 404 spam from an unknown
  client; backlog (cosmetic).
- **#101 (G21)** — HealthWatcher false-flipped a live container to
  `runtime_status=stopped` after 2 min of OTel silence; deferred.

---

## Pass-3 (rev v2 + G18 fix)

**Outcome**: turn 1 still rc=0 with no events. Discovered two more
bugs in pods/_template:

1. Claude CLI refuses `--dangerously-skip-permissions` when the
   process runs as **root** ("cannot be used with root/sudo
   privileges for security reasons"). Pod container had been running
   as root.
2. The bootstrap passed the prompt as a trailing positional argv,
   but `--add-dir <directories...>` is variadic and slurps the prompt
   as another directory. Claude exited with "Input must be provided
   either through stdin or as a prompt argument".

Both fixed in PR #46:
- `pods/_template/Dockerfile` creates a `pod` user (uid 1000) +
  `USER pod` + `HOME=/home/pod`; compose template binds credentials
  at `/home/pod/.claude/.credentials.json`. (Also closes kanban #97.)
- `bootstrap._run_claude` pipes the prompt via stdin so argv parsing
  can't confuse it.

While there, added a 5-minute annotation reconciler (#89) that
re-publishes RequestAnnotation for un-annotated endpoints whose
first reactor fire was lost.

---

## Pass-4 (rev v2 + #46)

**Outcome**: the swarm actually moved. pod-a078fee2db70 spawned,
read the proclamation, decided its role, proposed its own admission
via `consensus_omnium` with N=1 eligibility, voted yes on its own
proposal, the senate auto-closed the proposal as approved within
~10 s, and the decisions context sealed adr-951807ef1be6.

Wall-clock timeline:

| t (s) | event |
|------|-------|
| 0 | `ProclamationIssued` |
| 8 | `PodContainerStarted` |
| 8 | `AgentBooted` · `PodCharterLoaded` · `AgentSessionStarted` |
| 20 | first MCP tool calls: `state.proclamations`, `state.members`, `pods.list_pods` |
| 20 | text: "I see the proclamation: design Uber with riders, drivers, and surge" |
| 20 | `mcp__senate__propose_admission` — proposes as **simulator** role |
| 20 | `ProposalOpened(prop-d94d5ba25374, kind=admission, strategy=consensus_omnium)` |
| 20 | `BallotCast(yes, auto: proposer endorsement)` |
| 20 | `ProposalClosed(outcome=approved)` |
| 20 | `PodAdmitted` |
| 20 | `DecisionSealed(adr-951807ef1be6)` |
| 24 | `AgentTurnEnded` rc=0, num_turns=5, duration 15s |

§1, §2, §3 of spec/08 acceptance demonstrated cleanly. The first
agent turn captured tool calls, sealed a real decision, and the
N=1 admission auto-pass works without any special-case code path —
exactly the v2 vision (spec/08 §3).

### Personality observation

Quoted verbatim from the agent's `text` content (Witness drop-cap
material):

> *"I'm reading my charter and bootstrapping as a platform agent. Let
> me first explore the current state of the conclave and identify my
> role."*

> *"I see the proclamation: design Uber with riders, drivers, and
> surge pricing. As the bootstrapping agent, I should propose my own
> admission. Looking at the system, I see no other pods exist yet."*

The agent picked **simulator** as its role — directly motivated by
the proclamation's "One pod is the real-world simulator" mandate.
Its charter for admission was:

> "The simulator is the real-world authority for Uber. It generates
> rider requests with origin/destination/time, simulates driver
> locations, movement, and availability, adjudicates trip outcomes,
> manages time progression, exposes the current world state."

That's real product reasoning encoded in the admission proposal,
not boilerplate.

### New gap discovered: G22 — session resume fails

A follow-up DM ("rename yourself + propose other pods") triggered a
second turn that died immediately with `--resume <session_id>` →
"No conversation found with session ID". Claude CLI couldn't find
the cached session id on disk because `$HOME/.claude` in the pod is
basically read-only (only the credential file is mounted).

Hotfix in bootstrap: on rc=1, clear the cached `_session_id` so the
next turn starts fresh. Commit on the same branch as the pass-4
notes; will be folded into pass-5.

---

## §1–§11 acceptance status

| § | Criterion | Pass-4 |
|---|---|---|
| §1 | empty-state, one write affordance, no zero counters | ✓ |
| §2 | proclamation card within 3 s | ✓ (~1 s) |
| §3 | first-pod renames itself | ✗ DM-triggered second turn failed (G22) |
| §3 | admission proposal | ✓ |
| §3 | N=1 auto-pass | ✓ |
| §3 | admission seals a decision | ✓ |
| §4 | three of four strategies fire | ✗ only consensus_omnium fired |
| §5 | 5–10 pods admitted | ✗ only one (simulator) |
| §6 | live token stream + tool-call rendering | ✓ (stream-json events captured in `agent_turns`) |
| §7–§10 | depend on §5 multi-pod scenarios | ✗ pending |
| §11 | ResetState | ✓ (verified pre-pass) |

§4 / §5 / §7–§10 need more pods — which depend on the simulator
either fanning out admission proposals itself (it didn't, at
haiku/low effort) or Augustus driving the DM-triggered fan-out
(currently blocked by G22).

---

## Loop status

The loop hasn't terminated yet — pass-4 filed G22, which needs a
hotfix (already coded in this commit). Pass-5 will run after merge.

**Realistic budget note**: the swarm runs on Augustus's Anthropic
account, which `rate_limit_info.overageStatus` reports as
`"rejected"`/`"out_of_credits"`. Pass-4 still completed because the
five-hour primary quota was within bounds, but a longer multi-pod
run may hit the wall.
