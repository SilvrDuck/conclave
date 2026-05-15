"""NATS-backed BusAdapter — wired implementation for slot 2.

Plain core NATS (no JetStream) at alpha: inbox topics are wake signals,
durability lives in the observer's Postgres and the monorepo. Reconnect is
on; drain on close. Every request enforces the caller's timeout.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import nats
import structlog
from nats.aio.msg import Msg as NatsMsg
from nats.errors import TimeoutError as NatsTimeoutError

if TYPE_CHECKING:
    from nats.aio.client import Client as NatsClient
    from nats.aio.subscription import Subscription as NatsSubscription

from .base import Handler, Subscription

log = structlog.get_logger(__name__)


@dataclass
class _NatsSub:
    sub: NatsSubscription

    async def unsubscribe(self) -> None:
        await self.sub.unsubscribe()


class NatsBus:
    def __init__(self, servers: str | list[str], *, name: str = "conclave") -> None:
        self._servers = servers
        self._name = name
        self._nc: NatsClient | None = None

    async def connect(self) -> None:
        async def _err(e: Exception) -> None:
            log.warning("nats.error", error=str(e))

        async def _disc() -> None:
            log.warning("nats.disconnected")

        async def _rec() -> None:
            log.info("nats.reconnected")

        self._nc = await nats.connect(
            servers=self._servers,
            name=self._name,
            error_cb=_err,
            disconnected_cb=_disc,
            reconnected_cb=_rec,
            max_reconnect_attempts=-1,
            reconnect_time_wait=2,
        )

    async def close(self) -> None:
        if self._nc is not None:
            await self._nc.drain()
            self._nc = None

    @property
    def _client(self) -> NatsClient:
        if self._nc is None:
            raise RuntimeError("bus not connected; call connect() first")
        return self._nc

    async def publish(
        self,
        topic: str,
        payload: bytes,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        await self._client.publish(topic, payload, headers=headers)

    async def subscribe(self, topic: str, handler: Handler) -> Subscription:
        async def _wrap(msg: NatsMsg) -> None:
            try:
                await handler(msg.data)
            except Exception as exc:
                log.warning("nats.handler.error", topic=topic, exc=str(exc))

        sub = await self._client.subscribe(topic, cb=_wrap)
        return _NatsSub(sub=sub)

    async def request(self, topic: str, payload: bytes, *, timeout: float) -> bytes:
        try:
            msg = await self._client.request(topic, payload, timeout=timeout)
        except NatsTimeoutError as e:
            raise TimeoutError(f"NATS request {topic} timed out") from e
        return bytes(msg.data)
