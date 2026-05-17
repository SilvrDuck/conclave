# Proposal B: The Hansard of the Swarm — an Archive of Decisions

The Forum is a parliamentary record being typeset in real time. Every agent
turn, every ballot, every council message is **a numbered minute** entering
the printed record. The architect doesn't watch a stage; he reads the
transcript as it comes off the press. Personality lives in the testimony
itself — verbatim quoted utterance, dissenting note, scribal marginalia —
not in costume.

## Information architecture

A single dominant frame: **the open codex**. Two columns of running record,
generous margins for scribal annotation, foot-line catchwords joining the
"sheet" you're on to the next. Four top-level routes — these are the four
JTBD perspectives, never named after backend modules:

- `/` **Quire** — Glance. The codex's title page + current sheet. Pod graph
  rendered as an architectural plate facing the running record.
- `/record` **Record** — Witness. The chronological transcript. Sheets paginate
  by *epoch* (one proclamation = one epoch = one numbered book).
- `/chamber/:id` **Chamber** — A single council or senate proposal blown up to
  full-bleed. Speaker-by-speaker.
- `/folio/:pod` **Folio** — Direct. One pod's complete dossier: charter,
  current turn, endpoints, every minute it spoke in.
- `/apps` **Apps** — Try. A list of plates, each a running service's hostname.

The same record is reachable two ways: scroll the codex linearly, or click
any entity (catchword, marginal reference, cartouche) to jump to its folio.
The graph is **inside** the codex, never a separate "diagram tab."

## Page-by-page layout

**Quire (Glance).** Verso page: a typeset half-title — proclamation numeral
in scarlet (`PROCLAMATIO·II`), the proclamation's text set in italic body,
the placeholder decision printed beneath as a **cartouche** with status
`placeholder · council pending`. Recto page: an **architectural plate** —
React Flow graph of pods, rendered as if engraved (1-px black strokes,
parchment fill, no drop-shadows, no gradients), pods as small typeset
labels inside ruled rectangles, OTel edges as hairlines that pulse scarlet
on traffic. Foot of recto: a catchword joining to the next minute on the
Record page. No dashboard counters; absence is shown by silence.

