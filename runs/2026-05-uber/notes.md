# Pass-2 — Design Uber

**Date**: 2026-05-17
**Branch**: v2 (post #95 merge)
**Scenario**: Design Uber. Riders request rides; drivers accept and complete them; pricing surges when demand outstrips supply. One pod is the real-world simulator.
**Architect**: Augustus (driven by Claude / no human in the loop)
**Outcome**: **Loop did not close**. The platform booted cleanly, the first pod spawned and consumed the proclamation, but the agent's first turn returned with `tokens_in=0 tokens_out=0` and the swarm stopped progressing. New platform-gap tasks filed below.

---

## §1 — What worked

Recorded as one-line acceptance signals against [spec/08](../../spec/08-v2-acceptance.md):

- §0 **Empty state**: the Forum's Glance perspective renders the parchment torn-leaf insert correctly with `Speak, and the conclave begins.` and no leftover counters. ✓
- §1 **One write affordance**: the empty-state proclamation field is the only write. ✓
- §2 **Proclamation reception**: within ~1 s of submitting, `ProclamationIssued` lands in observer activity and the Bandeau numeral updates to `№ I`. ✓
- §2 **First-pod spawn (SpawnFirstPod)**: a pod-id was minted and the container brought up within ~1 s of the proclamation. ✓
- §6 **OpenLLMetry-style span around the Claude turn**: `agent_turns` has a row with `started_at` / `ended_at`. ✓ (but with zero token counts — see gap G18 below)
- §11 **Reset**: clicking Reset on the Forum, or `POST /commands {kind: ResetState}`, wipes back to zero pods / proclamations / activity in ~5 s. ✓ (verified earlier as part of #93)

What the Forum surface delivered on:
- Pod-Cartouche node renders with correct state-pip colour cycle (`not_yet_spawned` → `running` → `stopped`).
- The Roll right-rail shows the four bootstrap events in rubric verbs: `PROCLAIMED`, `SPAWNED`, `BOOTED`, `LOADED`.
- Witness Codex renders the proclamation with its drop cap on the first paragraph (and only there — the FolioDrawer drops the cap as spec/09 §3 mandates).
- StuckTray surfaces the pod as "container stopped" once HealthWatcher flips it.

---

## §2 — What did not work

### Platform-gap G18 — Claude turn returns `tokens_in=0 tokens_out=0`

**Observed**: pod-73fb7c806fcd's only Claude turn (turn `6a63c260085e`, duration ~30 s, exit code 0) recorded zero input and zero output tokens. The pod's `agent_turns` projection shows the timing but no usage. The pod then sat idle — no rename, no proposal, no work.

**Hypothesis** (in order of plausibility):
1. The bootstrap `stream-json` parser at `pods/_template/agent/bootstrap.py:284-331` is reading from an empty stream because Claude CLI silently authenticated against the wrong endpoint or printed no events.
2. The credentials at `/root/.claude/.credentials.json` are present but the binary at `/opt/claude/2.1.143` couldn't find them (mount-path mismatch).
3. `--output-format stream-json` is being ignored at this Claude version.

The agent printed no model output to stdout or stderr that the bootstrap captured — only the harness lines around the turn. **This is the headline platform gap of pass-2** because every downstream step (rename, propose, build) depends on the agent actually producing text.

### Platform-gap G19 — `SendDirectMessage` from Augustus never reaches the pod's inbox

**Observed**: I sent a `SendDirectMessage` via `POST /commands`. The flow was:
1. observer's `OperatorService.fan_out_forum_command` → `publish_command("SendDirectMessage", payload, "council")`.
2. mcp-coms picked it up, called `ComsService.dm()`, opened council `council-26effa85086b` between `__augustus__` and `pod-73fb7c806fcd`, posted the body, emitted `CouncilOpened` + `MessagePosted` to JetStream.

The pod's bootstrap (`pods/_template/agent/bootstrap.py:432-436`) only subscribes to:
- `conclave.inbox.<pod_id>` — core NATS, no one publishes to it for DMs
- `conclave.events.operator.ProclamationIssued`
- `conclave.events.operator.DirectMessageFromUser`

`MessagePosted` and `CouncilOpened` go to the council context, not to `conclave.inbox.<pod_id>` or `DirectMessageFromUser`. **The pod literally has no listener for the DM path.** Spec/02 Phase 7 says "MessagePosted(... from=__user__) delivered to pod inbox" — the platform doesn't deliver.

Fix: mcp-coms should fan out the message to `conclave.inbox.<pod_id>` (core NATS) whenever a Augustus-DM message is posted; OR operator should publish a `DirectMessageFromUser` event when `SendDirectMessage` is the command kind.

### Platform-gap G20 — `/ingest/pod-activity` 404 spam

**Observed**: observer logs show ~10 POST `/ingest/pod-activity` per second returning 404. The path doesn't exist in `observer/api/ingest.py` (only `/ingest/otel` and `/ingest/otel/v1/traces` are defined). The source isn't a current service in this repo's `services/` (grep confirms no live code emits to that path).

Hypothesis: a stale client lingering on this dev box from v1, or a Tempo health probe with the wrong path. Harmless (observer 404s and keeps running) but noisy in logs and a sign something off-tree is leaking traffic.

Fix: either drop the offending client (figure out what's polling — probably a leftover from a previous architecture) or add a 204 catch-all on `/ingest/pod-activity` with a deprecation log line.

### Platform-gap G21 — `runtime_status` flips to "stopped" while the container is still running

**Observed**: `/state/pods` reports `runtime_status=stopped` for pod-73fb7c806fcd at T+2 minutes, but `docker ps` confirms `conclave-pod-73fb7c806fcd` is `Up 5 minutes`. The pod is alive; only its OTel-span emission stopped (because the agent isn't doing anything).

HealthWatcher's staleness threshold (~2 min of no spans) is too aggressive given the realistic case of a long-thinking agent. Spec/08 §10 R1 says "node turns red within 5 s of container kill" — but this is the reverse: a healthy container is being marked stopped on a long pause.

Fix: HealthWatcher should distinguish `agent_state=thinking` from `runtime_status=stopped`. The first means "no spans, but the container heartbeat tells us it's alive"; the second means "the container itself is gone". Today only the staleness path exists.

(This is exactly the docker-events subscription requested by kanban #24, which now becomes load-bearing rather than nice-to-have.)

---

## §3 — Personality observations

Almost none — the swarm never got past the first turn. The single Claude turn produced no captured output, so there's no quotation to record. **The personality-as-quotation principle from spec/09 cannot land if the agent doesn't speak.**

---

## §4 — Recommendation

Pass-2 closed with the loop not terminating; new platform-gap tasks (#G18–G21 above) filed in kanban. Pass-3 should run only after **G18 (zero-token Claude turn) and G19 (DM-to-inbox routing)** are fixed — these are the load-bearing failures. The other two (404 spam, HealthWatcher false-stopped) are quality-of-life and can be deferred.

When pass-3 runs, the realize → analyze → nuke loop closes if no new platform-gap tasks are filed during analyze.
