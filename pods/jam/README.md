# pods/_template — code-variant pod template

Copy this directory to `pods/<pod-id>/` when spinning up a new code pod.
A code pod = one container holding both:
- the **agent** (Claude Code CLI subprocess driving the workspace), and
- the **service** code the agent is writing (its `workspace/`).

Adopted pods (`pods/_adopted_template/`) use a different shape: main OSS
image + sidecar.

## Layout

```
pods/<pod-id>/
  charter.md           markdown system-prompt the agent reads each wake
  agent/               agent runtime (this dir is platform-managed, NOT
                       part of the workspace)
    bootstrap.py       starts: register with mcp-pods, wakes Claude Code
    requirements.txt
  workspace/           the agent's project root — where they write code
    main.py            (placeholder; real agent will rewrite)
  Dockerfile           multi-stage: agent layer + workspace layer
```

`charter.md` is the only file Augustus expects to edit through the Forum.
The rest of the pod's contents are agent-authored.

## What the agent does on boot

1. `register_self(pod_id, display_role, image_strategy=code)` on
   mcp-pods. The pod_id is the directory name.
2. Read `charter.md`.
3. Open a Claude Code session over the bundled MCP servers
   (`senate`, `coms`, `decisions`, `state`, `pods`), with the charter as
   the system prompt prefix.
4. Loop: receive proclamations + DMs from its inbox, plan, edit the
   `workspace/`, build, propose admissions or contract changes, vote.
5. Restart the workspace process on file change (`uvicorn --reload`).

## OTel

Auto-instrumentation is enabled by `opentelemetry-instrument` in the
service entrypoint. The OTel collector at `otel-collector:4318` is
shared across the conclave network — each pod's spans flow there.

## Status (v2 alpha)

The bootstrap **registers** the pod and starts the workspace's
placeholder server. The Claude Code agent loop itself is gated behind
`ENABLE_AGENT=true` env (off by default) so the platform can come up
without burning API credit. See kanban/tasks for ongoing work.
