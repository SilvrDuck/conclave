# 09 — Forum UX

**Status**: contract for the v2 Forum rebuild. Synthesised by the
architect from three independent UX-research proposals
(`runs/2026-05-uber/ux-research/{a,b,c}.md`). Spec/09 is binding: the
rebuild PR(s) cite the §-numbers below; deviations go through this
spec, not through the code.

> The grand vision is that the architect *sees* the agents' debates,
> personalities and dissent. The Forum is not a dashboard. It is a
> typeset record of a swarm reasoning. Observability of agent reasoning
> *is* the product (see [00-vision](00-vision.md)).

---

## §0 — North-star principles

- **The page is parchment; the data is ink.** Manuscript skin is the
  default chrome, never the exception. Library defaults stay only
  where this spec explicitly grants them (the ReactFlow canvas, mono
  spans for ids/transcripts).
- **Restraint over decoration.** Every flourish must earn its rent in
  legibility — Tufte's "approximately right rather than exactly
  wrong", not stained-glass nostalgia. A senior dev grokking a 10-pod
  swarm at a glance is the user; if a versal makes that harder, it's
  removed.
- **Personality is encoded as quotation, not portrait.** Agents do
  not have avatars, mascots or character art. Their personality is
  what they *say* — verbatim transcript, dissent in council,
  ballot-comment voice. The platform's job is to surface their words
  unmediated.
- **Animation is reserved for events that happened in the system**,
  never for events that happened in the UI. No skeletons, no
  shimmer, no idle decoration loops.
- **Every domain entity is a node in a navigable graph.** Click any
  pod, decision, proposal, council, proclamation, endpoint — open
  its folio in the right-side drawer. The drawer's own links are
  themselves traversable. This is the §9 interconnection invariant
  from [01-jtbd](01-jtbd.md), made concrete.

---

## §1 — Routes & shell

One window. No tabs named after backend modules.

| Route | Perspective | Jobs (from spec/01) |
|---|---|---|
| `/glance` | **Glance** | J2, J9 |
| `/witness` | **Witness** | J3, J5, J8 |
| `/try` | **Try** | J6 |
| `/direct` | **Direct** | J1, J4, J7 |

Crosscutting (open as drawer / page, never tab):

| Route | What |
|---|---|
| `/p/:pod_id` | Pod folio (drawer over current perspective) |
| `/m/:council_id` | Council thread |
| `/d/:decision_id` | Decision plate |
| `/x/:proclamation_seq` | Proclamation page (`№ III`) |
| `/inbox` | Augustus's pending actions (J8, J9 catch-all) |

### Shell chrome

A single **bandeau** across the top, 40px tall:

- **Wordmark** at left: `CONCLAVE` in Cinzel small-caps, 14px.
- **Current numeral** in the centre: `№ III` in Cormorant Garamond
  semibold, with the proclamation's first 60 characters trailing in
  italic, ellipsis-truncated. Click = jump to that proclamation page.
- **Perspective toggle** at right: four-segment Radix `ToggleGroup`
  reading `Glance · Witness · Try · Direct`. Active segment shows a
  gold-leaf hairline beneath; inactive segments are faded-ink.
