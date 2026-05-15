# Conclave v1 — acceptance criteria

**Status**: contract for "done". When every box below ticks, we can call the
alpha a real first version. Until then we're prototype-shipping.

The shape of the acceptance is one **golden demo** + a set of **invariants**
that must hold during and around it.

---

## Operating principle: ship small, expand on demand

Conclave is **opinionatedly agile**. The platform's prompts, defaults, and
review surfaces are tuned to push agents toward the smallest thing that
delivers value, then expand only when a concrete need shows up. No
big-bang architecture, no speculative pods, no waterfall — *especially not
in the founder's first 30 minutes*.

What that means for the founder agent (encoded in `iusiurandum.md` and the
charter template):

- **Ship a working v0 first.** When a proclamation arrives, the founder
  proposes the *fewest* peers it can imagine that, end-to-end, deliver
  *something* the emperor could see. For a "Netflix clone", v0 is a
  single `web` pod serving one hardcoded video with a fake login — not
  three pods with proper auth, catalog, and streaming services. Two
  peers max for the first iteration; one is fine if it works.
- **New pods only when an existing pod hits a real wall.** Reasons to
  propose a peer: an agent's workspace is getting too tangled to reason
  about; a service needs to scale or restart independently; a contract
  boundary is becoming load-bearing. *Not* reasons: "auth deserves its
  own service in theory", "we should separate concerns up front".
- **Iterate in tight loops.** Council → ADR → ship → observe → council.
  An ADR that opens at 22:00 and closes at 22:08 with a 3-line summary
  is doing better work than one that opens at 22:00 and is still being
  drafted at 22:45.
- **Reject pre-decided architectures.** If the founder's first
  proposal looks like "let's spin up 6 pods modelled on Netflix's
  micro-services", the platform should make that uncomfortable: the
  charter template asks "what specific failure today justifies this
  pod?" and the council strategy defaults to `consensus_omnium` for any
  initial-architecture proposal with >2 peers, forcing dissenters to
  speak up.
- **`senate.propose_completion` is a first-class verb.** The founder is
  expected to call it the moment the v0 mandate is met, not after every
  conceivable improvement is shipped. Subsequent proclamations grow the
  system.

What that means for the prompts and platform:

- The founder's iusiurandum opens with "Ship the smallest working slice
  that fulfils the proclamation, then stop and observe." before any
  language about peers and councils.
- The charter template's `## Why this pod and not a chunk of an existing
  pod?` field is required, not optional. Empty answer → senate
  auto-rejects.
- `state.platform_info` returns a `project_age_seconds` field; if the
  founder proposes more than 2 peers within the first 60s of project
  age, the senate logs a `velocity_warning` ADR (informational, doesn't
  block) and the Forum surfaces it.
- The acceptance demo (§0) checks that the founder ships **a running v0
  with one or two pods**, then proposes additions in later iterations —
  not that it nails the final 3-5-pod architecture on the first try.

This isn't a soft suggestion in the docs. It's an *opinion the platform
holds*, and the design of every prompt, default strategy, ADR template,
and senate band UI is meant to reinforce it.

---

## Verification protocol: how I (Claude) actually check each criterion

Every criterion in this spec is checked by **driving the running stack with
the Playwright MCP and the Chrome DevTools MCP**, not by reading source or
guessing. The pattern, per criterion:

1. `mcp__playwright__browser_navigate` to the relevant URL (Forum or any
   pod's service URL).
2. `mcp__playwright__browser_take_screenshot` + `mcp__playwright__browser_snapshot`
   (accessibility tree) for the visual state.
3. `mcp__playwright__browser_console_messages` (level=error) to ensure no
   unhandled errors fire.
4. `mcp__playwright__browser_network_requests` to check the right API
   calls happen with the right shapes.
5. `mcp__chrome_devtools__list_console_messages` +
   `mcp__chrome_devtools__list_network_requests` when I need fuller
   devtools context — e.g. "did the SSE stream emit?", "did the React
   render avoid a re-mount?", "did the Vite proxy hit observer:8000?".
6. For reactivity criteria: stamp the screenshot time, take a second
   screenshot N seconds later, diff the two, and confirm the change
   happened within the budget.
7. For "no leftover state": Playwright opens an incognito context so I
   don't measure my own cached cruft.

**Every checkbox in §1–§11 must be backed by a Playwright/DevTools
recipe.** If a criterion can't be expressed as a sequence of MCP calls
that pass/fail deterministically, it doesn't belong in the spec — rewrite
it until it does.

### Per-criterion verification recipe template

```
- [ ] CRITERION
   - precondition:  state of the system before checking (e.g. "stack up, no proclamation sent")
   - action:        the user action being simulated (navigate, click, type)
   - check:         the assertion against the result (screenshot match, snapshot text, network shape)
   - tools:         the MCP calls that perform the action and the check
