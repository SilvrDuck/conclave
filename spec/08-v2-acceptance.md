# 08 — v2 Acceptance

**Status**: contract for "done" on v2. When the criteria below pass on
a clean machine for the **current validation scenario**, the
acceptance pass is complete. v2 is shipped only when the realize →
analyze → nuke loop in §14 closes with zero new platform-gap tasks.

> v2's deliverable is the *platform*, not whichever app the swarm
> builds this round. The validation scenarios (Spotify-clone, design
> Uber, …) are exercise weight — see [00-vision](00-vision.md).
> Acceptance failures are platform failures, never "the agents could
> have built a better feature."

---

## The shape of acceptance

Four layers, in order. All four must pass for v2 to ship.

1. **Golden run.** One unscripted execution of the current
   scenario's mandate that reaches the end-state below.
2. **Invariants.** Properties that hold during, before, and after the
   golden run.
3. **Quality gates.** Specific responses to the QA scenarios in
   [06-atam](06-atam.md).
4. **Loop closure.** Realize → analyze → nuke completes with zero
   platform-gap tasks filed during the analyze phase (§14).

Every criterion gets a recipe — a sequence of Playwright / OTel /
HTTP / curl actions that pass-or-fail deterministically. Recipes that
can't be made deterministic don't belong in this spec.

---

## §0 — The golden run

A fresh machine. The architect runs `bash kickstart.sh`. Augustus
opens the Forum at a single URL. The Forum is empty: no pods, no
proclamations, no decisions, no graph nodes. One affordance is
visible: a proclamation field. The rest of the UI shows empty states,
not zeros.

The current validation scenario is **design Uber**. Augustus types:

> *"Design Uber. Riders request rides; drivers accept and complete
> them; pricing surges when demand outstrips supply. One pod is the
> real-world simulator — it generates rider requests, simulates
> driver locations and movement, and adjudicates trip outcomes — so
> the rest of the swarm has a world to react to."*

He clicks Proclaim. From that moment, the criteria in §1–§11 below
hold. Within roughly **45 minutes** of wall time, Augustus can open
the deployed multi-pod app and watch a simulated ride flow
end-to-end (request → match → in-progress → completed) and watch a
surge-pricing event fire when the simulator pumps demand.

> Earlier scenarios (Spotify-clone — listen / lyrics / shared jam)
> remain on record under `runs/<YYYY-MM-scenario>/notes.md`. Each
> pass picks a new scenario that exercises senate strategies and
> observability surfaces the previous one did not. See §14.

---

## §0.5 — The simulator pod role

For scenarios that need a feed of synthetic real-world events
(rides, traffic, weather, stock ticks, sensor readings), the
proclamation reserves one pod as the **simulator** — also called
oracle, environment, or real-world feed, whichever fits the domain.
The simulator is a normal pod: admitted via the senate, named by
itself, capable of being exiled.

- [ ] **The proclamation names the simulator role.** The simulator
      role is mandated by the proclamation text, never hard-coded
      into the platform.
- [ ] **The simulator pod is admitted via the senate**, never
      pre-spawned. The platform code path that admits the simulator
      is the same as for every other pod.
- [ ] **The simulator's HTTP traffic generates real OTel call
      edges** to every consumer pod. The Glance graph shows the
      simulator as a hub.
- [ ] **The simulator's reasoning is visible in Witness.** Surge
      events, driver allocations, and adjudicated outcomes appear
      as agent turns in its pod drawer and (when they affect peers)
      in council threads.
- [ ] **The simulator is not necessarily the first pod.** The first
      pod (§3) is whichever role the founding agent picks from the
      proclamation; the simulator may be that pod or may be
      proposed later. Either way, §3's bootstrap rules apply
      identically — no special-case path.

---

## §1 — Pre-proclamation surface (Glance perspective in its empty form)

- [ ] **Empty state is genuinely empty.** No "0 pods · 0 decisions"
      counters. No leftover sprites. No first-run wizard.
- [ ] **One write affordance is visible.** Proclamation field.
- [ ] **Refresh is idempotent.** Same screen, no flicker.
- [ ] **The Forum's four perspectives are accessible but
      content-empty.** Glance / Witness / Try / Direct — each shows a
      one-liner empty state. No tab named after a backend module.

---

## §2 — Proclamation reception

- [ ] **Within 3 seconds of submitting**, the proclamation card
      appears at the top of the Witness perspective with its numeral
      (I, II, …) and full text.
