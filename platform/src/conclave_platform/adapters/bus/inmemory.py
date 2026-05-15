"""In-memory bus — for tests and the founder-only quickstart path.

Real semantics: per-topic asyncio queues. At-least-once: each subscriber
gets its own queue. No persistence — process-local only.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import structlog

from .base import Handler, Subscription

log = structlog.get_logger(__name__)


@dataclass
class _InMemSub:
    topic: str
    handler: Handler
    task: asyncio.Task[None]
    queue: asyncio.Queue[bytes]

    async def unsubscribe(self) -> None:
        self.task.cancel()


class InMemoryBus:
    """Process-local pub/sub. Topics with `*` are not supported — exact match only."""

    def __init__(self) -> None:
        self._subs: dict[str, list[_InMemSub]] = defaultdict(list)
        self._responders: dict[str, Callable[[bytes], Awaitable[bytes]]] = {}
        self._closed = False

    async def connect(self) -> None:
        self._closed = False

    async def close(self) -> None:
        self._closed = True
        for subs in list(self._subs.values()):
            for s in subs:
                s.task.cancel()
        self._subs.clear()
        self._responders.clear()

    async def publish(
        self,
        topic: str,
        payload: bytes,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        if self._closed:
            raise RuntimeError("bus closed")
        for sub in list(self._subs.get(topic, [])):
            await sub.queue.put(payload)

    async def subscribe(self, topic: str, handler: Handler) -> Subscription:
        if self._closed:
            raise RuntimeError("bus closed")
        queue: asyncio.Queue[bytes] = asyncio.Queue()

        async def _drain() -> None:
            while True:
                payload = await queue.get()
                try:
                    await handler(payload)
                except Exception as exc:
                    log.warning("subscriber.error", topic=topic, exc=str(exc))

        task = asyncio.create_task(_drain(), name=f"inmem-sub-{topic}")
        sub = _InMemSub(topic=topic, handler=handler, task=task, queue=queue)
        self._subs[topic].append(sub)
        return sub

    def register_responder(
        self,
        topic: str,
        responder: Callable[[bytes], Awaitable[bytes]],
    ) -> None:
        """Used for request/reply. Topic gets exactly one responder."""
        self._responders[topic] = responder

    async def request(self, topic: str, payload: bytes, *, timeout: float) -> bytes:
        if self._closed:
            raise RuntimeError("bus closed")
        responder = self._responders.get(topic)
        if responder is None:
            raise TimeoutError(f"no responder for {topic}")
        return await asyncio.wait_for(responder(payload), timeout=timeout)
