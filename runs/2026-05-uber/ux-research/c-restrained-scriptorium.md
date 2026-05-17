## Proposal C: The Restrained Scriptorium — observability that reads like a folio

The architect runs a 10-pod swarm. He needs Linear-grade density and the calm of a well-set page. Every manuscript flourish must earn its rent in *legibility* — Tufte's "approximately right rather than exactly wrong", not stained-glass nostalgia. Parchment is the chrome; the data is the ink.

### Information architecture

One window. No tabs named after backend modules. Four **perspectives** addressable by URL, not navigation: `/glance`, `/witness`, `/try`, `/direct`. Each perspective is a *page layout preset*, not a separate app; the same entities surface in all four, the layout simply changes what's foregrounded.

Crosscutting routes:
- `/p/:pod_id` — pod folio (drawer-shaped, opens over the current perspective)
- `/m/:council_id` — council thread
- `/d/:decision_id` — decision plate
- `/x/:proclamation_seq` — proclamation page (`№ III`)
- `/inbox` — Augustus's pending-action stack (J8, J9)

The graph is **persistent inhabitant of Glance** and a small navigator strip at the top of Witness/Try/Direct. Click anything anywhere → a drawer slides from the right with the entity's folio; every blue-underlined reference inside the drawer is itself a route. This is the §9 click-traverse invariant made concrete.

### Page-by-page layout

**Shell.** A 32px-tall **bandeau** across the top: scriptorium wordmark "CONCLAVE" in Cinzel small-caps at left; the current proclamation numeral "№ III" centre, ellipsis-truncated text on hover; on the right four perspective toggles as Radix `ToggleGroup` (Glance · Witness · Try · Direct), then a single status dot (green/amber/red parchment-ink). No sidebar. The bandeau is the only persistent chrome.