```

I'll fill these in for the criteria below as I implement each. The
template stays as the contract.

### Eyes verification ground rules

- I never claim a criterion passes from `curl` output alone. The user
  doesn't see `curl`; they see the browser. Every visual criterion must
  be confirmed by a screenshot or accessibility snapshot I personally
  inspected.
- For each fix I ship, I include a **before** screenshot (current broken
  state) and an **after** screenshot (post-fix). Both go in the PR body
  so the user can see what changed without rebooting the stack.
- Reactivity is measured: I record an event timestamp from
  `docker logs` and the timestamp of the screenshot that shows the
  resulting UI change, and I include the delta. If it's >2s, the
  criterion fails even if the UI eventually catches up.
- Console errors are blockers. Any `error`-level console message during
  the golden demo fails the run regardless of how nice the screenshots
  look.

### Graphify MCP support

The Graphify MCP server is also wired (see `.mcp.json`). When I need to
navigate the codebase to find which file owns a given behavior I'll lean
on it via `query_graph` / `get_node` / `shortest_path` rather than grep —
faster and the audit trail (EXTRACTED/INFERRED/AMBIGUOUS) keeps me honest.

---

## 0. The golden demo

A new user opens `http://localhost:5173` from a blank machine state. They
see:

- An empty stage labeled clearly as the Forum, with marble texture and the
  Roman aesthetic. No pods, no ADRs, no proposals. A single piece of UI
  is dominant: a proclamation input that reads "*The Forum awaits your
  word.*" with a single big text field and a "Proclaim" button.
- No noise. No "0 members · 0 open · 0 ADRs" counters. No activity feed
  prelude. Just stillness — the Forum before it begins.

They type **"Let's build a Netflix clone"** and click Proclaim.

**Within 3 seconds**, every one of these must be visible without page
refresh:

1. A marble tablet appears top-centre with the proclamation text. A roman
   numeral "I" is engraved on it (this is the project's first
   proclamation).
2. A clay (dashed-outline) ADR tablet appears in the Tabularium ribbon at
   the side, titled `adr-0001 — Architecture for: Let's build a Netflix
   clone`, body `_pending senate council_`.
3. A sprite labeled `founder` materialises on the stage with a pulsing
   golden halo ("thinking…").
4. A side log starts emitting events: "Augustus proclaims.", "founder
   spawned.", "founder reading proclamation.", etc. Updates flow without
   user action.

**Within 60 seconds**, the user sees the founder propose 3–5 peer pods
(e.g., `auth`, `catalog`, `streaming`, `web`). For each proposed peer:

5. A clay sprite (proposed, not yet admitted) appears on the stage.
6. A senate-band entry appears at the top labelled "founder proposes
   admit:auth" with a ballot strip.
7. When the founder casts its self-yes ballot and the strategy passes, the
   clay sprite hardens to stone (admitted) and a peer container spins up.
   The user sees the spawn count tick on the bus.

**Within 5 minutes**, the user sees:

8. A council line drawn between peers, animated, labeled "first
   architecture". Hovering shows the most recent 3 messages.
9. As the council closes, the placeholder ADR (`adr-0001`) hardens from
   clay to stone. The body is now the council's summary.
10. Each peer's agenda lights up with concrete `doing` items.
11. New ADRs accumulate in the Tabularium as peers ship contract changes.

**Within 30 minutes**, the user can:

12. Open a second browser tab to `http://localhost:8800` (or whatever port
    the web pod ships) and see **a running Netflix-clone frontend**:
    a small catalogue of 3–4 demo videos with thumbnails, a login flow,
    and the ability to click a movie and **watch a demo video play** in the
    browser. Videos can be canned (Big Buck Bunny, any CC-licensed clip);
    the point is *the platform's agents wired the system end-to-end*.

---

## 1. Pre-proclamation surface

The user-facing UI must satisfy all of these before a single proclamation
is sent:

- [ ] **Empty state is genuinely empty.** No "0 of 0" counters, no
      "watching…" placeholder, no "click here" button hints, no stale
      sprites from previous runs. State persistence is wiped per kickstart
      so the user never sees leftovers.
- [ ] **One affordance only.** The Forum view's pre-proclamation surface
      shows the marble stage, the title, and the proclamation input.
      Everything else (Tabularium, Council list, ADRs, Members count) is
      hidden or rendered as empty/awaiting.
