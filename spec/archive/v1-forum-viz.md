# Forum View Redesign — feedback doc

**Status**: brainstorm. No code yet — call this when you want it implemented.

## Framing: the user is the emperor, not a peer

The user **is not** the founder, is not "another voice in the senate", does
not propose alice or vote on contract changes. The user is Augustus — the
person whose word starts the project and (occasionally) reorients it. Two
verbs, full stop:

- **Proclaim**: "Let's build a Netflix clone." / "Pivot toward a kanban
  tool instead." / "We need this shipped by tomorrow." High-level intent,
  never an implementation directive.
- **Decree** (rare, blunt): edit a charter, exile a pod, halt the senate.
  Goes through the same UI but is visibly heavier.

The senate brainstorms; the emperor sets the horizon. Pi-as-founder reads
the proclamation, decides on the smallest viable set of peers, proposes
them, and the resulting peer group deliberates the first architecture.
Whether the project ends up monolithic, three-pod, or six-pod is an output
of that deliberation, **not** something the user spelled out in the
proclamation.

### How that changes the UI surface

- The mandate input is renamed **proclamation** (or `Edictum` if we lean
  into the bit). No target-pod selector — proclamations go to the project,
  which in practice means the founder's inbox plus a bus broadcast on
  `system/mandate`. If the founder is not running, the proclamation seeds
  the founder pod and then wakes it.
- The text reads heavy on submit: "Augustus has spoken." or "The Emperor
  proclaims:" then the text echoes back on the senate band as a marble
  tablet. Not in a corner; *front and centre*. The pods spin up under it
  visually — the proclamation is the cause, the pods are the consequence.
- A **proclamation timeline** along the top: each proclamation a stone
  cartouche with a timestamp + the first 60 chars. Click to expand to the
  full text and see which ADRs trace back to it.
- The Wizard view's "issue first mandate" step is replaced by the same
  proclamation UI inline on the Forum. There is no separate "launch"
  ceremony — the first proclamation IS the launch.

### The first ADR — a placeholder, not a decree

Today, the first ADR is whatever the founder happens to write as part of
its admission. That's the wrong shape. The right shape:

1. Emperor proclaims `"build a Netflix clone"`.
2. Spawner brings up the founder pod with an **empty placeholder ADR
   pre-seeded** at `adr-0001` with title "Architecture for: build a
   Netflix clone" and body `_pending senate council_`. The Tabularium
   shows it as a clay tablet (not yet stone) with a dashed border.
3. Founder reads the proclamation + the placeholder, calls
   `senate.propose_member` for a small group of peers it thinks the
   project needs (e.g., `catalog`, `streaming`, `auth`, `web`). Each
   proposal includes a one-line "why I think this pod is needed" rationale
   that gets attached to the placeholder ADR as a draft note.
4. Once peers are admitted, the founder convenes a council
   (`coms.convene_council`) on the topic "first architecture". Each peer
   contributes their view. The council closes with a summary that becomes
   the **finalised body** of `adr-0001`. At that point the tablet hardens
   from clay to stone in the Tabularium.
5. From there it's normal Conclave: peer councils, contract-change
   proposals, ADR per decision.

The placeholder is important because it gives the user something to look
at the moment they hit "Send" — and a visible "brainstorm in progress"
state instead of an empty `state/members` and `decisions_list_adrs`
returning `[]`. The clay→stone transition is a visual heartbeat: the
project is *becoming* something.

### What the spawner needs to do to support this

- On the very first proclamation (i.e. no founder yet running):
  1. Seed `pods/founder/` if missing.
  2. Launch the founder container.
  3. **Pre-seed the placeholder ADR via the senate REST surface**
     (`POST /adrs` with a `status: placeholder` field — needs a column
     added to the ADR row) so it shows up in the Tabularium before any
     agent has even loaded.
  4. Publish `goal_updated` with the proclamation text to the founder's
     inbox.
- On a second-or-later proclamation, no seeding; just publish.
- Detect "is the founder already running?" via
  `docker ps --filter name=^conclave-founder$`.

### Imperial vs senate language in the rest of the UI

- Forum: the proclamation belongs to "the Emperor". Pod sprites continue
  to look like Roman characters; they remain peers.
- Tabularium: ADRs sealed with the senate's "S·P·Q·R" mark. Placeholders
  show a draft seal.
- Council: chatrooms styled as the senate floor. The user can read but
  cannot speak — the senate is the senate; the emperor doesn't sit on it.
