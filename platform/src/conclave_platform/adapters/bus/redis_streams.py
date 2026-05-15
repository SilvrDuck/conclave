"""Redis Streams BusAdapter — stub for alpha. See `nats_impl` for the wired path."""

from __future__ import annotations

from ..base import AdapterNotImplementedError
from .base import Handler, Subscription

_MSG = "Redis Streams bus not wired in alpha"


class RedisStreamsBus:
    def __init__(self, url: str) -> None:
        self._url = url

    async def connect(self) -> None:
        raise AdapterNotImplementedError(_MSG)

    async def close(self) -> None:
        raise AdapterNotImplementedError(_MSG)

    async def publish(
        self,
        topic: str,
        payload: bytes,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        raise AdapterNotImplementedError(_MSG)

    async def subscribe(self, topic: str, handler: Handler) -> Subscription:
        raise AdapterNotImplementedError(_MSG)

    async def request(self, topic: str, payload: bytes, *, timeout: float) -> bytes:
        raise AdapterNotImplementedError(_MSG)
