# pods/_adopted_template — adopted-variant pod template

An **adopted pod** is one where the *service* is an off-the-shelf OSS
image (postgres:16, qbittorrent, meilisearch, …) and the *agent* runs
in a separate **sidecar** container with privileged access into the
main container (docker exec / the service's admin API / config-file
mounts on a shared volume).

Spec ref: [spec/02-event-storming.md §Phase 2](../../spec/02-event-storming.md),
[spec/05-ddd-contexts.md §C6](../../spec/05-ddd-contexts.md),
[spec/07-c4.md §Pod (adopted variant)](../../spec/07-c4.md).

## Layout

```
pods/<pod-id>/                  (copied from this template)
  charter.md                    agent system-prompt (Augustus may edit)
  sidecar/
    bootstrap.py                register_self(image_strategy=adopted) +
                                supervise the main container via docker exec
    requirements.txt            httpx + fastmcp + docker (python SDK)
    Dockerfile                  agent-only image
  compose.snippet.yaml          template snippet for compose, declaring
                                main + sidecar services and the shared
                                network / volume
```

## How the two containers cooperate

- **Main** (the OSS image) is the actual service. It runs as the image
  intends. No agent code inside.
- **Sidecar** mounts:
  - **NOT** the raw `/var/run/docker.sock`. Instead, a per-pod
    `tecnativa/docker-socket-proxy` sits in front of the socket with
    a `CONTAINER_NAME_FILTER=^pod-<role>$$` regex. The sidecar reaches
    docker via `DOCKER_HOST=tcp://pod-<role>-docker-proxy:2375`,
    which restricts the API surface to its own container only
    (CONTAINERS=1 + EXEC=1 + POST=1, everything else 0). Spec/07-c4
    + ATAM risk 153 + kanban #32 mandate this scoping before any
    adopted pod is given an agent.
  - A named volume shared with main where the agent can drop config
    files the OSS service rereads (postgres `pg_hba.conf` etc.).
  - Read-only `/pod/charter.md`.
- They share the conclave network. Traefik routes `<role>.conclave.local`
  → **main**, not the sidecar (the sidecar isn't an HTTP service).

## What the sidecar does

1. Wait for the main container's health to settle.
2. Call `register_self(image_strategy='adopted', main_image=<image>)`
   on mcp-pods.
3. Enter the agent loop (Claude Code). The agent:
   - Reads logs via `docker logs <main>`.
   - Edits config via files in the shared volume (or `docker cp`).
   - Restarts main with `docker restart` if config requires it.
   - Proposes admission, votes, etc. — same MCP surface as code pods.

Image-swap is a senate proposal kind; the orchestrator (mcp-pods) is
responsible for tearing down + bringing up the new main + sidecar pair
with the original pod_id preserved.

## Status (v2 alpha)

This template is the **shape** an adopted pod takes. The Claude Code
agent loop is feature-flagged off by default (`ENABLE_AGENT=false`),
mirroring the code-variant template. A concrete instance — adopted
postgres for the Spotify-clone catalog — lands in a follow-up branch
that wires the actual compose profile.
