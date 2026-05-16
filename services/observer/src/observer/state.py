"""Application-scoped state shared across handlers.

Built once at startup, torn down on shutdown. Handlers fetch via
`request.app.state.observer` rather than module globals.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import asyncpg
from conclave_core import Bus

from observer.config import Config


@dataclass
class AppState:
    config: Config
    pool: asyncpg.Pool
    bus: Bus
    event_broadcaster: EventBroadcaster
    bus_close: asyncio.Event


class EventBroadcaster:
    """Fan-in/fan-out hub for SSE clients.

    Anything published on the bus that we want the Forum to see is also
    pushed through this broadcaster; SSE handlers subscribe to a fresh
    queue with `subscribe()`.
    """

    def __init__(self) -> None:
        self._subs: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subs.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._subs.discard(q)

    async def publish(self, payload: str) -> None:
        async with self._lock:
            dead: list[asyncio.Queue[str]] = []
            for q in self._subs:
                try:
                    q.put_nowait(payload)
                except asyncio.QueueFull:
                    dead.append(q)
            for q in dead:
                self._subs.discard(q)
