# Runs — validation pass notes

Each subdirectory captures one **realize → analyze → nuke** pass of
the v2 acceptance loop (see [spec/08 §14](../spec/08-v2-acceptance.md#14--realize--analyze--nuke)).

Per-pass artifacts:

- `notes.md` — observations from the analyze phase, including which
  acceptance criteria limped, which agent turns surfaced
  personality (quoted verbatim), and which UI / platform gaps got
  filed as kanban tasks.
- `proclamation.txt` — the exact text Augustus typed in.
- `transcript-highlights.md` (optional) — selected council
  transcripts that illustrate dissent, debate, or charter rewrites.

Naming: `runs/<YYYY-MM>-<scenario-slug>/`.

| Pass | Scenario | Status |
|------|----------|--------|
| 1 | Spotify-clone (listen / lyrics / jam) | scrapped before §14 codified — no notes captured |
| 2 | Design Uber (rides / surge / simulator) | next |

When the analyze phase of a pass files zero new platform-gap tasks,
v2 is shipped — see spec/08 §14.