- [ ] **Proclamation input is the visual centre of mass.** It is wide,
      monumental-looking, with a heavy serif placeholder ("Let's build a
      Netflix clone"). It is not a small form at the top of a noisy page.
- [ ] **Wizard/Tabularium/Council nav links are still present** in the
      side rail but understated until they have content.
- [ ] **Refreshing the page in this state shows the same empty Forum.**
      No flicker, no race, no need for the user to think about it.

## 2. Proclamation reception

The instant the user clicks Proclaim, before any agent has done anything:

- [ ] **Optimistic UI**: the marble tablet appears immediately with the
      proclamation text. No spinner. No "Sending…". If the publish fails
      it un-renders with an error explaining why, but the default is the
      tablet appears.
- [ ] **The placeholder ADR appears immediately** in the Tabularium — the
      *platform* writes it (not the founder agent). It is rendered as a
      clay tablet with a dashed border, body "_pending senate council_".
- [ ] **The founder pod sprite appears immediately** on the stage, with a
      "spawning" indicator (gold pulse).
- [ ] **The activity log is visible from the moment of the proclamation
      onwards**, not before. It opens with a "Proclamation I — Let's
      build a Netflix clone" entry.

## 3. Bootstrap visibility (founder)

Once the founder container is up:

- [ ] The founder sprite's "spawning" indicator transitions to "thinking"
      (rotating pulse) when Pi opens its first turn.
- [ ] The activity log shows live entries:
      - `founder.spawned`
      - `founder.thinking` (turn_start)
      - `founder ▸ read /conclave/iusiurandum.md`
      - `founder ▸ state_members`
      - `founder ▸ state_platform_info`
      - `founder ▸ senate_propose_member(auth, …)`
      - etc.
      Updates within 1–2s of the underlying event. Filter by pod, kind.
- [ ] When the founder calls `senate_propose_member`, the senate band
      sprouts a new proposal cartouche showing the proposed pod name,
      strategy, ballot status, and rationale on hover.
- [ ] The proposed pod sprite appears in clay form on the stage (not yet
      admitted) the moment the proposal lands.

## 4. Senate flow

For every proposal made by an agent:

- [ ] Open proposals show with **ballot-strip** UI: yes/no/abstain counts,
      eligible voters, deadline countdown, hover-for-rationale.
- [ ] On approval: the cartouche flips to "approved", the affected pod
      sprite hardens (clay → stone for member proposals; tablet hardens
      for ADR-bound proposals).
- [ ] On rejection: cartouche flips to "rejected" with a strikethrough
      style and the rejection-ADR appears in the Tabularium.
- [ ] Sortition strategies show the drawn panel as small icons next to
      eligible voters.
- [ ] Founder N=1 trivial pass renders correctly (single ballot, instant
      close).

## 5. Peer pod spawn (the heart of the demo)

When the senate admits a member proposal:

- [ ] The spawner reacts in <2s of `vote_closed` and launches a new
      container.
- [ ] The activity log emits `spawner.launched(pod=<name>, image=…,
      cid=…)`.
- [ ] The new pod's sprite hardens from clay → stone the moment the
      container is `running`.
- [ ] The new pod's harness boots and shows up in the activity log:
      `<pod>.harness.ready`, `<pod>.pi.started`.
- [ ] Clicking the pod sprite opens a side panel showing: container ID,
      service URL inside the docker network, current charter excerpt,
      current agenda, current endpoints.

## 6. Cross-pod deliberation

The first council the founder convenes to design the architecture:

- [ ] An animated line is drawn between the founder and each participating
      peer on the stage.
- [ ] Hovering the line shows the last 3–5 messages in the council, with
      sender and timestamp.
- [ ] The activity log streams council messages as `coms.message(<from>,
      <to>, <body[:60]>)` entries.
- [ ] When the council closes:
      - The line fades.
      - The placeholder `adr-0001` tablet hardens (clay → stone).
      - The ADR body is the council summary, not "_pending_".
      - The Tabularium shows it as a fully sealed tablet with S·P·Q·R
        watermark.

## 7. Contract changes (the second senate cycle)

When a peer's contract changes (alice ships an endpoint that another
peer calls):

- [ ] The observer's call-graph picks it up, the new endpoint annotation
      flow runs (annotation_requested → annotation back), and the call
      edge appears on the stage as an arrow.
- [ ] If a peer raises a contract-change proposal under
      `consensus_omnium`, the senate band shows the proposal needing every
      affected caller's yes. The ballot strip fills in real time as each
      peer votes.