- [ ] **A placeholder decision tablet appears in Witness**, titled
      "Architecture for: <first 60 chars of proclamation>", body
      "_council pending_", status `placeholder`. *Created by the
      platform, not by the agent.*
- [ ] **A pod node appears on the Glance graph** within 5 s, sized as
      a placeholder (no service yet), labeled with its initial
      neutral handle (not "founder").
- [ ] **The activity ticker opens** with the proclamation as its first
      row, followed by `pod_spawned`, `agent_session_started`,
      `agent_turn_started` events as they happen.

---

## §3 — First-pod bootstrap

- [ ] **The first pod renames itself** when its role becomes clear —
      whatever the agent decides from the proclamation (e.g. for
      Uber, `rider-app` / `dispatch` / `simulator`; for Spotify,
      `web` / `music-ui`). The display-role on the graph updates in
      real time. The pod's stable id never changes.
- [ ] **The first pod proposes admission** via the senate. The
      proposal shows on the Witness senate band with: kind, one-line
      summary, strategy, deadline countdown, ballot strip with one pip
      per eligible voter.
- [ ] **N=1 admission auto-passes** because the proposer is the only
      eligible voter. *No special-case bootstrap code path.*
- [ ] **The admission seals a decision** with a non-empty body. The
      Glance graph hardens the pod node from placeholder to admitted
      (visual distinction).

---

## §4 — Senate as test bed

This is the single criterion that most justifies v2's existence.

- [ ] **At least three of the four strategies fire during the golden
      run**: `majority`, `supermajority`, `consensus_omnium`, and
      `sortition`. Each appears on the senate band with its
      distinguishing UI (strategy badge, ballot strip behaviour,
      sortition draws shown).
- [ ] **Each strategy demonstrates non-trivial dynamics**:
      - `consensus_omnium` must run with ≥3 affected pods.
      - `sortition` must draw a subset and show the draw.
      - `supermajority` must close on its quorum rule (e.g. exile
        attempt rejected because it fell short of 2/3).
- [ ] **No proposal sits open past its deadline.** The deadline reactor
      closes any open proposal within 30 s of its deadline.
- [ ] **Every proposal has a non-empty summary in its payload** that
      renders in the senate band cartouche. v1 left these blank.

---

## §5 — Many pods (the test conditions for §4)

- [ ] **Between 5 and 10 pods admitted** by the end of the golden run.
      For the Uber scenario, the natural split is roughly:
      `rider-app`, `driver-app`, `dispatch`, `pricing`, `simulator`,
      plus likely an adopted `postgres` for trip storage and an
      adopted `redis` for live driver locations. The exact split is
      the agents' decision.
- [ ] **At least one adopted pod** runs in the golden run (an OSS
      image managed by an agent sidecar with privileged access). The
      most natural candidate is `postgres:16`.
- [ ] **At least one image-swap** demonstrated in the golden run:
      a pod proposes `kind=image_swap`, the senate passes it, and
      the platform brings the new container up with the agent's
      identity preserved. **Required** — image-swap is the
      load-bearing demonstration of pods self-modifying their
      substrate; if no organic scenario surfaces during the run,
      the run team contrives one (e.g. force `postgres:16 → postgres:17`).

---

## §6 — Councils & meetings

- [ ] **At least one council is convened** during the golden run.
      Most naturally during the early architectural debate
      (e.g. "who owns the trip ledger?" / "who owns lyrics?",
      whichever the scenario surfaces).
- [ ] **The council appears as a thread in Witness** with named
      participants, time-ordered messages, sender identity. Messages
      appear within 1 s of being posted.
- [ ] **When the council closes**, the placeholder decision (or a new
      one) is sealed with the council's summary as its body.
- [ ] **The call-edges graph reflects the council's
      participants** — the pods involved show edges to each other
      while the council is open.
- [ ] **Augustus can open a DM with any pod** from the Forum (J7) and
      the pod's agent receives the message in its inbox. The reply
      lands in the DM thread within one agent turn.

---

## §7 — Build & deployment

- [ ] **Real HTTP call edges appear on the Glance graph** from
      OpenTelemetry spans (not synthesised). Edges animate when
      traffic flows.
- [ ] **Each pod registers a hostname** with Traefik
      (`<pod>.conclave.local`). No port-counter logic in the platform.
