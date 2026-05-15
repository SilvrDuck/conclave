"""conclave-harness — the per-pod sidecar entry point.

Reads env vars:
  POD_NAME         — required
  BUS_URL          — nats://bus:4222 (default)
  OBSERVER_URL     — http://observer:8000
  WORKSPACE_ROOT   — /workspace (the bind-mounted monorepo)
  BRANCH           — main (or proto/<topic>)
  CHARTER_PATH     — pods/<pod>/charter.md (relative to workspace root)
  PI_SESSION_DIR   — /root/.pi/agent

Then wires the bus + observer + repo + Pi together and runs until stopped.
"""

from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path

import httpx
import structlog

from ..adapters.bus import InMemoryBus, NatsBus
from ..adapters.cli import PiCli
from ..adapters.repo import LocalGitRepo
from ..core import PodName
from .dual_writer import DualWriter
from .file_watcher import watch
from .inbox import InboxLoop

log = structlog.get_logger(__name__)


async def run() -> None:
    pod = PodName(os.environ["POD_NAME"])
    bus_url = os.environ.get("BUS_URL", "nats://bus:4222")
    observer_url = os.environ.get("OBSERVER_URL", "http://observer:8000")
    workspace = Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
    branch = os.environ.get("BRANCH", "main")
    charter_path = Path(
        os.environ.get("CHARTER_PATH", f"pods/{pod}/charter.md")
    )
    session_dir = Path(os.environ.get("PI_SESSION_DIR", "/root/.pi/agent"))
    pod_workspace = workspace / "pods" / pod

    bus = InMemoryBus() if bus_url.startswith("inmemory") else NatsBus(servers=bus_url)
    await bus.connect()
    observer = httpx.AsyncClient(base_url=observer_url, timeout=10.0)
    repo = LocalGitRepo(workdir=workspace)
    cli = PiCli()
    charter_full = (workspace / charter_path).read_text(encoding="utf-8")

    writer = DualWriter(
        pod=pod, workspace_root=workspace, branch=branch, repo=repo, observer=observer
    )
    inbox = InboxLoop(
        pod=pod,
        bus=bus,
        cli=cli,
        charter=charter_full,
        pod_workspace=pod_workspace,
        session_dir=session_dir,
        env={"POD_NAME": pod, **os.environ},
    )
    await inbox.start()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    endpoints_path = pod_workspace / "endpoints.md"
    agenda_path = pod_workspace / "agenda.md"

    tasks = [
        asyncio.create_task(
            watch(endpoints_path, writer.write_endpoints, stop=stop),
            name="watch.endpoints",
        ),
        asyncio.create_task(
            watch(agenda_path, writer.write_agenda, stop=stop), name="watch.agenda"
        ),
    ]

    log.info("harness.ready", pod=pod, workspace=str(workspace))
    await stop.wait()
    log.info("harness.shutdown", pod=pod)
    for t in tasks:
        t.cancel()
    await inbox.stop()
    await bus.close()
    await observer.aclose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