**Glance.** Single full-bleed pane. ReactFlow canvas with custom nodes; edges are real OTel-derived calls (Path D). The graph background is parchment (#F4ECD8) with a faint vellum noise SVG fill at 4% opacity — never animated, never moves. Each pod is a **Cartouche** node (see Components). The simulator pod (§0.5) gets a slightly larger frame and a hairline gold rule top-and-bottom — heraldic, not luminous. A 220px-wide **Roll** anchors the right edge: append-only activity sparkline-and-line per epoch, last 200 named events. Bottom-left, a **Stuck Tray** (collapsed by default, expands on hover) listing pods with `agent_state=stuck` and one-click force-actions. No metric counters. No "0 pods" zero state — empty Glance shows only a single inline proclamation field on parchment, vertically centred (§1).

**Witness.** Two columns, 60/40. Left: **Codex of Proclamations** — vertically stacked, reverse-chronological, each proclamation rendered as a real page (drop cap, justified body, scribal numeral, gutter for cross-refs). Beneath each proclamation, indented, its descendants: councils → decisions → image-swaps, every link clickable. Right column: when you click a council, its thread fills here; when you click a decision, its plate fills here. The right column is essentially the focused entity, the left column is "everything you can reach from here." This satisfies J3 (digest), J5 (witness meetings), J8 (read full ballot context).

**Try.** A grid of **Plaques** (Radix `Card` with manuscript framing) — one per pod with a public HTTP service. Each plaque shows: display-role in Cinzel small-caps; hostname (`rider-app.conclave.local`) in mono; a 64px endpoint sparkline (Tufte-mode: requests-per-minute over the last hour, no axes, gray normal-range band); an "Open" button that opens the app in a new tab. Adopted-pod plaques carry a small `image:tag` badge in mono. One column on narrow screens, three on wide. This is J6, no theatre.

**Direct.** Two stacked sections. Top: **Charter Editor** — when a pod is selected, its `charter.md` pre-loads (§11) in a serif diff view, with the original as faded ink and edits as new ink; one "Submit edit" affordance commits. Bottom: **DM thread** for the selected pod, posting goes through `coms.dm` (J7). Right-side drawer always shows the pod's live token stream (J4) — this is the only place where the agent's prose is the headline.

**Pod folio (drawer over any perspective).** Three vertical bands inside one Radix `Sheet`. Band 1: identity (display-role in Cinzel, stable id in mono, charter excerpt, image strategy). Band 2: **Live agent transcript** — OpenLLMetry stream, monospaced, tool-call lines rendered as miniature plates (`tool: senate.propose_member` inset in a 1px gold frame). "Thinking since 14:23" stamp at top. Band 3: **Neighbours** — services this pod calls / is called by (mini-graph), councils it sits in, decisions it co-authored, proposals it has open. Every line a route.

### Dominant components

1. **Bandeau.** The 32px scriptorium top bar. Cinzel wordmark, numeral, perspective toggle, single health dot. No icons except one.
2. **Cartouche.** The pod node on the Glance graph. Oval parchment frame, display-role in Cinzel small-caps inside, a 12px **state pip** (running/stopped/stuck) at top-right, a 24×6 endpoint-traffic sparkline at the bottom. Placeholder pods are dashed outline, admitted pods are solid, exiled pods are crossed-through.
3. **Phylactery.** The message bubble in council threads. Speech-scroll silhouette with a 16px sender heraldry (a deterministic two-letter monogram in Cinzel on a coloured field; same colour per pod throughout the app — this *is* the pod's identity colour). Augustus's DMs use a gold ink and a square frame instead of a scroll.
4. **Plate.** The decision card. Bordered like a printed plate from an 18th-century scientific journal: 1px rule top + bottom, decision title in Cinzel, body in serif, "Sealed N V MMXXVI" footer in scribal numerals, affected pods as monogram row.
5. **Roll.** The right-edge activity feed in Glance. Each entry is one line: timestamp (mono, dim), event-name (small-caps, Cinzel-medium), one-sentence summary (serif). Hour markers as fine rules. No icons.
6. **Ballot Strip.** The senate cartouche's voting row. One pip per eligible voter (monogram if cast, hollow circle if pending, dash if abstain). For sortition, undrawn voters are greyed parchment. Strategy badge to the left in Cinzel small-caps: `MAJORITY` / `SUPERMAJORITY` / `CONSENSUS·OMNIUM` / `SORTITION`. Deadline countdown in mono.
7. **Folio.** The right-drawer pod page. Three bands above. Radix `Sheet`.
8. **Codex.** Witness's left column — the vertical timeline of proclamations and their descendants. Indentation = parent/child. Drop cap on every proclamation, never on anything else.
9. **Marginalia.** The 8px-wide gutter strip beside any long body of text (charter view, decision body, council summary) where cross-references appear as small Cinzel numerals — click → drawer to that reference. This is where the manuscript skin earns its keep: it makes the §9 graph-of-everything visible without cluttering the page.
10. **Stuck Tray.** Bottom-left fold-out on Glance. One row per stuck thing, with a Cinzel verb-button (`NUDGE` / `RESTART` / `FORCE·CLOSE`). Only component allowed to use red.

### Typography

Three faces. Restraint is the design.

- **Cinzel** (display, all-caps and small-caps only). 11–14px. Used for: wordmark, perspective toggle, proclamation numerals, decision titles, strategy badges, named-event labels in the Roll, Tray verb-buttons, pod display-roles on cartouches. Never for body. Never above 28px — this is not a poster.
- **EB Garamond** (body serif). 14px default, 13px in dense tables, 15px for proclamation bodies. Used for: proclamation text, charter prose, decision bodies, council messages, summaries, council thread itself. Justified only inside the Codex; left-aligned everywhere else. **One drop cap** per proclamation, EB Garamond uppercase, two-line height, slightly inset. No drop caps anywhere else — a drop cap means "this is a proclamation."
- **JetBrains Mono** (mono). 12px. Used for: pod stable IDs, hostnames, image tags, timestamps in the Roll, OpenLLMetry transcripts, tool-call payloads, charter diff line numbers, schema names in hover-detail (§11 keeps them off normal surfaces).

Scribal numerals (`№ III`, `V·MMXXVI`) appear only on proclamation numbers and decision-sealed dates. Everywhere else, Arabic numerals in mono. The hard rule: **if you can't tell what a number means at a glance, the design fails.**

Line-height 1.45 for serif body; 1.2 for Cinzel; 1.5 for mono streams. 8px spacing scale (8/16/24/32/64), borrowed wholesale from Linear.

### Palette

Calm parchment. The Forum is never bright; it is also never grey-on-grey.

| Hex | Role |
|---|---|
| `#F4ECD8` | Parchment — page background, primary surface. |
| `#E8DCC0` | Vellum — secondary surface (drawer, dialog, cartouche fill). |
| `#1F1A14` | Iron-gall ink — primary text, primary stroke. |
| `#6B5E48` | Faded ink — secondary text, hairline rules, axis-less sparkline strokes. |
| `#A48143` | Gold leaf — accent only: proclamation numerals, sealed-decision rule, selected node ring, Augustus DM ink. **Never used as fill, never used for hover state.** |
| `#3B5A3C` | Verdigris — "running" / healthy state pip, edge animation when a call fires. |
| `#7A1F1F` | Cinnabar — "stuck", deadline-passed, exile vote. Only red in the system. |
| `#C8BFA5` | Wash — disabled state, dashed-outline placeholders, normal-range gray band on sparklines. |

Dark mode is `#1A1714` ink-on-parchment inverted to ink-on-board with the same gold/verdigris/cinnabar — same semantics, no second design.

### Motion & decoration policy

**Allowed.**
- Edge "ink-bloom" when an OTel call fires (verdigris, 800ms, opacity 0→1→0.4, no easing past the peak). This is the W1 acceptance check — visible within 5s.
- Drawer slide from the right, 220ms, Radix default.
- Token stream: characters append as they arrive; no caret-blink, no typewriter sound (obviously).
- Proclamation drop-cap fades in once on first render, then static forever.
- Stuck-pod pip pulses cinnabar at 1.5Hz. The only periodic animation.

**Forbidden.**
- Ambient parchment-curl, page-turn page-flip, candleflicker, illuminated borders that move.
- Hover scale on cards. Hover changes the rule from `#6B5E48` to `#1F1A14`. That's it.
- Loading skeletons that shimmer. We use a static "_council pending_" italic line instead — Tufte over Lottie.
- Confetti on decision-seal, ever.
- Decoration that overlaps content. The gold rule above a sealed decision sits *above* it, not *across* it.

The principle: **animation is reserved for events that happened in the system**, never for ones that happened in the UI.

### JTBD coverage

- **J1 (proclaim).** Glance empty state and the bandeau both expose a single proclamation field; submitting renders a fresh proclamation page in Witness within 3s (§2).
- **J2 (glance health).** Bandeau status dot + Glance graph state pips + Stuck Tray. Two-second read.
- **J3 (catch up).** Witness's Codex shows proclamations and named descendants grouped by epoch; the Roll on Glance is the wider stream. Sub-minute read because every entry is a sentence, not a row.
- **J4 (watch one think).** Pod folio band 2 — live OpenLLMetry stream with tool calls as plates and a "thinking since" stamp. Always available via drawer from any node click.
- **J5 (witness meetings).** Witness right column renders the council thread when a council is clicked; Phylacteries with sender monograms; closed councils show the summary in a final framed Plate inline.
- **J6 (try).** The Try perspective: one Plaque per public pod, hostname + endpoint sparkline + "Open" link.
- **J7 (course-correct).** Direct perspective: per-pod DM thread + charter diff editor; live token stream stays visible in the drawer so Augustus sees his nudge land.
- **J8 (imperial vote).** `/inbox` lists pending ballots as Plate-shaped cards with full rationale and a ballot affordance; selecting one opens its proposal page (kind/strategy/eligibles/deadline/rationale).
- **J9 (detect stuck).** Stuck Tray on Glance; cinnabar pulse on the cartouche's pip; one-click Tray verbs (`NUDGE`, `RESTART`, `FORCE·CLOSE`) hit Observer's command endpoints.

### Risks / trade-offs

1. **Cinzel small-caps at 11–13px will be the legibility canary.** On a low-DPI external monitor the flared serifs blur. Mitigation budget: if QA shows it fails, swap Cinzel for **Trajan Pro** or fall back to **IBM Plex Serif** uppercase-tracked-+0.08em for the same semantic role; the design's identity does *not* hinge on Cinzel specifically, it hinges on "Roman small-caps reserved for one job."
2. **Parchment palette has a narrow contrast ceiling.** Iron-gall on parchment is fine (AA-passing) but anything *non-text* — small icons, the state pips, sparkline strokes — needs aggressive testing. A senior dev squinting at a Stuck Tray pip at 2am must read it; cinnabar must read against vellum, not just parchment. Bring the contrast checker to the design review.
3. **The drop-cap-only-on-proclamations rule is easy to violate.** A junior contributor will inevitably add a drop cap to a decision body because "it looked nice." The rule needs to be encoded as a single `<Proclamation>` component — not a CSS class anyone can apply — and lint-enforced. Without that discipline, the manuscript becomes theme-park.