- [ ] **An adopted `postgres` pod** (if admitted) has its credentials
      configured by its agent and accepts connections from peer pods.
- [ ] **At least one real cross-pod call** is recorded in Tempo and
      visible in the graph.

---

## §8 — Try what they built

- [ ] **Augustus can open the deployed app** from the Try
      perspective in one click. The Try view lists every pod with a
      public HTTP service, hostname, and one-click open.
- [ ] **A ride can be hailed.** The rider-app accepts a destination,
      the dispatch pod allocates a driver from the simulator's
      pool, and the trip transitions through accept → in-progress
      → completed within ~60 s of simulated time.
- [ ] **Surge pricing visibly fires.** The simulator pumps demand;
      the pricing pod raises rates; the rider-app reflects the
      multiplier on the next quote.
- [ ] **The Uber clone need not be pretty.** Quality of the
      *platform's observability* is the bar, not the rider UI.

---

## §9 — Watchability invariants (cross-cutting)

- [ ] **Every agent turn is visible** as a token stream in the pod
      drawer (J4). The transcript updates live during the turn.
- [ ] **Every council is readable** as a thread (J5). Closed
      councils show the summary.
- [ ] **Every proposal shows kind + summary + strategy + ballot strip
      + deadline.**
- [ ] **The activity ticker carries every named event** (admissions,
      decisions, deployments, image-swaps, exiles, completion).
- [ ] **The graph re-flows on each new pod / call edge** without a
      page reload.
- [ ] **Click any node → drawer of neighbours.** Agent → services,
      meetings, decisions, charter, token stream. Decision → proposal,
      participants, affected services. Proclamation → spawned pods,
      decisions, deployed apps. The drawer's links are themselves
      clickable.

---

## §10 — Robustness

- [ ] **Kickstart in under 90 s** post-cache (`bash kickstart.sh`).
- [ ] **Stack restart (`docker compose down && up`) preserves**
      proclamations, admitted pods, charters, decisions, council
      transcripts. Agent sessions resume via Claude Code `--resume`.
- [ ] **No silent failures.** When a pod's container is killed:
      within 5 s the Glance graph turns its node red; the activity
      ticker logs the event; restarting the container brings the pod
      back to running.
- [ ] **No leaked containers.** `kickstart.sh` re-run wipes all
      conclave-* containers cleanly.
- [ ] **Postgres single-instance, never locks.** No `database is
      locked` errors anywhere in the run.

---

## §11 — Augustus's surface

Plane-B operator surface stays focused.

- [ ] **Four writes from the Forum**, never more:
      proclamation, DM to a pod, charter edit, imperial vote.
- [ ] **Charter editor pre-loads the current charter** (J7). No more
      "blank textarea decrees a new charter."
- [ ] **Augustus never sees container names, NATS subjects, port
      numbers, or schema names** in normal use. These surface in
      hover-detail panels only.
- [ ] **The Forum has no first-run wizard** on a running deployment.

---

## §12 — Quality gates (per [06-atam](06-atam.md))

Each ATAM scenario maps to one or more acceptance criteria above.
Spot-checked here:

- [ ] W1 (live call edges on the graph) → §7, §9.
- [ ] W2 (token stream for one pod) → §9.
- [ ] W3 (council thread) → §6.
- [ ] W4 (proposal cartouche complete) → §3, §4.
- [ ] O1–O4 (OSS substitutions) → no custom code where OTel /
      JetStream / Traefik / Claude Code can serve. Audit at PR time.
- [ ] R1–R3 (robustness) → §10.
- [ ] MA1 (many pods boot fast) → §5.

---

## §13 — Anti-acceptance

Things v2 acceptance explicitly does *not* require, to avoid scope
creep:

- A polished scenario front-end. Whatever the swarm ships — Uber
  clone, Spotify clone, anything else — can be a list and a button.
  Aesthetics are not a platform-acceptance gate.
- Real domain integrations (maps, music licensing, payment rails,
  sensor feeds, …). The simulator pod stands in for any external
  world the scenario needs.
- Multi-tenant conclave.
- Auth / authz inside the platform.
- The CLI wizard (deferred per [00-vision](00-vision.md)).
- The frontend wizard view (removed per
  [03-prototype-audit](03-prototype-audit.md)).
- Performance budgets tighter than "visible within 2 s."
- Personas (Cicero / Cato).
- Skills / shared-skills directories.
- Revival of exiled pods (Phase 2 only).

