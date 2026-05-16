"""Adopted-pod sidecar bootstrap.

Differences from the code-variant bootstrap:
- No workspace process to supervise. The main container is owned by
  Docker; we observe + manage it via the docker socket.
- Registers with `image_strategy=adopted` + `main_image=<image>`.
- Waits for the main container to report a healthy state before
  registering, so the platform doesn't see a pod whose service isn't up.
- The agent loop (when enabled) is the only Python-async work; the
  service runs in the peer container, not as our child.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys

import docker
from docker.errors import NotFound
from fastmcp.client import Client

log = logging.getLogger("pod.sidecar")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


MCP_PODS_URL = os.environ.get("MCP_PODS_URL", "http://mcp-pods:8000/mcp")
MCP_PODS_TIMEOUT = float(os.environ.get("MCP_PODS_TIMEOUT", "10"))
MAIN_CONTAINER = os.environ.get("MAIN_CONTAINER")  # set in compose
MAIN_IMAGE = os.environ.get("MAIN_IMAGE", "unknown")
WAIT_FOR_MAIN_S = float(os.environ.get("WAIT_FOR_MAIN_S", "60"))
ENABLE_AGENT = os.environ.get("ENABLE_AGENT", "false").lower() == "true"


async def wait_for_main_healthy() -> None:
    """Poll docker for the main container's running state. Caps at
    WAIT_FOR_MAIN_S so a missing main fails fast."""
    if not MAIN_CONTAINER:
        log.error("MAIN_CONTAINER env required for adopted-pod sidecar")
        sys.exit(1)
    client = docker.from_env()
    deadline = asyncio.get_event_loop().time() + WAIT_FOR_MAIN_S
    while asyncio.get_event_loop().time() < deadline:
        try:
            c = client.containers.get(MAIN_CONTAINER)
        except NotFound:
            log.info("waiting for main container %s …", MAIN_CONTAINER)
            await asyncio.sleep(1)
            continue
        state = (c.attrs.get("State") or {})
        running = state.get("Running", False)
        health = (state.get("Health") or {}).get("Status")
        if running and (health in (None, "healthy")):
            log.info("main %s up (health=%s)", MAIN_CONTAINER, health)
            return
        log.info("main %s state=%s health=%s", MAIN_CONTAINER, state.get("Status"), health)
        await asyncio.sleep(1)
    log.error("main %s did not become healthy in %ss", MAIN_CONTAINER, WAIT_FOR_MAIN_S)
    sys.exit(1)


async def register() -> None:
    pod_id = os.environ.get("POD_ID")
    display_role = os.environ.get("DISPLAY_ROLE", pod_id or "unnamed")
    if not pod_id:
        log.error("POD_ID env var required")
        sys.exit(1)
    async with Client(MCP_PODS_URL, timeout=MCP_PODS_TIMEOUT) as c:
        result = await c.call_tool(
            "register_self",
            {
                "pod_id": pod_id,
                "display_role": display_role,
                "image_strategy": "adopted",
                "main_image": MAIN_IMAGE,
                "charter_path": "/pod/charter.md",
            },
        )
        log.info("registered: %s", result.data)


async def agent_loop() -> None:
    """Placeholder. Real loop will spawn Claude Code with the MCP
    servers + a docker-exec tool wrapper so the agent can manage the
    main container."""
    log.info("agent loop active (placeholder; ENABLE_AGENT=true)")
    while True:
        await asyncio.sleep(60)


async def main() -> None:
    await wait_for_main_healthy()
    await register()

    if not ENABLE_AGENT:
        log.info("agent disabled (ENABLE_AGENT=false); sidecar idle")
    else:
        asyncio.create_task(agent_loop(), name="agent")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()
    log.info("signal received; exiting")


if __name__ == "__main__":
    os.environ.setdefault("OTEL_SERVICE_NAME", os.environ.get("POD_ID", "unknown-pod-sidecar"))
    os.environ.setdefault(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318"),
    )
    asyncio.run(main())