- **Status dot** + **Reset** at far right: one parchment dot
  (verdigris / amber / cinnabar) for "system breathing / something
  blocked / something dead"; a `Reset` ink-link triggers `POST
  /commands {kind: ResetState}` after a Radix `AlertDialog`
  confirmation.

That is the entire persistent chrome. No sidebar. No icon bar.

---

## §2 — The Glance perspective

Single full-bleed pane.

- **Centre**: ReactFlow canvas with custom **Cartouche** nodes (see
  §6) and OTel-derived call edges (real, not synthetic). Background
  is parchment with a 4%-opacity SVG noise fill — static.
- **Simulator pod** (§0.5 of [08-v2-acceptance](08-v2-acceptance.md))
  renders one frame larger and is bordered top-and-bottom by a
  hairline gold rule. Heraldic, not luminous.
- **Right rail — the Roll**: 220px-wide append-only activity feed,
  the last 200 named events. Each row: timestamp (mono, faded ink) ·
  rubric verb (`PROCLAIMED`, `ADMITTED`, `SEALED`, `STUCK`,
  `EXILED`, etc.) in Cinzel small-caps · one-sentence summary in EB
  Garamond. Click → open the relevant folio in the drawer. No
  icons.
- **Bottom-left — the Stuck Tray**: a 32-px-tall fold collapsed by
  default; expands on hover into a list of stuck things, each with
  one **rubric verb-button** (`NUDGE` / `RESTART` / `FORCE-CLOSE`).
  Cinnabar is the only colour the Tray is allowed to use.
- **Empty state** (§1 of 08-v2-acceptance): the canvas is *empty*,
  not zero-counted. A single inline proclamation field — a torn-leaf
  insert in Cormorant Garamond 20px — sits vertically centred on
  parchment with the legend "*Speak, and the conclave begins.*" No
  first-run wizard, no "0 pods", no counters.

Glance is the *ambient page*. It is what the architect glances at
between other work.

---

## §3 — The Witness perspective

Two-column codex spread.

### Left column — Codex of Proclamations (≈ 60% width)

Vertically stacked, reverse-chronological. Each proclamation is a
real page:

- **Drop cap** in EB Garamond, two-line height, slightly inset, on
  the first letter of the proclamation body. **This is the only
  place in the app where a drop cap appears.** A drop cap means "a
  proclamation begins here."
- **Scribal numeral** in the gutter: `№ III` in Cormorant Garamond
  semibold.
- **Body** in EB Garamond 16px, justified.
- **Indented descendants** beneath each proclamation: every council,
  proposal, decision, image-swap that descended from it, each a
  one-line Cinzel small-caps verb + EB Garamond summary, each
  clickable to open in the right column.

Page breaks between proclamations are a 0.5-px faded-ink rule with a
**catchword** at the foot: the first word of the next proclamation,
in italic. Click it → smooth-scroll to that proclamation.

### Right column — Focused entity (≈ 40% width)

When you click a council in the left column, it fills here as a
**phylactery thread**. When you click a decision, it fills here as a
**Plate**. When you click a proposal, it fills here as a **Cartouche**
with its ballot strip. The right column never becomes empty: if
nothing is clicked, it shows the most-recently-active entity from the
current proclamation.

### Roll-replacement note

Witness's append-only stream is the same data as Glance's right rail
but **typeset differently** (chronological down the column, no
sparkline). One event, two surfaces, never duplicated as state.

---

## §4 — The Try perspective

A grid of **Plaques**, one per pod with a public HTTP service. Three
columns on wide screens, one on narrow.

Each plaque:
- Display-role at top in Cinzel small-caps, 14px.
- Hostname in mono 12px below (`rider-app.conclave.local`).
- A **64px endpoint sparkline** (Tufte-mode): requests-per-minute
  over the last hour, no axes, faded-ink stroke, normal-range as a
  4%-opacity wash band. The shape of the line is the data.
- An `Open` ink-link in compass-blue.
- Adopted-pod plaques carry an `image:tag` badge in mono at the
  foot.

No screenshots. No iframe thumbnails. The plaque is the affordance.

---

## §5 — The Direct perspective

Two stacked sections plus a persistent right drawer.

**Top — Charter Editor.** When a pod is selected (from a chooser
strip), its `charter.md` pre-loads in a serif diff view: the original
text as faded ink, edits in primary ink. One `Seal edit` wax-seal
button at the foot commits. The editor is EB Garamond 15px — the
charter is *prose the architect is writing in the agent's voice*,
not config.

**Bottom — DM thread.** Per-pod **phylactery thread** to send
direct messages (J7). Augustus's voice renders in gold ink with a
square frame; the agent's reply renders in iron-gall on the
scroll-shaped phylactery (see §6).

**Right drawer (always visible in this perspective)** — the selected
pod's **live agent transcript**. OpenLLMetry stream, monospaced
where it must be (raw model output), wrapped in EB Garamond
miniature plates when it renders a tool call. "*Thinking since
14:23*" stamp in italic faded-ink at top.

---

## §6 — Components

The ten components below are the entire surface vocabulary. New
surfaces compose these; no one-off card shapes.

1. **Bandeau** — the 40px top bar (§1). Cinzel wordmark, scribal
   numeral, perspective toggle, single health dot, Reset link.

2. **Cartouche** — the pod node on the Glance graph. Oval parchment
   frame, display-role in Cinzel small-caps, 12px **state pip** at
   top-right (verdigris running / cinnabar stuck / wash
   not-yet-spawned), 24×6 endpoint-traffic sparkline at the bottom.
   Dashed outline = placeholder pod; solid = admitted; crossed-through
   = exiled. The simulator pod has the gold hairline above-and-below.

3. **Phylactery** — speech-scroll message bubble for council
   messages, DMs, and any agent quotation. Sender heraldry is a
   16px deterministic two-letter monogram in Cinzel on a coloured
   field; the colour is **the pod's identity colour** and is the
   same monogram-fill used everywhere that pod is referenced. Body
   in EB Garamond. Augustus's voice uses gold ink and a *square*
   frame instead of a scroll.

4. **Plate** — the decision card. 18th-century scientific-journal
   plate: 1-px rule top + bottom, decision title in Cinzel,
   body in EB Garamond, "*Sealed V·MMXXVI*" footer in scribal
   numerals, **affected-pods row** below the body as a tight strip
   of pod monograms (each clickable). Placeholder decisions render
   `_council pending_` in italic faded-ink — the empty-tablet
   anti-pattern from v1 is now visually unmistakable.

5. **Roll entry** — one line of the Glance right-rail and Witness
   left-column digest. Timestamp · rubric verb · summary. No icons.

6. **Ballot Strip** — the senate cartouche's voting row. One pip per
   eligible voter (filled monogram if cast, hollow circle if
   pending, em-dash if abstain, wash-grey if sortition-undrawn).
   Strategy badge to the left in Cinzel small-caps:
   `MAJORITY` / `SUPERMAJORITY` / `CONSENSUS·OMNIUM` / `SORTITION`.
   Deadline countdown in mono.

7. **Folio drawer** — the right-side Radix `Sheet` that opens
   whenever a domain entity is clicked. Three vertical bands:
   identity → live transcript → neighbours. **Neighbours** is the
   navigable-graph affordance: each line is a clickable route to
   another folio. The drawer can be deep-stacked (one folio opening
   another) with a back chevron — same UX pattern as the v1
   PeekDrawer the rebuild replaces.

8. **Marginalia rail** — the 8px-wide gutter beside any long body
   (charter, decision body, council summary) where cross-references
   appear as small Cinzel scribal numerals. Click → open the
   referenced entity in the drawer. **This is where the manuscript
   skin earns its keep**: the §9 graph-of-everything is visible
   without cluttering the page.

9. **Wax seal** — primary action button. Cinnabar disc, 32px, with
   a single Cinzel letter embossed (`P` for `Proclaim`, `S` for
   `Seal edit`, `O` for `Open app`, `A`/`N` for `Aye`/`Nay`
   ballots). **Used sparingly** — at most one wax seal per surface.
   Secondary actions are ink-link text in compass-blue.

10. **Stuck Tray** (§2). The only component allowed to use cinnabar
    as a fill. Verb-buttons in Cinzel small-caps.

---

## §7 — Typography

Three faces. Restraint is the design.

- **EB Garamond** (body serif, OFL on Google Fonts).
  - 16px proclamation bodies / Witness column.
  - 15px charter editor.
  - 14px default body, council messages, decision bodies.
  - 13px in dense tables / Roll summaries.
  - Italic for proclamation text, scribal asides, deadlines,
    "*Thinking since…*" stamps.
  - **Drop cap** rule: appears **only** on proclamations, encoded
    as a single `<Proclamation>` React component. Not a CSS class
    anyone can apply.

- **Cinzel** (display small-caps, OFL on Google Fonts).
  - 11–14px only. **Never above 28px.** This is not a poster.
  - Used for: wordmark, perspective toggle, scribal numerals,
    decision titles, strategy badges, named-event rubrics in the
    Roll, Tray verb-buttons, pod display-roles on cartouches,
    rubric verbs on Plates.
  - **Never** for running body text.

- **JetBrains Mono** (mono, OFL).
  - 12px.
  - Used for: stable pod IDs, hostnames, image tags, timestamps in
    the Roll, OpenLLMetry transcripts, tool-call payloads, charter
    diff line numbers.
  - Never in chrome.

**Scribal numerals** (`№ III`, `V·MMXXVI`) appear only on
proclamation numerals and decision-sealed dates. Everywhere else,
Arabic numerals in mono. *If you can't tell what a number means at
a glance, the design fails.*

**Sizes — discontinuous, deliberate**:
12 marginalia · 13 Roll summary · 14 default body · 15 charter ·
16 proclamation body · 20 cartouche title · 28 page heading. **No
size between 28 and 56** — the scale is intentionally broken to
mark "this is a heading".

Line-height: 1.45 serif body · 1.2 Cinzel · 1.5 mono. 8-px spacing
scale (8/16/24/32/64), borrowed from Linear.

---

## §8 — Palette

Eight colours. Every hue carries a semantic.

| Hex | Name | Role |
|---|---|---|
| `#F4ECD8` | Parchment | Primary surface, page background |
| `#E8DCC0` | Vellum | Secondary surface — drawer fill, cartouche fill |
| `#1F1A14` | Iron-gall ink | Primary text, primary stroke |
| `#6B5E48` | Faded ink | Secondary text, hairline rules, axis-less sparkline |
| `#A48143` | Gold leaf | **Accent only** — proclamation numerals, sealed-decision rule, simulator's hairline, Augustus's DM ink. Never fill, never hover state. |
| `#3B5A3C` | Verdigris | Running / healthy state pip; OTel call-edge ink-bloom |
| `#7A1F1F` | Cinnabar | **The only red** — stuck, deadline-passed, exile vote, Stuck-Tray verb buttons, Reset confirmation |
| `#1F3D4A` | Compass blue | **The only blue** — clickable cross-references, ink-links. Nothing decorative is blue. |
| `#C8BFA5` | Wash | Disabled, sortition-undrawn pip, dashed-outline placeholders, sparkline normal-range band |

