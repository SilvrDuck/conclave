"""Uvicorn entry — `uv run conclave-observer`."""

from __future__ import annotations

import asyncio
import os

import structlog
import uvicorn

from ..adapters.bus import NatsBus
from .app import create_app

log = structlog.get_logger(__name__)


def main() -> None:
    dsn = os.environ.get(
        "OBSERVER_DSN", "sqlite+aiosqlite:///./observer.db"
    )
    bus_url = os.environ.get("BUS_URL", "nats://bus:4222")
    host = os.environ.get("OBSERVER_HOST", "0.0.0.0")  # noqa: S104 — container, bound by compose
    port = int(os.environ.get("OBSERVER_PORT", "8000"))

    bus = NatsBus(servers=bus_url, name="observer")
    asyncio.run(bus.connect())

    log.info("observer.start", dsn=dsn, bus=bus_url, port=port)
    app = create_app(dsn=dsn, bus=bus)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
