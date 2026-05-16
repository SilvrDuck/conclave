# Retro — Alpha 1 (post-v1 acceptance walkthrough)

Date: 2026-05-16
Author: architect feedback, captured by the developer
Status: triage — none of these are fixed yet

This retro captures what the architect saw watching the system run
after the v1 spec was checked off. v1 acceptance passed in isolation;
this is the gap between "every box ticked" and "feels like the system
described in the brainstorm."

> Note on planes. The conclave project has two: (1) **building
> conclave** — architect (the user) directs, developer (me) writes the
> code; (2) **conclave runtime** — Augustus operates the UI, pod agents
> act autonomously, the developer does not exist on this plane. This
> retro lives on plane 1: the architect is telling the developer what
> the runtime needs to become.

---

## Raw feedback (verbatim, lightly grouped)

### Senate / proposals / ADRs

- **Open proposals with passed deadlines linger.** There are a bunch of
  deadline-passed open proposals just sitting there. Something should
  close them — either auto-tally when the deadline elapses, or sweep and
  mark expired.
- **Proposals have no text.** The user cannot know what they were. The
  proposer's rationale or summary is missing from the UI (and possibly
  from the payload). A proposal needs to be readable by a human at a
  glance — kind + one-line summary minimum.
- **Tablets (ADRs) are super abstract.** They need a human description.
  Most ADR tablets don't have real text on them explaining what they
  are. The clay→stone metaphor only works if there is actually a
  paragraph on the stone.

### Forum / pods / topology

- **Exiled agents are still on the forum map.** Once a pod is exiled it
  should leave the stage (or move to an "exiled" tray), not keep sitting
  on a column.
- **Agent names like `react-23523`.** Hash-suffix names tell the user
  nothing. Agents should have names that say what service they are
  (`frontend`, `auth`, `transcode`, `catalog`...).
- **First agent should not remain "founder".** It should rename itself
  as soon as it takes a role — e.g. become `frontend` the moment it
  decides that's what it is doing. "Founder" is the spawning role, not
  the working role.
- **The forum should look like a system diagram.** Agents as services,
  with the visible relationships between them. Right now it's a row of
  marble figurines on columns; it should read like an architecture
  diagram of a running microservice mesh.
- **No databases / infra visible.** We should see databases and other
  shared resources, and which agent is connected to which. The system
  diagram needs more than just the agent nodes.
- **No communication lines between agents.** I don't see any edges. If
  `frontend` is calling `auth`, that should be a visible line on the
  stage — preferably live (lit when in use, dim when idle).

### Agent communication

- **No chatrooms visible between agents.** No meeting minutes. The
  brainstorm has agents convening councils to decide things; in the UI
  there is no surface for that. Where are the conversations?
- **Opening an agent modal should show its complete stream of tokens.**
  Right now the pod modal shows status pills and URLs but not the live
  agent transcript. The operator needs to read what the agent is
  actually thinking and saying.

### UI / liveness

- **No spinners or "working" affordance.** Nothing on the UI tells you
  an agent is currently thinking — maybe a thinking cloud above the
  marble figure? The activity log scrolls but the stage itself is
  static. The pod marble going from `idle` → `thinking` should be
  visually obvious from across the room.

### Naming / charter

- **"Tabularium" is too exotic a name.** Rename. (Sub-text: the Roman
  metaphors are nice but some words land as friction instead of
  flavour.)
- **Charter editor should show the current agent prompt.** Today the
  editor is a blank textarea that decrees a *new* charter; it should
  load the agent's existing system prompt so you can edit it instead of
  rewriting from scratch.

---

## Bias for the next iteration

> "The system overall for now should be biased towards microservices
> for everything. The goal is to have the agents discuss their role and
> take opportunities based on who they are in the system."

This reframes the design target. The conclave isn't "a swarm of
generic agents that happen to write code"; it's "a self-organising
microservice mesh where each agent IS one service and chooses what to
build based on its identity and what the other services need." Every
following decision should be measured against that.

Concrete implications that fall out of this bias:

- Agents own a **role identity** (frontend, auth, db, transcode…), not a
  hash. The first thing a new pod does is name itself per its mandate.
- The forum is a **live architecture diagram**, not a tableau. Nodes are
  services, edges are real calls, infra (DB, queue, bus) shows up as
  distinct node shapes.
- Inter-agent **chatrooms / councils** are first-class. Every proposal,
  every cross-cutting decision, every "hey, should this be in my pod or
  yours?" leaves a readable trail.
- Proposals and ADRs **read like the README of a tiny service**: title,
  one-line summary, rationale, affected services. Empty stone tablets
  are a bug.

