# Proposal A: The Conclave Codex — a living, scriptorium-grade gospel of the swarm

The Forum reads as one continuously-illuminated codex. Every screen is a folio: a dense decorative border, a column of "scripture" (the live system data), miniatures (cards) inside the column, and marginalia (annotations, tickers, dissent) running down the gutter. Color carries role: **purple = senate**, **vermillion = decisions**, **gold = proclamations**, **lapis = councils/voices**, **ferrous green = pods/services**. Decoration never hides content; it is the chrome, never the signal.

---

### Information architecture

One application, one global frame ("the codex"), four routes — exactly the JTBD perspectives ([01-jtbd §"Four perspectives"](../../../spec/01-jtbd.md)), never the v1 backend-module tabs ([03 §UI / §L8](../../../spec/03-prototype-audit.md)):

- `/glance` — the **Atlas folio**: live system as one illuminated map.
- `/witness` — the **Annals folio**: stacked, scrollable chronicle of proclamations, councils, proposals, decisions.
- `/try` — the **Reliquary folio**: a launcher of the swarm's running apps.
- `/direct` — the **Scriptorium folio**: proclaim, DM, charter-edit, imperial ballot.

Crucially, every route shares one persistent **right-hand "drawer of neighbours"** — clicking any node, name, decision, message, or endpoint *anywhere* opens the same drawer ([07-c4 §C2.1, §C3](../../../spec/07-c4.md); the interconnection invariant of [01-jtbd](../../../spec/01-jtbd.md)). The drawer is a sub-folio itself: heraldry at top, neighbours-as-clickable-cards below. This is the navigable knowledge graph the vision demands ([00-vision §3](../../../spec/00-vision.md)).

A persistent left **rail of illuminated initials** marks the four routes — `A` (atlas), `N` (annals), `R` (reliquary), `S` (scriptorium) — each a versal letter, gilded when active, inked-flat when not. A top **bandeau** carries an `I` numeral for the current proclamation, a stuck-tray bell with crimson seal-count, and the Augustus inbox count rendered as ballot tabs (J8/J9).

The dominant frame is therefore: bandeau (top, slim) → rail of versal initials (left, slim) → main folio (centre, the route) → drawer of neighbours (right, expanding from icon-strip to half-page).

---

### Page-by-page layout

**`/glance` — Atlas folio.** The folio's text column is replaced by a **carpet page**: React Flow filling 60% of the centre, framed by a 32-px ornamental border. Pods render as **roundel nodes** — circular medallions whose ring colour encodes role (`green` code-pod, `bronze-with-rivets` adopted-pod), whose halo encodes runtime (`gold` running, `dim` not-yet-spawned, `vermillion` stopped — §10 R1, §7), whose centre carries the agent's display-role in insular majuscule. Edges = real OTel calls ([07 §Path D](../../../spec/07-c4.md)); animated by a slow gold-thread "draw" the second the span lands. **Marginalia gutter** (right of the graph, ~280 px, inside the border) carries the activity ticker as illuminated chapter-marks: `proclaimed`, `admitted`, `sealed`, `deployed`, `image-swapped`. Above the graph: a **glance band** of five badges — `proclamation age`, `pods active`, `pods stuck`, `last named event`, `simulator pulse` — each is a small cartouche (J2). Empty state ([§1](../../../spec/08-v2-acceptance.md)): the carpet page shows only the frame, the central oculus pulsing slowly, the legend "_The page is bare. Speak, and the swarm will copy your word._" with a single Radix `TextArea` for the first proclamation.

**`/witness` — Annals folio.** A two-column codex spread. Left column (~64ch): time-descending list of **named entries** — Proclamation cards (gold, with Roman numeral drop-cap), Council cards (lapis), Proposal cards (purple), Decision cards (vermillion). Right column: marginalia — agent-quote pull-outs lifted verbatim from the live agent traces (this is where personality lives — [00-vision §"The product"](../../../spec/00-vision.md); [08 §14 analyze](../../../spec/08-v2-acceptance.md)). Each entry expands inline into its own miniature: a proposal expands to its full **senate cartouche** (kind · summary · strategy · ballot strip · deadline countdown — §4, W4); a council expands to its **thread** (each message a phylactery, see below — W3); a decision expands to its full sealed body (vermillion plate). Filter chips at the top — *proclamations · councils · proposals · decisions · all*. Group dividers are illuminated initials of the day (`M`, `T`, `W` in versal).