- [ ] On approval: a new ADR is sealed. The endpoint annotation reflects
      the change.

## 8. Shipping the Netflix clone

This is the demoable end state — the platform's agents must produce a
runnable system, not just talk about one. **Per the operating principle,
v1 done is a working v0 first**, not a polished 5-pod architecture:

- [ ] **v0** ships within 8 minutes of proclamation: ONE pod (the
      founder, or one peer) serving an HTML page on a host-mapped port
      with a single hardcoded video playable in-browser and a fake
      login. The user can see *something working* before the senate
      gets fancy. Verified by `mcp__playwright__browser_navigate` to
      the published port and a screenshot showing the video element.
- [ ] **v1 expansion** happens *after* v0 is live and only when the
      senate has at least one ADR justifying each new pod with a
      concrete failure of the v0 design (e.g. "auth pod separated
      because v0's login is a hardcoded credential check we can't
      iterate on without redeploying the web pod"). At least 3 pods
      host real running services at this stage, but each one points to
      an ADR explaining *why it had to be its own pod*.
- [ ] Each pod's container exposes its service on the conclave network.
- [ ] The `web` pod serves an HTML page on a host-mapped port the user
      can open in a browser.
- [ ] The page lists at least 3 hardcoded "videos" with thumbnails. At
      least one of them, when clicked, **plays an embedded video** in the
      browser (Creative-Commons-licensed clip baked into the project
      template — Big Buck Bunny or similar).
- [ ] The login flow (register → token → use the catalogue) works.
- [ ] Stopping any one pod and bringing it back up does not break the
      others (per spec §12: agreements durable, gossip ephemeral).

## 9. Observability invariants

These must hold throughout the demo:

- [ ] **Reactivity budget**: every state change is visible in the UI
      within 2 seconds of the underlying event. No 30-second polling
      delays.
- [ ] **No silent failures**: if a pod's harness crashes, the activity
      log shows it; the pod sprite shows a "down" indicator (red dot,
      faded); the user is not left wondering.
- [ ] **No mysterious carryover**: nothing renders on the UI that didn't
      come from the current run. Wiping state + reload = clean stage.
- [ ] **Hover always works**: every interactive element has a useful
      tooltip — pods show charter excerpt + endpoints, lines show recent
      messages, proposals show rationale, ADRs show summary.
- [ ] **The activity log is the system's heartbeat.** It must update
      visibly on every meaningful event. If the user can't tell from the
      log whether the system is doing anything, the log is broken.

## 10. Robustness

- [ ] **One-command kickstart**: `bash kickstart.sh` brings the platform
      up from a wiped state in under 90 seconds (post-build).
- [ ] **One-command teardown**: `docker compose down -v` kills everything
      and frees the volumes.
- [ ] **Restart safety**: stopping and re-starting the platform stack
      preserves all admitted members, all ADRs, and the workspace tree.
      The observer cold-start path rebuilds projections.
- [ ] **No leaked containers**: spawner-launched pods are cleaned up on
      teardown.

## 11. What the user does — and does NOT — do

The user's surface area is exactly two writes:

- [ ] **Proclamation** (text input). All high-level direction goes here.
- [ ] **Charter edit** (Charter Editor view) and **exile** (Exile
      District) — rare, blunt, both styled as Imperial decrees with a
      confirmation step.

What the user does **not** do:

- [ ] The user does **not** propose pods, write charters from scratch, or
      cast ballots. Those are senate actions. The UI doesn't even surface
      those buttons to the emperor.
- [ ] The user does **not** edit `conclave.config.yaml` after the wizard.
- [ ] The user does **not** know about NATS topics, container names, or
      ADR IDs by hand. Those exist; they're surfaced in hover panels but
      not in the day-to-day flow.

## 12. The acceptance test (concrete, reproducible)

Each of the following test scenarios must be runnable and pass on a
clean machine:

- [ ] **T1 — Blank-state proclamation produces a running system**
  1. `bash kickstart.sh`
  2. Open `http://localhost:5173`.
  3. Confirm pre-proclamation surface (criteria §1).
  4. Type "Let's build a Netflix clone" → Proclaim.
  5. Wait 30 minutes max.
  6. Verify all of §0 (1–12), §2, §3, §4, §5, §6, §8.

- [ ] **T2 — Reset is real**
  1. Run T1 fully.
  2. `docker compose -f infra/compose.yaml down -v`; remove
     `/tmp/conclave-demo`.
  3. `bash kickstart.sh`.
  4. Open the UI: confirm pre-proclamation surface (§1) — *nothing*
     carries over.

- [ ] **T3 — Reactivity**
  1. During T1's run, open dev tools network tab.
  2. Confirm no manual page reload is ever needed for the user to see
     the next state transition.
  3. Confirm activity-log delta latency p95 < 2s after the underlying
     event (measured against `docker logs conclave-<pod>` timestamps).

- [ ] **T4 — Pod restart**
  1. During T1's steady state, `docker stop conclave-auth`.
  2. UI must show the `auth` pod as down within 5s.
  3. `docker start conclave-auth`. UI must show the pod back to
     admitted/thinking within 5s.

- [ ] **T5 — Stack restart preserves the project**
  1. `docker compose down` (no `-v`).
  2. `docker compose up -d`.
  3. UI reflects all members, ADRs, agendas from before the stop.

---

## What's broken / missing today (honest gap analysis)

Today's stack does parts of this, but every single criterion above is
worth checking. The big known gaps:

| Area | What's missing |
| --- | --- |
| Pre-proclamation surface | Forum still shows pod counter / activity panel before any proclamation. Needs an "awaiting" mode. |
| Placeholder ADR | Not implemented at all. Spawner doesn't seed a clay tablet on first proclamation. Senate's `Adr` model has no `status: placeholder \| sealed` field. |
| Proclamation framing | Mandate input still has a target-pod selector; reads as a debug tool, not an imperial proclamation. Visual prominence is wrong. |
| Live messages | No SSE / WebSocket. Activity panel diffs every 2s. Council line message tooltips have no data source yet. |
| Pi turn telemetry | Harness logs turn_start / turn_end but doesn't POST to observer. UI has no "thinking" indicator other than `agenda.doing != []`. |
| Spawner reliability | When senate-ledger published events before bus was wired, spawner missed them silently. No catch-up path; no replay. |
| Senate band UI | Doesn't exist yet. |
| Council line drawing | Doesn't exist yet. |
| Demo video baked-in | No CC video clip in the pod base image; no helper for the agents to wire a video player. |
| Reactivity p95 budget | Currently 5s (poll interval). Needs SSE for <2s. |
| Charter Editor / Exile | Still stubs; commits to disk but no PR-back path; no confirmation step. |
| Restart safety | InMemoryDocs loses ADRs on senate-ledger restart; SqliteDocs exists but spawner config still defaults to in-memory in tests. |
| Pod-down detection | Observer doesn't poll docker/healthchecks; UI can't tell when a pod sprite should go red. |
| Empty-state copy | Lots of debug strings ("Members: 0", "ADRs: 0") visible to the user. |

The minimum work to get from here to v1-passing is roughly:

1. **Backend reactivity** — SSE endpoints on observer for: members,
   proposals, ADRs, agenda, activity-log stream. (1–2 days)
2. **Placeholder ADR** — Adr `status` column + spawner seeds adr-0001
   on first proclamation. (0.5 day)
3. **Pi turn telemetry** — harness POSTs `/ingest/pod-activity` on
   turn_start/turn_end; observer projects; UI subscribes via SSE. (0.5
   day)
4. **Pod-down detection** — observer polls docker inspect or harness
   heartbeats. (0.5 day)
5. **Spawner replay** — on startup, walk `/proposals` for any
   approved-but-not-spawned-yet pods. (0.5 day)
6. **Forum rebuild** per `spec/forum-viz.md` — SVG, mandate input as
   centre-piece, Tabularium ribbon, senate band, activity panel, hover
   tooltips. (2–3 days)
7. **Empty-state pass** — strip all debug strings; "the Forum awaits
   your word" copy. (0.5 day)
8. **Demo-video pre-baked** — drop a CC clip + thumbnail set into the
   pod image; small skill that the `web` agent can call. (0.5 day)
9. **Acceptance tests** — write T1–T5 as actual reproducible scripts;
   wire to CI or at least a `make demo` target. (1 day)

That's ~7–10 focused dev-days from a single hand, or two parallel work
streams (backend + frontend) for ~4–5 days. Not free, not impossible.

---

## What it means to be done

When a fresh laptop can:

1. `git clone … && cd conclave && bash kickstart.sh`
2. Open `http://localhost:5173`
3. Type "Let's build a Netflix clone"
4. Walk away, come back in 30 minutes
5. See peer pods running, ADRs sealed, council transcripts in the UI,
   and `http://localhost:8800` serving a working catalogue with a
   playable demo video

…then this is v1.

Until then, we have a serious prototype with the right architecture and
real agent autonomy, but the user experience isn't there yet.