---

## §14 — Realize → Analyze → Nuke

v2 is not done after one passing golden run. v2 is done when the
loop below closes with **zero new platform-gap tasks**.

**Platform-gap** (the term that decides loop termination): a task is
a platform-gap if it asks the *platform* — not the scenario, not the
swarm's app — to change. Concretely, a task is a platform-gap iff
addressing it requires editing one or more of:

- `libs/conclave-core/` (events, models, bus, schemas)
- `services/observer/` (commands, projections, state endpoints,
  reactors, SSE feed, the OTel ACL)
- `services/mcp-*/` (any MCP server's tools or reactors)
- `pods/_template/` or `pods/_adopted_template/` (the agent
  bootstrap, charter scaffolding, OTel wiring)
- `services/forum/` (any Forum perspective, component, or theme
  surface listed in §1–§11)
- `infra/` (compose, Traefik dynamic, Tempo, OTel collector,
  Postgres init)
- `kickstart.sh` / `teardown.sh` / acceptance recipes

By contrast, **scenario-gaps** are filed against the swarm's
workspace (the pod code the agents wrote — `pods/<id>/workspace/`,
charters, decisions) and do **not** count toward the loop's
termination. **Polish-gaps** that are pure copy / colour / spacing
inside the Forum are platform-gaps only if they violate a §1–§11
checkbox; otherwise they're filed to the backlog and do not block
loop closure.

Each pass of the loop:

1. **Realize.** Start with a genuinely clean state. `bash
   kickstart.sh`, issue the current scenario's proclamation, let
   the swarm run to acceptance. The architect observes; only
   Augustus intervenes (J6/J7: DMs, charter edits, imperial
   votes).

2. **Analyze.** Capture observations as markdown notes in
   `runs/<YYYY-MM-scenario>/notes.md`:
   - Which §1–§13 criteria passed cleanly, which limped, which
     failed.
   - Which agent turns surfaced personality (debates, dissent,
     style). Quote them verbatim — personality is core to the
     product (see [00-vision](00-vision.md)).
   - Which UI surfaces were unreadable, ambiguous, or
     non-clickable. Be specific.
   - Which platform behaviours were stubbed, placeholder, dummy,
     or "TODO later." File each as a kanban task before the next
     pass starts.

3. **Nuke.** `bash teardown.sh`, remove the `postgres_data`,
   `nats_data`, `tempo_data` volumes, and prune any leftover
   `conclave-*` containers. The next pass starts on a fresh
   machine state. The `runs/<YYYY-MM-scenario>/` notes are kept
   in git.

The loop terminates when an analyze phase files zero new tasks. At
that point v2 is done.

Each new scenario must exercise senate strategies and observability
surfaces the previous one did not. The pass-picker tracks which
boxes a scenario lights up, by column:

| Pass | Scenario | New strategy fires | New surfaces stressed | Notes path |
|------|----------|--------------------|------------------------|------------|
| 1 | Spotify-clone (listen / lyrics / jam) | majority, supermajority, consensus_omnium, sortition | Glance call edges, Witness council thread, Try app | scrapped before §14 codified — no notes captured |
| 2 | Design Uber (rides / surge / simulator) | re-runs all four under load | Simulator pod (§0.5), call edges with a hub topology, surge as an emitted event | `runs/2026-05-uber/` |

---

## What "done" sounds like

When the architect can:

1. Clone the current version branch on a fresh machine.
2. Run `bash kickstart.sh`.
3. Open the Forum.
4. Type the current scenario's proclamation.
5. Watch for ~45 minutes without intervening:
   - 5–10 pods admitted via real senate votes that exercise
     multiple strategies, one of which is the simulator,
   - councils visibly debate the architecture,
   - call edges light up between pods (the simulator is a hub),
   - at least one OSS image runs as an adopted pod,
   - the deployed app opens on `localhost` and the scenario's
     core flow works end-to-end.
6. Click any node in the Glance graph and traverse its neighbours
   to any other node via the drawer.
7. Re-run the loop on the next scenario without filing new
   platform-gap tasks.

…then v2 is done.

If any of the following are true at that point, v2 is not done:
- "I couldn't see what `<pod>` was thinking."
- "Why is this still custom code?"
- "Where's the meeting transcript?"
- "Why is there a port number anywhere on screen?"
- "The simulator didn't show its reasoning."
- "I filed a task during analyze." → run the loop again.