**`/try` — Reliquary folio.** A grid of three to six **reliquary cards**, one per running pod with a public HTTP service (§8). Each card: heraldic shield with the pod's role-initial, hostname (`<pod>.conclave.local`) inscribed below in small caps, one-click "Open in new tab" rendered as a wax-seal button, a thumbnail iframe (lazy-loaded). Pods with no public face show a parchment-blank placeholder.

**`/direct` — Scriptorium folio.** Three nested workspaces, switched by a tabbed gilded ribbon:
1. **Proclaim** — a wide quill-and-parchment textarea (Cormorant Garamond, 20px), pre-prefixed with the next Roman numeral, a single seal-shaped submit button. Submitting plays a 600 ms gilding animation on the numeral.
2. **Direct messages** — pod chooser (versal roundels in a strip), then a phylactery thread with Augustus's voice in gold ink, the agent's in dark ink (J7).
3. **Charter** — pod chooser, then a Radix Tabs split: `current` (rendered illuminated markdown) / `edit` (Codemirror with same theme) / `diff` (shadcn diff viewer with red strike-throughs / green insertions in marginalia style). Pre-loads current text (§11). Commit is a "seal this revision" wax-seal button.

The fourth Forum write — **imperial ballot** (J8, §11) — lives as a banner that drops from the bandeau when an Augustus-eligible proposal opens, expanding inline to the proposal cartouche with `for / against / abstain` seal-buttons. No separate route.

---

### Dominant components

The personality vocabulary — every novel component carries a name the architect can use in PR review:

1. **Versal** — the illuminated initial. Used as route icons, proclamation numerals (I, II, …), day-dividers, drop-caps on every entry's first paragraph. Spans 3 lines. Letter colour from role palette.
2. **Cartouche** — the **proposal plate**. Purple-ground oval frame around: kind badge · summary · strategy chip · ballot strip · countdown. The single load-bearing senate component (W4, §4).
3. **Phylactery** — the speech-scroll message bubble. Used for council messages, DMs, agent-quote marginalia. Sender heraldry (small roundel) flush left, scroll-shaped body, time in marginal Roman numerals.
4. **Roundel** — the pod node on the graph. Circular, ringed, with display-role inside. Hover reveals neighbours-count badges (services, councils, decisions); click opens the drawer.
5. **Wax seal** — the primary action button. Vermillion disc with a versal letter pressed into it. Used for `Proclaim`, `Seal charter`, `Open app`, `Cast ballot`. Hovered = wax glistens (subtle filter).
6. **Plate** (or *Tablet*) — the **decision card**. Vermillion ground, gold border, decision title in display serif, body in body serif, "_sealed_" stamp diagonal across one corner when finalised. Placeholder plates render in cool grey ("_council pending_") to make the empty-tablet anti-pattern from v1 ([03 §Domain Clay → stone](../../../spec/03-prototype-audit.md)) visually unmistakable.
7. **Marginalia rail** — the right-of-content gutter. Carries the activity ticker (on `/glance`), the agent-quote pull-outs (on `/witness`), the neighbour drawer when open (everywhere).
8. **Carpet frame** — the 32-px ornamental border that wraps every folio. Subtle knotwork at the corners; nodes-in-the-frame light up when their pod has activity (a one-line ambient health gauge — J2).
9. **Stuck tray** — bell icon in the bandeau, drops a crimson list of blocked things (J9, §11). Each entry is a tiny phylactery with a single seal-button action.
10. **Drawer of neighbours** — right-edge panel; pinnable. Header is a versal roundel with the clicked entity's heraldry; body is groups of clickable neighbour-cards (services, councils, decisions, …). Implements the §9 invariant: every entity reachable in ≤2 clicks.