Nine colours total (counted wash separately — it is the disabled
shade). Dark mode is `#1A1714` board inverted to ink-on-board with
the same gold/verdigris/cinnabar/blue.

---

## §9 — Motion & decoration policy

**Allowed**:

- **OTel call-edge ink-bloom**: when a span lands, the edge strikes
  verdigris for 600 ms (`opacity 0 → 1 → 0.4`, no easing past the
  peak). One strike per call, no looping pulse. Satisfies acceptance
  W1 (live edges visible within 5 s).
- **Drawer slide**: Radix `Sheet` default — 220 ms ease-out, no
  spring.
- **New Minute typesets in**: 200 ms ink-bleed (`opacity 0 → 1`,
  no slide, no bounce, no fade-from-zero). Activity-feed appends use
  this.
- **Drop cap fades in** once on first render, then static forever.
- **Stuck-pod pip pulses cinnabar** at 1.5 Hz. The only periodic
  animation in the system.
- **Token stream**: characters append as they arrive; no caret
  blink, no typewriter sound.

**Forbidden**:

- Skeleton loaders that shimmer. Pending content uses italic
  faded-ink text ("*council pending*").
- Hover scale or shadow change on cards. Hover changes a rule stroke
  from `#6B5E48` to `#1F1A14`, period.
