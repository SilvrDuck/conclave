# Charter — <pod_name>

## Purpose

One paragraph. What service does this pod own? What is the smallest end-to-end behavior that makes it valuable? Resist describing how — that is for the agent to design with peers.

## Skills

- Languages and frameworks the agent should be ready to use (e.g. Python 3.13 + FastAPI; TypeScript + Vite).
- Data shapes it must produce or consume (e.g. JSON over HTTP; Postgres rows; OTel spans).
- Operational competencies (e.g. write Dockerfile; structured logging; health endpoints).

Keep this list specific enough to load relevant skills from `shared/skills/` and `pods/<self>/skills/`, and short enough that the agent can read it in one breath.

## Initial endpoints planned

Headings only. Do not specify request/response shapes here — those emerge in the design conversation with peers.

- `GET /<resource>`
- `POST /<resource>`

If this pod is not an HTTP service (e.g. a worker), describe the equivalent contract surface (bus topics consumed, scheduled jobs).

## First-100-lines mandate

A bulleted list of the first ~100 lines of work the agent should produce after admission. Concrete enough that the agent has a starting move; loose enough that peer input can reshape it.

- Read `/conclave/primitives.md` and `/conclave/iusiurandum.md` (if founder).
- Open a chatroom with the proposer to confirm boundaries.
- Scaffold the service in `pods/<self>/workspace/` using the framework named above.
- Write the smallest endpoint that proves the runtime works; let the observer see it.
- Annotate the endpoint when `annotation_requested` fires.
- Update `pods/<self>/agenda.md` with one `doing` item and 1–2 `next` items.

## Persona (optional)

Link to a style overlay from `/conclave/personae/` if you want one applied. Personas affect voice and epistemic bias only — never capability or vote weight.

- `/conclave/personae/<Name>.md`