---

## Triage / suggested next moves (not implemented yet)

| # | Item | Likely fix area |
|---|------|-----------------|
| 1 | Auto-close expired proposals | `senate_ledger` deadline sweeper |
| 2 | Proposal summary in payload + UI | `core/models.Proposal.summary` + Forum cartouche |
| 3 | ADR body must be non-trivial | seal-ADR validator + Pi charter rule |
| 4 | Hide / tray exiled pods | `Forum.tsx` stage filter |
| 5 | Pods rename themselves on role assignment | `state.rename_self` MCP + observer rebroadcast |
| 6 | System-diagram layout (services + infra + edges) | `Forum.tsx` rewrite of stage layer |
| 7 | Infra nodes (DB, bus, queue) on stage | observer projection from `pod_activity` + new infra registry |
| 8 | Live call-edges between pods | bus-tap on `coms.send` + edge animation |
| 9 | Chatroom view + meeting minutes | `/state/chatrooms` already exists — needs UI |
| 10 | Token-stream view in pod modal | `pi.py` output_tail → `/state/pod-output/{pod}` SSE |
| 11 | Thinking-cloud / working indicator | `pi_state` already projected — needs animated affordance |
| 12 | Rename "Tabularium" | search/replace + UI copy |
| 13 | Charter editor pre-loads current charter | observer `/state/charter/{pod}` + edit modal |

None of these are bug fixes against the v1 spec — they are the gap
between "the spec passed" and "the system feels like itself."

---

## What a successful v2 prototype must showcase

v1 proved the platform can boot, proclaim, admit a single pod, and ship
a one-shot demo. v2 has to showcase the **full system** — not just
prove the wiring works, but be watchable as a self-organising team.

Hard criteria for v2:

- **Real multi-pod app deployed.** A non-trivial, multi-microservice
  application has to actually come up at the end of the run. Not a
  single pod with three endpoints — multiple cooperating pods, each
  owning a service, with visible inter-service calls.
- **Meetings are observed.** Council / chatroom conversations between
  agents have to be visible and readable in the UI as they happen.
  Decisions made together leave minutes. If the agents only talk
  through proposals, that isn't a meeting — the retro feedback above
  (chatrooms, comm lines, token streams) is the prerequisite.

### v2 theme: "do a Spotify clone"

The test proclamation will be a **Spotify clone**. The theme is chosen
because it naturally pulls toward a microservice split — catalog,
streaming, auth, playlist, lyrics, social/jam, transcode, recommend —
without anyone having to be told.

Rule for writing the test proclamation:

- The proclamation stays **feature-based**, not architecture-based. We
  ask for what the user wants to do, not which services should exist.
  Good: "users can listen to music, see lyrics scroll, and start a
  shared listening jam with a friend." Bad: "spawn a catalog service, a
  lyrics service, and a jam service."
- The interesting features (lyrics store, jam / shared-listening, maybe
  recommendations or social feed) are picked because they obviously
  *imply* additional services — the agents have to discover that split
  themselves and propose the right pods. That discovery, debated in
  visible chatrooms, is what v2 is showcasing.

If at the end of a v2 run we see: one feature-shaped proclamation, a
visible debate where pods decide who owns what, a system-diagram forum
with several named service pods + their infra + their call edges, and a
working Spotify-clone UI talking to those services — v2 is done.

---

## UX direction for v2

Grounding from current UX practice (agent observability tools, dev
dashboards, dashboard design heuristics): transparency + intervention
at every step; at-a-glance overview that is scannable without decoding;
progressive disclosure (overview → one-click drill-down → full trace);
5–6 cards per view max; organise around jobs-to-be-done not features.

### Persona

**Augustus the operator.** Not a coder; a director. Wants the system
to build apps for him. Doesn't read raw logs. Cares about: is it
working, are we on track, can I see what they decided, can I redirect
them, can I try the result?

### Jobs-to-be-done

1. "Tell the conclave what I want built next" — issue / refine a proclamation.
2. "Glance at the room and tell if things are healthy" — ambient awareness.
3. "Catch up after being away" — digest of meaningful events.
4. "Watch what `frontend` is actually doing right now" — live token stream of one pod.
5. "Witness the agents debating who owns lyrics" — meetings / councils with minutes.
6. "Open the thing they built and try it" — first-class launcher for the deployed apps.
7. "Course-correct: no, lyrics is its own pod" — nudge / DM / follow-up proclamation.
8. "Vote / weigh in when pods ask me" — visible inbox for senate proposals.
9. "Is anyone stuck?" — block detection (pods thinking too long, failing services, missed deadlines).

### Two load-bearing principles

