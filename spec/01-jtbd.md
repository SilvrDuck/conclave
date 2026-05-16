# 01 — Jobs-to-be-Done

**Tool**: Jobs-to-be-Done (Christensen / Ulwick).
**Aim**: pin down the outcomes that matter, decoupled from the v1 UI.

## Two planes, two persona sets

Conclave has two distinct planes. They never share a UI.

### Plane A — Building conclave (the platform itself)

| Persona | Who | What they want |
|---------|-----|----------------|
| **Architect** | The human designing conclave (today: Thibault) | Make the platform real, beautiful, plug-and-play. Use OSS over custom. |
| **Developer** | An LLM coder (today: Claude) acting under architect direction | Write platform code, fix platform bugs, never drive a running conclave. |

The architect's surface is *this repo*. The developer never appears on
plane B.

### Plane B — Conclave runtime (using conclave to build something)

| Persona | Who | What they want |
|---------|-----|----------------|
| **Augustus** (the operator) | A human director, not a coder | Have a microservice app built for them. Watch the team work. Course-correct. |
| **Pod agents** | Autonomous LLM agents (one per service) | Build / manage one service end-to-end. Coordinate with peers. |

The two persona sets never overlap. This spec focuses on Augustus
because plane A is the project's own work — its acceptance is in
[03-prototype-audit](03-prototype-audit.md) (lessons) and
[08-v2-acceptance](08-v2-acceptance.md) (criteria).

## Augustus — the nine jobs

Augustus is not coding. He directs. He watches. He occasionally
intervenes. Each job below is something he tries to accomplish in a
session, the *circumstances* that trigger it, and the *outcome* that
counts as success.

> Notation per JTBD entry:
> *When … I want to … so that …*
> followed by frequency and the *success signal* (what the UI must
> make legible for the job to count as done).

### J1 — Issue / refine a direction

*When* a new direction is needed (new project, mid-course pivot, scope
extension), *I want to* state it once in plain language *so that* the
team starts on it immediately and I don't have to repeat myself.

- Frequency: 1–10 per session.
- Signal: within 3 s of submitting, every relevant agent has the new
  direction in its inbox, the new proclamation shows on the timeline,
  and a placeholder decision tablet exists for the architecture it
  implies.

### J2 — Glance and sense health

*When* I'm doing other things and look up at the conclave window, *I
want to* know within 2 seconds whether things are healthy, stuck, or
in active progress, *so that* I can either go back to other work or
zoom in.

- Frequency: constant (passive).
- Signal: one high-contrast indicator per axis (project age, agents
  active, agents blocked, last meaningful event). No decoding required.

### J3 — Catch up after being away

*When* I come back from lunch / overnight, *I want to* read a digest
of meaningful events (admissions, decisions, deployments, votes), *so
that* I'm caught up in under a minute without scrolling.

- Frequency: a few times a day.
- Signal: a chronological digest of *named* events (not every bus
  ping), grouped by epoch, with one-line summaries. Sub-minute read.

### J4 — Watch one agent think

*When* something feels off with one pod ("`auth` has been thinking
for 4 minutes"), *I want to* read its live token stream + current
tool calls *so that* I can tell whether it's progressing, stuck, or
hallucinating.

- Frequency: as-needed.
- Signal: a per-pod transcript that updates live, with tool calls and
  results highlighted, and a clear "still thinking" / "idle since X"
  state.

### J5 — Witness a meeting

*When* agents are debating something cross-cutting (who owns lyrics?
should we adopt `meilisearch`?), *I want to* see the meeting and its
minutes *so that* I understand how the decision was reached and can
intervene if needed.

- Frequency: several per session.
- Signal: every council / chatroom appears as a readable thread with
  named participants, time-ordered messages, and (when closed) a
  one-paragraph summary that becomes the ADR body.

### J6 — Try what they built

*When* I want to test the running app, *I want to* open it from the
dashboard in one click *so that* I'm not hunting for URLs / ports.

- Frequency: many times a session.
- Signal: a first-class "apps" surface listing every running pod's
  public URL with a thumbnail / endpoint map. One click → new tab.

### J7 — Course-correct

*When* I see a pod heading the wrong way, *I want to* nudge it ("no,
lyrics is its own pod") *so that* I redirect without having to
re-issue a full proclamation.

- Frequency: a few per session.
- Signal: a per-pod DM affordance whose message lands in the pod's
  inbox the same way a proclamation would. Pod must reply / ack.

### J8 — Vote when asked

*When* a pod proposes something that needs the emperor's nod (rare:
exile, charter overhaul, project completion), *I want to* see the
proposal with full context *so that* I can vote without spelunking.

- Frequency: rare.
- Signal: an inbox of pending votes with one-line summary + full
  rationale + ballot affordance. Augustus can vote or pass.

### J9 — Detect stuck

*When* anything is stuck (a vote past its deadline, a pod thinking too
long, a service failing health checks, a council with no recent
messages), *I want to* be told *so that* I don't discover it by
accident.

- Frequency: passive.
- Signal: a "stuck" tray surfacing each blocked thing with a one-line
  reason and a one-click action (force-close vote, restart pod, nudge
  council).

## Four perspectives (collapsing the nine jobs)

The nine jobs naturally cluster into four high-level perspectives.
Each gets equal weight in the UI; layout is downstream of this list
(see [07-c4](07-c4.md)).

| Perspective | Jobs served | Headline |
|-------------|-------------|----------|
| **Glance** | J2, J9 | Ambient health, blockers, last event. |
| **Witness** | J3, J5, J8 | Meetings, decisions, history. |
| **Try** | J6 | Launcher for the running apps. |
| **Direct** | J1, J4, J7 | Proclaim, DM, watch one pod think. |

Source for this clustering: the architect explicitly said all four
matter equally, captured in [v1 retro](archive/v1-retro-alpha-1.md).

## The interconnection invariant

Across all four perspectives, **every domain entity is a node in a
navigable graph** — click any one to traverse to its neighbours:

| Click… | Reaches… |
|--------|----------|
| Agent | service owned · agents called / calling · meetings in · decisions co-authored · proclamations descended-from · live token stream · charter · endpoints |
| Meeting | participants · triggering proclamation · proposals produced · decisions sealed · transcript |
| Proposal | proposer · sortition pool · ballots · resulting decision · affected agents |
| Decision | proposal sealed · participants · affected services · originating proclamation |
| Proclamation | spawned agents · proposals · decisions · apps deployed |
| App / service | owning agent · upstream / downstream services · endpoints · decisions that shaped it |

Without this graph, J4 / J5 / J7 / J8 all degenerate.

## What Augustus is *not*

- Not a coder. Doesn't read raw logs.
- Not a peer in the senate (he doesn't ballot every proposal — only the
  rare imperial ones, J8).
- Not the keeper of any uptime / fault budget. The conclave is dumb
  infrastructure; he just sets direction.
- Not a developer of conclave. Conclave-as-product is plane A; the
  architect and the LLM developer live there.

## Anti-jobs (things the v1 UI optimised for that we don't need)

- **"Read p95 latency budgets."** Augustus doesn't care. Trace
  reactivity is platform plumbing.
- **"Inspect NATS topics."** Internal detail.
- **"Configure slot adapters from the UI."** Configure is a
  bootstrap-CLI / YAML concern (see [00-vision](00-vision.md)
  bootstrap UX call).
- **"Edit a charter from scratch in a textarea."** Edit, yes —
  *from scratch*, no; the editor must load the current text.