- Charter Editor: this is the one place the emperor can override the
  senate (per spec §13 — charter edits are a user write path). Style it
  as "Imperial decree" with a heavy serif and a "stamp before signing"
  confirmation step so the user doesn't accidentally rewrite someone's
  identity.
- Exile District: same treatment as charter — exile is also an
  imperial-or-senate action; both paths land here.

### Concretely, the proclamation flow

```
   ┌────────────────────────┐
   │ EMPEROR (the user)     │
   │ "Build a Netflix clone"│
   └──────────┬─────────────┘
              │ proclaim
              ▼
   ┌────────────────────────┐
   │ /control/proclamation  │  (rename from /control/mandate)
   │  • seed founder if     │
   │    not running         │
   │  • pre-seed placeholder│
   │    adr-0001 (clay)     │
   │  • publish goal_updated│
   │    to pod/founder/inbox│
   │  • broadcast on        │
   │    system/mandate      │
   └──────────┬─────────────┘
              │
              ▼
   ┌────────────────────────┐
   │ Founder pod            │
   │  reads proclamation +  │
   │  placeholder ADR       │
   │  proposes 3–5 peers    │
   │  with draft rationales │
   │  attached to adr-0001  │
   └──────────┬─────────────┘
              │
              ▼
   ┌────────────────────────┐
   │ Spawner launches peers │
   │ Peers boot, read their │
   │ charters + adr-0001    │
   └──────────┬─────────────┘
              │
              ▼
   ┌────────────────────────┐
   │ Founder convenes       │
   │ council on first       │
   │ architecture           │
   │ Peers deliberate       │
   │ Council summary becomes│
   │ finalised adr-0001     │
   │ Tablet: clay → stone   │
   └────────────────────────┘
```

The Forum should make this whole sequence visually obvious as it unfolds.
The proclamation, the empty pods spawning, the placeholder ADR materialising
under the band, the council line lighting up when the council opens, the
tablet hardening when the council closes — that's the "Conclave is alive"
moment we want every demo to land.

## What's wrong today

The current Forum view (`ui/src/views/Forum.tsx`) renders pods as static
domus sprites at hash-deterministic positions on an 800×500 canvas. Polls
`/state/members` every 5s and slaps a yellow halo on pods with an active
`doing` agenda item. It looks fine in a screenshot. It does almost nothing
useful when you're trying to *understand what's happening right now*:

- No way to see **who's talking to whom** — chatrooms are listed in a
  separate tab (`Council`) but the spatial relationship is lost.
- No idea **what's being said** without leaving the Forum to dig through
  message history.
- No visibility on a pod's **HTTP surface** — port, service URL, last call,
  current status — even though the observer knows all of that.
- No sense of **time** — a pod that's been quiet for 6 hours looks identical
  to one mid-turn.
- **Senate activity is invisible** — open proposals, ongoing ballots,
  rejected ADRs. The single most important platform signal is sitting on
  `/proposals` and never shown on the Forum.
- **Agenda items are tucked into the halo** — the most actionable per-pod
  signal isn't readable.
- **The mandate input is missing entirely** — the user has no way to seed
  a new project from the UI.

The Forum should be the one screen a user can stare at and answer:
*what is the system doing, what is each pod doing, what's about to change?*

## Target experience

Think *Roman Forum + Grafana + Figma whiteboard*, in that order:

- A **stage** with pods as columns or domus sprites arranged in a circle,
  not on a hash-grid. Stable positions across reloads (deterministic seed)
  but the layout reads as a senate room, not a coordinate plane.
- **Lines drawn between pods** for live communication: a thin animated line
  for an active chatroom; a thicker, gold one for a council; a directional
  arrow for an HTTP call recorded by the observer's call-graph. Lines fade
  when the corresponding bus topic goes idle for >30s.
- **Hovering a line** pops a tooltip with the conversation: last 5 messages
  (from `/state/chatrooms` + a future `/state/messages/{chatroom_id}`),
  participant list, last_active. No click required — instant.
- **Clicking a pod** opens a slide-out side panel anchored to the pod
  showing:
    * pod name, status, admitted_at, charter excerpt
    * **service endpoint table** — the pod's URL inside the docker network
      (`http://conclave-<pod>:8000` or whatever the harness reports), the
      observed endpoints from `/state/endpoints/<pod>` with method, path,
      annotation, last_seen rate
    * **agenda** — full `doing` / `next` / `blocked-on` lists
    * **recent ADRs** affecting the pod (filter `decisions_list_adrs?pod=<name>`)
    * **proposals** the pod opened or is voting on