These two are the spine of v2's UX. Layout decisions come after.

**1. All four jobs matter equally and each gets its own perspective.**

Glance, witness meetings, try the apps, and direct — none of these is
the primary one we optimise for at the cost of the others. They each
get a dedicated perspective:

- **Glance & sense health** — ambient awareness; sparse, high-contrast.
- **Witness meetings & decisions** — the conversation is the headline.
- **Try what they built** — launcher view for the deployed apps + endpoints.
- **Direct & course-correct** — proclaim + vote inbox + per-pod DM.

How these perspectives are exposed (tabs, modes, filters on one
screen, separate routes) is a downstream layout decision — see
"Layout, secondary" below. Don't lock it in yet.

**2. The UI is a navigable graph of interconnected entities.**

Every domain object in the UI is a node in a navigable graph;
clicking any one fans out to its neighbours, and the neighbours are
clickable to recurse. Tokens, charters, transcripts are *reachable
through this graph*, not the destination by themselves.

| Click… | Reveals (linked entities) |
|--------|---------------------------|
| **Agent** | service it owns · agents it calls / is called by · meetings it's in · ADRs it co-authored · proclamations it descends from · charter · live token stream · agenda · endpoints |
| **Meeting / council** | participating agents · the proclamation that triggered it · proposals it produced · ADRs it sealed · transcript |
| **Proposal** | proposer · sortition pool · ballots so far · the ADR it will seal into · affected agents |
| **ADR (tablet)** | proposal it sealed · participating agents · affected services · the proclamation it traces back to |
| **Proclamation** | spawned agents · resulting proposals · sealed ADRs · apps that came out of it |
| **App / service URL** | owning agent · upstream / downstream services · endpoints · ADRs that shaped it |

So the drill-down is not "click pod → see pod's stuff." It is
"click anything → see its neighbours, then click a neighbour, recurse."
The UI becomes a small interactive knowledge graph of the running
system. The token stream / charter / meeting transcripts are *one* of
the things you reach this way, not the only destination.

### Layout, secondary

The *layout* (single ambient screen, job-shaped tabs, stage-centric
with overlays, persistent split panes, etc.) is downstream of the two
principles above and intentionally left open. Whatever layout v2
ships, the test is:

- Does it serve all four perspectives at roughly equal weight?
- Can Augustus click any entity (agent / meeting / proposal / ADR /
  proclamation / app) and reach all its neighbours from there?

A possible v0 sketch (one option, not the answer):

```
┌────────────────────────────────────────────────────────────────┐
│ CONCLAVE • proclamation III in flight    [Proclaim] [Apps ▾]  │
├──────────────────────────┬─────────────────────────────────────┤
│  system diagram          │ activity ticker                    │
│  (services + edges +     │ open proposals                     │
│   infra)                 │                                    │
├──────────────────────────┴─────────────────────────────────────┤
│ Apps:  [spotify-clone ↗ :8800]  [admin ↗ :8801]                │
└────────────────────────────────────────────────────────────────┘
```

### Implementation gates (layout-agnostic)

- The current first-run **Wizard** must disappear once the instance is
  seeded — it has no place on a running deployment.
- The current Forum / Senate / Activity tab split (tabs named after
  backend modules) gets replaced by **job-shaped perspectives**, in
  whatever shell makes the interconnection work.
- The **system-diagram stage** (services + edges + infra) blocks
  several perspectives — that one piece is the foundation of v2's UI
  regardless of which layout we end up choosing.
- The **graph drill-down** must hold across all perspectives — i.e.
  clicking an agent in the meetings view is the same entity click as
  in the apps view; selection persists, history is navigable.

### Sources

UX grounding came from:
- [Agent UX: designing UI for AI agents in 2026 (fuselabcreative)](https://fuselabcreative.com/ui-design-for-ai-agents/)
- [Best AI Observability Tools for Autonomous Agents in 2026 (Arize)](https://arize.com/blog/best-ai-observability-tools-for-autonomous-agents-in-2026/)
- [AI Agent Observability: A Complete Guide for 2026 & Beyond (Atlan)](https://atlan.com/know/ai-agent-observability/)
- [Dashboard Design UX Patterns Best Practices (Pencil & Paper)](https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards)
- [Building dashboards for operational visibility (Amazon Builders' Library)](https://aws.amazon.com/builders-library/building-dashboards-for-operational-visibility/)
- [Effective Dashboard Design Principles (UXPin)](https://www.uxpin.com/studio/blog/dashboard-design-principles/)
- [Personas vs. Jobs-to-Be-Done (NN/g)](https://www.nngroup.com/articles/personas-jobs-be-done/)
