"""conclave-mcp-coms — runs the coms MCP over streamable HTTP on PORT (default 8002)."""

from __future__ import annotations

import asyncio
import os

import httpx
import structlog

from ...adapters.bus import InMemoryBus, NatsBus
from .server import ComsDeps, build_mcp

log = structlog.get_logger(__name__)


def main() -> None:
    bus_url = os.environ.get("BUS_URL", "nats://bus:4222")
    observer_url = os.environ.get("OBSERVER_URL", "http://observer:8000")
    port = int(os.environ.get("PORT", "8002"))
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104

    bus: InMemoryBus | NatsBus = (
        InMemoryBus() if bus_url.startswith("inmemory") else NatsBus(servers=bus_url)
    )
    observer = httpx.AsyncClient(base_url=observer_url, timeout=10.0)

    async def _setup() -> None:
        await bus.connect()

    asyncio.get_event_loop().run_until_complete(_setup())

    deps = ComsDeps(bus=bus, observer=observer)
    mcp = build_mcp(deps)
    log.info("mcp-coms.start", port=port, bus=bus_url, observer=observer_url)
    mcp.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    main()