**Record (Witness).** Two columns. Left column ≈ 60% width — the
**running transcript**: numbered minutes (`I.iv.027` = epoch · phase ·
minute) down a tight left rail, speaker rendered in `SMALL CAPS` (the
agent's display-role), utterance in roman body. Council messages, agent
turns, ballots, sealings — *all the same record*, distinguished only by
typography. Right column ≈ 40% — **marginal gloss** rail: scribal
annotations the platform writes ("agent renamed itself", "ballot 3/5",
"deadline in 02:14"), reactor notes, and Augustus's own pencilled DMs.
Top of page: running head (`THE ACTS · BOOK II · OF THE URBAN
TRANSPORT SCHEME`). Foot: catchword to the next sheet. The activity
ticker is *this page*, not a side panel.

**Chamber.** One council or one proposal blown up. A senate proposal is
typeset as a single **cartouche** at top — kind, summary, strategy badge
in rubric, deadline countdown in italic numerals, ballot strip rendered
as a row of typeset pips (`□` unballoted, `■` aye, `▣` nay, `◐` drawn-but-
not-yet, for sortition). Beneath the cartouche, the **debate**: every
council message in transcript form. When the chamber closes, the sealed
decision body is set immediately below as the next minute — same page,
no modal, no popover. Use Radix `ScrollArea` for the long debate; Radix
`HoverCard` for in-line speaker-bio glosses.

**Folio (Direct / pod drawer).** Opens as a Radix `Dialog` styled as a
**leaf inserted into the codex** (parchment overlay sliding from the
right, ribbon bookmark in scarlet). Top: the agent's display-role in
caps, stable-id in small italic underneath. Body sections, each a
typeset heading: `CHARTER` (markdown rendered with rubricated initial
capital, "Edit" affordance is an inkwell glyph), `PRESENT TURN` (live
token stream — see Motion below), `ENDPOINTS` (a small set table),
`MINUTES` (cross-references to every Record entry where this pod
spoke — each line is a clickable catchword to its minute), `CHAMBERS`
(councils this pod attended). DM affordance is a single line at the
foot: `*Address a missive to <pod-role>*`.

**Apps (Try).** A list of running services as **plates** — typeset
panels with the pod-role engraved at top, hostname as the caption
(`rider-app.conclave.local`), endpoints listed beneath, one
`open ↗` action set in scarlet italic. No screenshots, no thumbnails;
the plate is the affordance.

## Dominant components

1. **Cartouche** — the framed plate that carries a proposal, a decision,
   or a proclamation. Always has: numeral, title, strategy badge, body.
   Single re-usable React component; every cartouche is a link to its
   own folio.
2. **Minute** — one row of the transcript. Bears a hierarchical number
   (`II.iv.027`), a speaker in small caps, a body. All Record content is
   minutes. There is no second "card" type.
3. **Marginal gloss** — the right-margin scribal note. Reactor output,
   automatic annotations, augustal pencillings. *Smaller type, italic,
   muted ink.* Never primary content; always supplementary.
4. **Catchword** — single-word join at the foot of any sheet pointing to
   the first word of the next. In the UI: a clickable typeset cue that
   prefetches the next minute and acts as the "jump to neighbour"
   affordance. The interconnection invariant (J4/J5/J7/J8) is *expressed*
   as catchwords.
5. **Rubric** — short red phrase opening a section (`AYE.` `NAY.`
   `SEALED.` `EXILED.` `STUCK.`). Status is rubrication, not a badge.
6. **Initial capital** — the dropped, rubricated letter that begins each
   epoch and each sealed decision. Visual punctuation for the eye.
7. **Ballot strip** — typeset pip row. Sortition draws shown as `◐`
   pips before they vote; consensus_omnium shows every affected pod.
8. **Running head** — page-top line that names current book and folio.
   On a long Record scroll, the running head updates as you cross epoch
   boundaries.
9. **Errata leaf** — the "stuck tray" (J9). Rendered as a tipped-in errata
   sheet at the bottom of Quire: pods stuck, proposals past deadline,
   councils silent. Each row is a minute with a one-tap fix-rubric.
10. **Press mark** — tiny typographic mark indicating a live OTel call
    edge. A hairline that strikes scarlet for ~600 ms when traffic
    passes. The only motion permitted on the architectural plate.

## Typography

- **Body**: **EB Garamond** (Google Fonts, OFL). Open-source revival
  of Garamond — the workhorse roman that Aldine and Renaissance
  printers bequeathed; reads as "official record" without costume.
  16/24 base, 14/22 in marginal gloss.
- **Italic**: EB Garamond Italic — used for proclamation bodies, scribal
  glosses, deadlines, and any *spoken* aside. This is the Aldine inheritance:
  italic = voice in the margin, not emphasis.
- **Small caps**: EB Garamond SC — for speaker labels (`SIMULATOR`,
  `DISPATCH`, `AUGUSTUS`) and for `AYE`/`NAY`/`SEALED` rubrics.
- **Numerals (display)**: **Cormorant Garamond** semibold, lining numerals
  for proclamation numerals and minute indices (`II.iv.027`).
- **Mono**: **JetBrains Mono** — only inside agent token streams and
  endpoint tables. Never in chrome.
- **Sizes**: 12 marginal · 14 minute body · 16 ballot strip · 20 cartouche
  title · 28 running head · 56 proclamation numeral. No size between 28
  and 56 — the scale is deliberately discontinuous.

## Palette

| Hex | Role |
|---|---|
| `#F4EFE2` | **Parchment** — primary surface. Warm, slightly mottled by SVG noise. |
| `#FBF8EF` | **Raw paper** — drawers, dialogs, secondary surface. Lighter. |
| `#1A1410` | **Printer's ink** — body type. Not pure black; pure black reads digital. |
| `#5C4A36` | **Faded ink** — marginal glosses, secondary type, divider rules. |
| `#A1141C` | **Rubrication** — scarlet. Rubrics, initial capitals, live OTel pulse, deadline imminence. |
| `#1F3D4A` | **Compass blue** — the one cool accent. Used *exclusively* for clickable cross-references (catchwords, folio links). Nothing else is blue. |
| `#7A5E2E` | **Sealing wax** — sealed decision indicator, "admitted" pod node fill. |
| `#9A9486` | **Foxing** — disabled / placeholder state. Pods not yet admitted. |

Eight colours, none decorative. Every hue carries a semantic.

## Motion & decoration policy

**Permitted:**
- Token streams type out at the agent's real rate (the only "animation" on
  the Folio page).
