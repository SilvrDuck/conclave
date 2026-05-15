"""Bus / transport adapter — slot 2.

Backs `coms` MCP and the harness inbox loop. Topic naming is the platform's
responsibility (e.g. `pod/<name>/inbox`, `system/<topic>`); the adapter just
pushes bytes around.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

Handler = Callable[[bytes], Awaitable[None]]


@runtime_checkable
class Subscription(Protocol):
    async def unsubscribe(self) -> None: ...


@runtime_checkable
class BusAdapter(Protocol):
    """Async pub/sub with at-least-once delivery for inbox topics."""

    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    async def publish(
        self,
        topic: str,
        payload: bytes,
        *,
        headers: dict[str, str] | None = None,
    ) -> None: ...

    async def subscribe(self, topic: str, handler: Handler) -> Subscription: ...

    async def request(self, topic: str, payload: bytes, *, timeout: float) -> bytes:
        """Request/reply on `topic`. Adapter MUST enforce timeout (no unbounded wait)."""
        ...