- Toast notifications. Notable events are Roll entries or Stuck-Tray
  rows.
- Avatars, emoji, icons-as-primary-content. The only ornament is
  the drop cap, rubric verbs, and scribal numerals.
- Confetti on decision-seal. Ever.
- Decoration that overlaps content. The gold rule above a sealed
  decision sits above it, not across it.
- Gradients. Drop shadows beyond a single 1-px hairline.
- Hover tooltips that hide information. Marginalia carries the
  supplementary text.

`prefers-reduced-motion` collapses every allowed motion to an 80 ms
opacity fade. Stuck-pip pulse becomes a static cinnabar fill.

---

## §10 — JTBD coverage

| Job | Surface that answers it |
|---|---|
| **J1 — proclaim** | Glance empty state torn-leaf insert; in steady state, a "P" wax seal on the Bandeau's right edge (Direct route handles long-form proclamations too). |
| **J2 — glance health** | Bandeau status dot + Glance graph state pips + Stuck Tray. 2-second read. |
| **J3 — catch up** | Witness Codex: every named event indented under its proclamation. Hourly activity digest renders as a folded "*overnight chapter*" group at the top. Sub-minute read because every entry is a one-sentence Roll line. |
| **J4 — watch one think** | Folio drawer band 2 (live OpenLLMetry stream), or Direct perspective's persistent right drawer when a pod is selected. Tool calls render as miniature Plates inline. |
| **J5 — witness meetings** | Witness right column renders a council thread as Phylacteries with sender monograms; closed councils show their summary in a framed Plate at the foot. |
| **J6 — try app** | Try perspective: one Plaque per public pod, hostname + endpoint sparkline + `Open` ink-link. |
| **J7 — course-correct** | Direct perspective: per-pod DM thread + Charter Editor. The persistent right drawer's live stream lets Augustus see the nudge land. |
| **J8 — imperial vote** | `/inbox` lists pending ballots as Plates with full rationale; selecting one opens its Cartouche with strategy / eligible / deadline / rationale and `A` / `N` / `—` wax seals. |
| **J9 — detect stuck** | Stuck Tray on Glance (cinnabar pulse on cartouche pip is the in-graph signal). One-tap Tray verb-buttons (`NUDGE` / `RESTART` / `FORCE·CLOSE`) hit Observer's command endpoints. |