- **A senate band across the top** showing open proposals as tiny tablets,
  each colored by strategy (majority blue, consensus gold, supermajority
  red, sortition green) with a ballot mini-bar showing yes/no/abstain
  counts. Hover to see the rationale; click to open the proposal in the
  Tabularium.
- **A mandate input docked at the bottom** — single-line text + Send button
  that POSTs to `/api/control/mandate`. Defaults to the founder pod.
  History dropdown of the last 5 mandates.
- **Time-of-flight indicators on every pod**: a small dot that pulses on
  `pi.event` `turn_start` and grays out on `turn_end`. Lets the user see
  *which agent is thinking right now*.
- **A sliver of system log at the bottom-right** — last 20 lines from the
  bus tap (vote_open, vote_closed, member_admitted, contract_change_proposed),
  in a monospaced trace pane.

## Data the UI already has access to

| Surface                | Path                                       | Notes |
| ---------------------- | ------------------------------------------ | ----- |
| Members + status       | `GET /state/members`                       | Polled |
| Per-pod endpoints      | `GET /state/endpoints/{pod}`               | Polled on click |
| Caller graph           | `GET /state/callers?method=&path=`         | Build line directions |
| Chatrooms              | `GET /state/chatrooms`                     | List + last_active |
| Agenda                 | `GET /state/agenda/{pod}`                  | Polled on click |
| Open proposals         | `GET /api/senate/proposals`                | Senate band |
| ADRs                   | `GET /api/senate/adrs?pod=<name>`          | Pod panel |
| Mandate publish        | `POST /api/observer/control/mandate`       | Already wired |

## Data the UI does **not** yet have (so the redesign needs these)

- **Live messages** — needs a chatroom-message stream. Cheapest option:
  observer subscribes to `chatroom/*` bus topic and projects to a
  `messages` table; expose `GET /state/messages?chatroom_id=&since=`. SSE
  endpoint `/state/messages/stream` for the line tooltip & log pane is
  the principled version.
- **Pi turn telemetry** — the harness already logs `pi.event turn_start /
  turn_end`. Easiest path: have the harness POST a `/ingest/pod-status`
  with `state in {thinking, idle}` per turn boundary. Observer projects
  to `members.status_extra` or a new `pod_activity` table. UI polls or
  subscribes via SSE.
- **Container info** — service hostname, port, image, container started_at,
  status. Sourced from the runtime adapter (`DockerComposeRuntime.list_pods`
  + `docker inspect`); observer ingest endpoint
  `POST /ingest/pod-runtime` from the spawner per launch + a daily refresh.
- **Bus tap** — for the bottom-right trace pane, an SSE endpoint
  `/state/bus-tap?topics=system/observer/*` that proxies the bus
  subscription to the browser.

## Implementation sketch (when we say go)

1. **Backend**: add the four data sources above. Observer gets new
   `pod_runtime`, `chatroom_message`, `pod_activity` tables + ingest paths,
   plus two SSE endpoints (`/state/messages/stream`,
   `/state/bus-tap`). Spawner posts container metadata on launch.
   Harness POSTs `pod_activity` on every Pi turn boundary.
2. **Frontend**: replace the canvas-and-sprites approach with **SVG**
   (better for hover/click hit-testing, accessible, animations via CSS).
   Pods become `<g>` groups with a deterministic-but-aesthetic layout
   (circle / Fibonacci / hand-tuned). Lines are SVG `<path>` with CSS
   `stroke-dasharray` + `animation` for the active-conversation flow.
   Hover tooltips with Radix (or hand-rolled — we already pull SWR).
   Slide-out panel as a fixed-position aside with CSS `transform`
   transition.
3. **Senate band**: a horizontal flex container at the top, each proposal
   a `<button>` that opens a modal anchored at the band.
4. **Mandate input + history**: simple `<form>` at the bottom, `<datalist>`
   for history.
5. **Trace pane**: a fixed bottom-right `<pre>` rendering the last 20
   bus events from the SSE stream, max-height capped.

## Asks before implementation

- Confirm we keep the Roman aesthetic on the new SVG layout — the user
  liked it.
- Decide whether the pod panel slides over the stage (current SPA pattern)
  or pushes the stage left (more discoverable but loses spatial context).
- Decide if the bottom trace pane should be collapsible.
- Choose between SWR-polled refresh (simple) vs SSE everywhere (snappier,
  more backend work).

When you give the word, this becomes a feature branch.