Where these map to libraries: Roundels and edges via **React Flow** custom nodes ([04 chain 1](../../../spec/04-wardley.md)); the drawer, dialog, tabs, dropdown via **Radix Themes**; the carpet/decorative borders and versals via small inline SVG components (no images, themeable); markdown rendering via **shadcn's `<Card>` shells** for plates and **MDX** for decision bodies.

---

### Typography

Three faces. Generous; no more.

- **Display (versals, proclamation numerals, route headings):** *UnifrakturMaguntia* — black-letter, dense, used at 64–120 px. Drops to 32 px for day-dividers. Reserved for ornament; never used for running text.
- **Editorial (drop-caps, headings inside cards, proposal summaries, charter rendering):** *Cormorant Garamond* — display weight 500 for headings (24–32 px), regular 400 for sub-heads (18 px). Set on the `text-balance: balance` body.
- **Body / data (everything readable, agent transcripts, endpoint tables, ticker rows):** *Inter* at 14–16 px. Inter is the load-bearing operational face — the codex aesthetic must never make endpoint paths or ballot counts hard to scan ([08 §11](../../../spec/08-v2-acceptance.md), [06 QA1](../../../spec/06-atam.md)). Code/hostnames in *JetBrains Mono* 13 px.

Drop-caps appear on the first paragraph of every Witness entry and on the proclamation body in `/direct`. They span 3 lines, are coloured by role, render via CSS `initial-letter` with a span-class fallback for letter-specific spacing ([Smashing on drop caps](https://www.smashingmagazine.com/2012/04/drop-caps-historical-use-and-current-best-practices/)).

---

### Palette

Parchment-on-warm-vellum ground; ink-on-vellum text; gold for the operator's word; role-accents for everything else.

| Hex | Name | Role |
|---|---|---|
| `#F4ECD8` | Vellum | Page background. Slightly warm. |
| `#E8DCBF` | Aged vellum | Card surfaces, gutters, drawer ground. |
| `#1E1A14` | Iron-gall ink | Body text, default ink. |
| `#6B5E3F` | Sepia | Secondary text, marginalia, timestamps. |
| `#C8A24B` | Gold leaf | Proclamations, Augustus's voice, active route, seal highlights. |
| `#5B2E91` | Senate purple | Proposals, ballots, strategy chips. |
| `#9E1B1B` | Vermillion | Decisions, sealed plates, primary actions, stuck warnings. |
| `#2A5F7A` | Lapis | Councils, messages, agent voices in phylacteries. |

A muted **ferrous green** (`#3F5A3A`) and a **bronze** (`#8A5A2B`) live as ring-colours on roundels (code-pod vs adopted-pod) — they read as material, not as content categories, and sit inside the eight above.

Dark mode: invert ground to a dim charcoal vellum (`#1B1813`) and pull all role-accents up 12% lightness. Gold becomes the only colour that *brightens*; it always reads as illumination.

---

### Motion & decoration policy

**Allowed.** Three motion verbs, no more:
- *Illumination*: gold flicker on a versal when its referent fires (a new proclamation, an admission). 600 ms, once.
- *Gilding*: a path-draw animation on a new graph edge or a closing seal. 400 ms.
- *Unscroll*: phylactery message appears with a 200 ms vertical-grow as it lands.

**Forbidden.** No parallax, no decoration that animates while idle, no "ambient" particle effects, no breathing borders. The carpet frame is static unless its embedded node has actual activity. Decoration never overlays content; marginalia lives *beside* the column, never *on* it. Agent transcripts, endpoint tables, and ballot strips render at full contrast in Inter — the manuscript chrome stops at the edge of every data block. If the architect ever says "I cannot tell what's happening" ([00-vision](../../../spec/00-vision.md)), the decoration loses. This is observability, not theatre — [03 §L5](../../../spec/03-prototype-audit.md).

Reduced-motion (`prefers-reduced-motion`): all three verbs collapse to a single 80 ms opacity fade.

---

### JTBD coverage

- **J1 (issue/refine direction)** — `/direct` Proclaim tab, single textarea, gold seal; submission populates the Witness annal and Atlas placeholder within 3 s (§2).
- **J2 (glance health)** — `/glance` top band of five cartouche badges and the carpet-frame node-lights; readable in <2 s.
- **J3 (catch up after away)** — `/witness` filtered to "named events only" + the marginalia rail of agent-quote pull-outs; the hourly Activity Digester ([07 §Reactors](../../../spec/07-c4.md)) materialises as a folded "_overnight chapter_" group at the top.
- **J4 (watch one agent think)** — click a roundel on Atlas → drawer opens → token-stream tab streams the live OpenLLMetry trace ([06 W2](../../../spec/06-atam.md)) in a phylactery sequence. "_Thinking since…_" stamp in sepia marginalia.
- **J5 (witness a meeting)** — Witness council card expands inline into a thread of phylacteries; on Atlas, participants get a temporary lapis edge while the council is open (§6).
- **J6 (try the app)** — `/try` Reliquary, one-click wax-seal opens the pod's hostname in a new tab (§8).
- **J7 (course-correct)** — `/direct` DM tab; pod chooser → phylactery thread; charter editor with pre-loaded diff view (§11).
- **J8 (vote when asked)** — bandeau imperial-ballot banner drops in, expands to the same Cartouche with three seal-buttons; never requires leaving the current route.
- **J9 (detect stuck)** — bandeau bell tray; each item a phylactery with a one-click action.

---

### Risks / trade-offs

1. **Aesthetic load is real.** UnifrakturMaguntia plus heavy borders plus three role-accent colours puts the codex one step from kitsch. The discipline is: chrome is decorative, every data zone is Inter at full contrast. If the line slips, this becomes a renaissance-faire site and J2's "<2 s sense of health" breaks. The remedy is to ship `/glance` first, measure recognition time on a real run, and prune the carpet frame if it costs more than 250 ms of cognitive overhead.

2. **Drop-caps and versals are fragile in long content.** Decision bodies, council transcripts, and charter renders can run to 2–10 paragraphs. Drop-caps must apply only to the *first* paragraph; a global `:first-letter` rule will gild every quote and code block by accident. This forces a small wrapper component and a discipline around what is "an entry" vs "the body of an entry." I judge the cost worth it; an architect who reads more will scan a real text column more easily than a flat-card grid.

3. **Black-letter accessibility.** UnifrakturMaguntia is unreadable below 32 px and screen-reader-hostile at any size. The mitigation is strict: versals are always purely decorative `<span aria-hidden="true">` with the semantic content in an adjacent Inter label. This works, but every new surface must remember the rule, or accessibility regresses silently — a real maintenance tax. The alternative (using a friendlier display serif) costs the aesthetic its teeth; I keep UnifrakturMaguntia and pay the tax.

Sources:
- [Book of Kells — Wikipedia](https://en.wikipedia.org/wiki/Book_of_Kells)
- [Très Riches Heures du Duc de Berry — Wikipedia](https://en.wikipedia.org/wiki/Tr%C3%A8s_Riches_Heures_du_Duc_de_Berry)
- [Lindisfarne Gospels — Wikipedia](https://en.wikipedia.org/wiki/Lindisfarne_Gospels)
- [Making the Divine, Observing the Tactile — Harvard Undergraduate Art History Journal](https://sites.harvard.edu/harvard-undergraduate-art-history-journal/making-the-divine-observing-the-tactile-the-carpet-pages-of-the-lindisfarne-gospels-as-an-aesthetic-of-paradox/)
- [Drop Caps: Historical Use And Current Best Practices With CSS — Smashing Magazine](https://www.smashingmagazine.com/2012/04/drop-caps-historical-use-and-current-best-practices/)
- [Cormorant Garamond — Google Fonts](https://fonts.google.com/specimen/Cormorant+Garamond)
- [Medieval UI on Dribbble](https://dribbble.com/tags/medieval-ui)
- [Top 21 Medieval Color Palette Ideas — Media.io](https://www.media.io/color-palette/medieval-color-palette.html)