---

## §11 — Build / data layer expectations

What the rebuild **keeps** from the existing Forum:

- `services/forum/src/api.ts` — fetcher prepends `/api`, types match observer reads.
- `services/forum/src/sse.ts` — `EventSource` connection to `/api/stream`.
- The build chain — Vite + Radix Themes + ReactFlow + Tailwind v4
  + SWR + react-markdown + remark-gfm. No new top-level deps unless
  this spec adds them.

What the rebuild **throws away**:

- `services/forum/src/App.tsx`, every file under `perspectives/`,
  the v1-shaped `components/` (Markdown.tsx and Linkified.tsx may
  be re-used verbatim — they are pure rendering primitives).
- The `.manuscript` class-scoped theme. Parchment is the default
  surface; there is no class-gated theme.
- Tailwind dark-mode chrome (`bg-slate-900` etc.) — replaced by §8
  palette tokens applied at the `:root` level.

---

## §12 — Acceptance for the rebuild PR(s)

- [ ] **spec/09 cited.** Each rebuild PR description names the
      §-numbers it implements. Improvisation beyond spec/09 is a
      kanban task, not a code change.
- [ ] **Parchment by default.** `localhost:5173` opens with the §8
      palette as the body background. No leftover slate-900 chrome.
- [ ] **All eight JTBD vignettes have an answer.** §10 maps every J
      to a surface; each row is traversable end-to-end on the
      running stack.
- [ ] **Click-through traverses through `/api`.** PR #91's
      relative-fetcher pattern stays; no absolute observer URLs.
- [ ] **Reset works from the Forum.** The Bandeau's Reset link
      issues `POST /commands {kind: ResetState}` (live since #93).
- [ ] **The three UX-research proposals stay in `runs/2026-05-uber/
      ux-research/`** alongside this spec so the rationale survives
      future passes.