- Live OTel call edges *strike* scarlet for ~600 ms on traffic, then
  fade to faded-ink. No looping pulse — one strike per call.
- New minutes **typeset in** with a 200 ms ink-bleed, then settle. No
  bounce, no slide, no fade-from-zero.
- Catchwords highlight on hover; cursor becomes the compass-blue link
  state.
- Drawer transitions: 180 ms ease-out, no spring.

**Forbidden:**
- Drop shadows beyond a single 1-px hairline.
- Gradients of any kind.
- Skeleton loaders. Empty states are *typeset empty* ("the record begins").
- Toast notifications. Everything notable is a minute or an errata row.
- Avatars, emoji, icons-as-primary-content. The only ornament is the
  occasional **initial capital** and the **rubrication**.
- Hover-tooltips that hide information. Marginalia carry the supplementary
  text instead.
- Decorative borders. Rules are 0.5 px faded-ink, period.

The rule: decoration **articulates** (Bodleian: "rubrication is articulation,
not decoration"). If a flourish doesn't help the eye locate something, it
is removed.

## JTBD coverage

- **J1 (proclaim).** Quire's recto top is a single field set as a torn-leaf
  insert; submission re-typesets the page into a numbered epigraph with a
  placeholder cartouche beneath, within 3 s.
- **J2 (glance health).** Quire renders the architectural plate plus the
  errata leaf. Stuck rubrics in scarlet are visible in 2 s.
- **J3 (catch up).** Record scrolls minute-by-minute, paginated by epoch.
  Activity digester output becomes a marginal-gloss summary at the foot of
  each closed book.
- **J4 (watch one pod think).** Folio's `PRESENT TURN` section is the live
  token stream, tool calls rubricated in line as they execute, "thinking
  since HH:MM" set as italic marginal gloss.
- **J5 (witness meeting).** Chamber route renders a council as the full
  debate transcript with closing summary printed as the next minute.
- **J6 (try app).** Apps lists running services as plates; one scarlet
  `open ↗` per plate.
- **J7 (course-correct).** Folio's DM line at the foot of each pod's
  dossier; the missive becomes a minute in the pod's `MINUTES` section
  immediately.
- **J8 (vote).** Imperial votes arrive as a cartouche on Quire with an
  `AYE / NAY / PASS` row in rubric. Click to ballot.

## Risks / trade-offs

1. **Density risks intimidation.** Two-column transcript with marginal
   glosses is *legible* but not glanceable in the way a dashboard tile is.
   J2 (glance) leans entirely on the Quire's architectural plate and the
   errata leaf — if either is off, glance breaks. Mitigation: the rubrics
   are scarlet for a reason.
2. **Serif body at 14 px requires good screens.** EB Garamond at the chosen
   sizes is gorgeous on retina, less so on a 1080p external monitor. The
   architect runs on retina; risk is bounded for the v2 audience.
3. **Personality is encoded as quotation, not as portrait.** No avatars,
   no character art. An agent's personality must come through in *what
   it says* and *how it dissents*. If the agent backends produce bland
   prose, the proposal under-delivers on the "see their personality"
   north-star. The Hansard direction *forces* the platform to lean on
   real transcript quality — which is correct, but it is a bet.
