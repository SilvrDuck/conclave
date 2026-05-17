# Pass-2 → Pass-5 — Design Uber

Five realize → analyze → nuke passes ran on 2026-05-17. Passes 2–4
were diagnostic; pass-5 reached spec/08 §3 rename + multi-pod
admission proposals. Loop has not yet terminated (more gaps still
open) but the trajectory is now clearly upward.

---

## Pass-2 (rev v2 + #36 + #38 + #39 + #40 + #42)

**Outcome**: agent's first turn returned `tokens_in=0 tokens_out=0`,
swarm stalled at boot. Filed and merged:
- **#98 (G18)** — Claude CLI requires `--verbose` with `--print
  --output-format stream-json`.
- **#99 (G19)** — `SendDirectMessage` from Augustus never reached
  the recipient pod inbox. `ComsService.post_message` now fans
  Augustus DMs out to `conclave.inbox.<recipient>`.
- **#100 (G20)** — `/ingest/pod-activity` 404 spam from a stale
  client; observer now 204-catches.
- **#101 (G21)** — HealthWatcher false-flipped live containers
  to `stopped` on span silence; now flips `agent_state` instead.

## Pass-3 (rev v2 + G18 fix)

Discovered two more bugs in pods/_template:
1. Claude CLI refuses `--dangerously-skip-permissions` when run as
   root. Pod was running as root.
2. `--add-dir` is variadic and slurped the prompt as a directory.

Both fixed in PR #46:
- pod runs as `pod` user (uid 1000) via Dockerfile + USER directive
- prompt now piped via stdin instead of trailing argv

## Pass-4 (rev v2 + #46)

Pod spawned, read proclamation, picked "simulator" role, proposed
its own admission via `consensus_omnium` with N=1 eligibility, voted
yes, the senate auto-closed approved, decisions sealed
adr-951807ef1be6. All in ~20s. **§1, §2, §3 (admission half) all
green.**

Followup turn failed because `--resume <session_id>` returned "No
conversation found" — `/home/pod/.claude` was created by Docker as
root and Claude can't write its session state there. Filed as
#102 (G22). Hotfix in the same commit: clear cached session_id on
rc=1. Proper fix in PR #48 (Dockerfile pre-creates the dir
pod-owned).

## Pass-5 (rev v2 + #46 + #48 + #49 + #50)

The simulator pod, after a DM nudge:
1. **Renamed itself** to `simulator` via `mcp__pods__rename_self`
   (§3 ✓).
2. **Proposed admission of four new pods** — `rider-app`,
   `driver-app`, `dispatch`, `pricing` — each via
   `mcp__senate__propose_admission` with proper charters that
   declare dependencies.

Verbatim charters the agent wrote:

> **rider-app** — *"Mobile/web frontend for riders to request
> trips, track driver location, and rate completed rides. Depends
> on: dispatch (trip requests), pricing (fare estimates), simulator
> (trip lifecycle)."*

> **dispatch** — *"Matchmaking service that routes incoming rider
> requests to available drivers and coordinates acceptances.
> Depends on: simulator (driver availability, location), pricing
> (incentives for acceptance)."*

That's real product reasoning. The agent grasped the system, picked
sensible role names, and articulated cross-pod dependencies.

### Sub-gap discovered, not yet filed

The simulator proposed each new pod with
`eligible_voters=[simulator, <new_pod_role>]` and
`strategy=consensus_omnium`. Two consequences:
- The new pods don't exist yet — they can't vote — so the proposals
  open and wait for the consensus_omnium quorum until the deadline.
- The candidate pod_ids are role names ("rider-app"), not minted
  `pod-<hex>` ids, so they don't satisfy the platform's pod-id
  convention.

This is more an *agent reasoning gap* than a platform gap: with a
more capable model the agent would either use `majority` (N=1
proposer) or wait for `mcp-pods` to mint the candidate first. The
platform supports "admission of a not-yet-registered pod" via
`mcp_pods.service.on_proposal_closed` (it inserts a placeholder
row), so the second consequence is fine. The first is honest
agent-prompting work, not a kanban platform task.

---

## §1–§11 acceptance, pass-5

| § | Criterion | Status |
|---|---|---|
| §1 | empty-state, one write affordance, no zero counters | ✓ |
| §2 | proclamation card within 3 s | ✓ (~1 s) |
| §3 | first-pod renames itself | ✓ (DM-triggered, pass-5) |
| §3 | admission proposal | ✓ |
| §3 | N=1 admission auto-passes | ✓ |
| §3 | admission seals a decision | ✓ |
| §4 | three of four strategies fire | partial — `consensus_omnium` only |
| §5 | 5–10 pods admitted | partial — 1 admitted + 4 proposed (unspawned candidates blocking quorum) |
| §6 | live OpenLLMetry stream + tool-call rendering | ✓ stream-json events parsed; usage now non-zero |
| §7–§10 | depend on §5 multi-pod | pending |
| §11 | ResetState | ✓ |

---

## Loop status

Five passes. Six platform-gaps discovered, four critical (G18, G19,
G21, G22) and two non-critical (G20, plus the implicit Dockerfile
non-root fix). All four critical gaps merged. Backlog still has 11
items — those count as platform-gaps for §14 loop closure but are
not pass-discovered.

**§4 multi-strategy and §5 multi-pod admission** are the
load-bearing remaining work for the golden run. They need either:
- a more capable agent model (sonnet+medium instead of haiku+low),
  which costs more on the user's Claude account; OR
- a better bootstrap initial prompt that walks the agent through
  the senate strategies and the admission-of-unspawned-candidate
  flow.

The Anthropic account is "out_of_credits" but pass-5 still ran
under the 5-hour primary quota. A multi-pod realize will probably
hit the wall before §5 closes.

Captured personality is real and substantial (see pass-5 charter
quotes). Spec/00's "see agents express their personality in
decisions" is met.
