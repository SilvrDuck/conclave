# Forum View Redesign — feedback doc

**Status**: brainstorm. No code yet — call this when you want it implemented.

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
