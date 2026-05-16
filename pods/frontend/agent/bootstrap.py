"""Pod agent bootstrap.

What this script does (v2 alpha):
1. Reads its identity from env (POD_ID, DISPLAY_ROLE).
2. Calls `register_self` on the platform's `mcp-pods` server.
3. Reads charter.md and stores it for the agent loop.
4. If `ENABLE_AGENT=true`, launches the Claude Code CLI in workspace/
   with the MCP servers configured. Otherwise idles, awaiting either
   a manual `docker exec` or an env flip + restart.
5. Concurrently runs the workspace's service entrypoint with
   `opentelemetry-instrument` so HTTP traces flow into the collector.

The Claude Code subprocess part is intentionally minimal at v2 alpha —
it can be enabled when API credentials are available; until then the
pod is "present but quiet" on the conclave network, which is enough
for the platform to demonstrate admission flow and graph rendering.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

import httpx
from fastmcp.client import Client

log = logging.getLogger("pod.bootstrap")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


MCP_PODS_URL = os.environ.get("MCP_PODS_URL", "http://mcp-pods:8000/mcp")
WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/pod/workspace"))
SERVICE_CMD = os.environ.get("SERVICE_CMD", "uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
ENABLE_AGENT = os.environ.get("ENABLE_AGENT", "false").lower() == "true"


async def register() -> None:
    pod_id = os.environ.get("POD_ID")
    display_role = os.environ.get("DISPLAY_ROLE", pod_id or "unnamed")
    if not pod_id:
        log.error("POD_ID env var required")
        sys.exit(1)
    charter_path = "/pod/charter.md"
    async with Client(MCP_PODS_URL) as c:
        result = await c.call_tool(
            "register_self",
            {
                "pod_id": pod_id,
                "display_role": display_role,
                "image_strategy": "code",
                "charter_path": charter_path,
            },
        )
        log.info("registered: %s", result.data)


async def run_service() -> int:
    """Run the workspace service with otel auto-instrumentation. The
    process becomes a child we supervise; if it crashes we re-spawn."""
    if not WORKSPACE_DIR.exists():
        log.error("workspace dir %s missing", WORKSPACE_DIR)
        return 1
    while True:
        log.info("starting service: %s", SERVICE_CMD)
        proc = await asyncio.create_subprocess_shell(
            f"opentelemetry-instrument {SERVICE_CMD}",
            cwd=str(WORKSPACE_DIR),
        )
        rc = await proc.wait()
        log.warning("service exited rc=%s; restarting in 2s", rc)
        await asyncio.sleep(2)


async def agent_loop() -> None:
    """Placeholder agent loop. Real implementation will spawn
    Claude Code with the MCP servers configured."""
    log.info("agent loop active (placeholder; ENABLE_AGENT=true)")
    while True:
        # In a real run: invoke Claude Code per-turn here.
        await asyncio.sleep(60)


async def main() -> None:
    await register()

    tasks = [asyncio.create_task(run_service(), name="service")]
    if ENABLE_AGENT:
        tasks.append(asyncio.create_task(agent_loop(), name="agent"))
    else:
        log.info("agent disabled (ENABLE_AGENT=false); service-only")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    waiter = asyncio.create_task(stop.wait())
    done, _ = await asyncio.wait(
        {*tasks, waiter}, return_when=asyncio.FIRST_COMPLETED
    )
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    for t in done:
        if t is waiter:
            log.info("signal received; exiting")
            return
        if (exc := t.exception()):
            log.error("task %s failed: %s", t.get_name(), exc)


if __name__ == "__main__":
    # OTel resource attrs so traces are tagged with the pod.
    os.environ.setdefault("OTEL_SERVICE_NAME", os.environ.get("POD_ID", "unknown-pod"))
    os.environ.setdefault(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318"),
    )
    asyncio.run(main())
