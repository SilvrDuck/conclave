# 08 — v2 Acceptance

**Status**: contract for "done" on v2. When the criteria below pass on
a clean machine, v2 is shipped.

> v2's deliverable is the *platform*, not the music app. The
> Spotify-clone is exercise weight — see [00-vision](00-vision.md).
> Acceptance failures are platform failures, never "the agents could
> have built a better feature."

---

## The shape of acceptance

Three layers, in order. All three must pass.

1. **Golden run.** One unscripted execution of the Spotify-clone
   mandate that reaches the end-state below.
2. **Invariants.** Properties that hold during, before, and after the
   golden run.
3. **Quality gates.** Specific responses to the QA scenarios in
   [06-atam](06-atam.md).

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

Augustus types:

> *"Users can listen to music, see lyrics scroll alongside the track,
> and start a shared listening jam with a friend."*

He clicks Proclaim. From that moment, the criteria in §1–§11 below
hold. Within roughly **30 minutes** of wall time, Augustus can open
a deployed multi-pod app and try the three features named in the
proclamation.

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
      `frontend`, `web`, `music-ui`, or whatever the agent decides
      from the proclamation. The display-role on the graph updates in
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
      The Spotify mandate naturally pulls toward: `web` / `frontend`,
      `auth`, `catalog`, `lyrics`, `jam` (or `social`), `transcode` (or
      `streaming`), plus likely an adopted `postgres` and an adopted
      `meilisearch`. The exact split is the agents' decision.
- [ ] **At least one adopted pod** runs in the golden run (an OSS
      image managed by an agent sidecar with privileged access). The
      most natural candidate is `postgres:16`.
- [ ] **At least one image-swap** demonstrated (a pod proposes and
      passes `kind=image_swap`, the platform brings the new pod up
      with the agent's identity preserved). Optional if a real
      reason doesn't surface; recorded as "demonstrated"
      vs "skipped — no reason emerged."

---

## §6 — Councils & meetings

- [ ] **At least one council is convened** during the golden run.
      Most naturally during the early architectural debate
      ("who owns lyrics?").
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
- [ ] **The music UI loads** (whatever the agents shipped). Listening
      to one of the demo tracks works in the browser. Lyrics scroll
      while a track plays. A shared-listening / jam feature is
      reachable.
- [ ] **The Spotify clone need not be pretty.** Quality of the
      *platform's observability* is the bar, not the music UI.

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

- A polished Spotify-clone front-end.
- Real music licensing — clips are demo / canned.
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

## What "done" sounds like

When the architect can:

1. Clone the v2 branch on a fresh machine.
2. Run `bash kickstart.sh`.
3. Open the Forum.
4. Type the Spotify-clone proclamation.
5. Watch for ~30 minutes without intervening:
   - 5–10 pods admitted via real senate votes that exercise multiple
     strategies,
   - councils visibly debate the architecture,
   - call edges light up between pods,
   - `postgres:16` runs as an adopted pod,
   - the deployed app opens on `localhost` and the three named
     features work.
6. Click any node in the Glance graph and traverse its neighbours
   to any other node via the drawer.

…then v2 is done.

If any of the following are true at that point, v2 is not done:
- "I couldn't see what `<pod>` was thinking."
- "Why is this still custom code?"
- "Where's the meeting transcript?"
- "Why is there a port number anywhere on screen?"
