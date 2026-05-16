"""NATS JetStream client. The bus *is* the chat; subjects are domain-typed.

Subject layout
--------------
  conclave.events.<context>.<EventType>   broadcast domain events
  conclave.commands.<context>.<Command>   commands routed to owning context
  conclave.inbox.<pod_id>                 per-pod fanout (consumers per pod)
  conclave.council.<council_id>           per-council append-only stream

Streams are durable. Consumers ack explicitly. The Observer reprojects
events into Postgres read models on first connect by replaying from a
durable consumer cursor.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from nats.aio.client import Client as NATSClient
from nats.js import JetStreamContext
from nats.js.api import RetentionPolicy, StreamConfig

from conclave_core.events import DomainEvent

EVENTS_STREAM = "CONCLAVE_EVENTS"
COMMANDS_STREAM = "CONCLAVE_COMMANDS"
COUNCIL_STREAM_PREFIX = "CONCLAVE_COUNCIL_"


def nats_url() -> str:
    return os.environ.get("NATS_URL", "nats://localhost:4222")


def event_subject(event: DomainEvent | type[DomainEvent], context: str) -> str:
    name = event.event_type if isinstance(event, DomainEvent) else event.__name__
    return f"conclave.events.{context}.{name}"


def command_subject(command_name: str, context: str) -> str:
    return f"conclave.commands.{context}.{command_name}"


def inbox_subject(pod_id: str) -> str:
    return f"conclave.inbox.{pod_id}"


def council_subject(council_id: str) -> str:
    return f"conclave.council.{council_id}"


class Bus:
    """Thin wrapper around NATS JetStream. One per process.

    Use as `async with Bus.connect() as bus: ...` so reconnection / cleanup
    is symmetric.
    """

    def __init__(self, nc: NATSClient, js: JetStreamContext) -> None:
        self._nc = nc
        self._js = js

    @classmethod
    @asynccontextmanager
    async def connect(cls, url: str | None = None) -> AsyncIterator[Bus]:
        nc = NATSClient()
        await nc.connect(servers=[url or nats_url()])
        js = nc.jetstream()
        bus = cls(nc, js)
        try:
            await bus.ensure_streams()
            yield bus
        finally:
            await nc.drain()

    async def ensure_streams(self) -> None:
        """Idempotently create the long-lived streams."""

        await self._ensure_stream(
            name=EVENTS_STREAM,
            subjects=["conclave.events.>"],
            retention=RetentionPolicy.LIMITS,
        )
        await self._ensure_stream(
            name=COMMANDS_STREAM,
            subjects=["conclave.commands.>"],
            retention=RetentionPolicy.WORK_QUEUE,
        )

    async def _ensure_stream(
        self, *, name: str, subjects: list[str], retention: RetentionPolicy
    ) -> None:
        cfg = StreamConfig(
            name=name,
            subjects=subjects,
            retention=retention,
            max_age=7 * 24 * 3600 * 10**9,  # 7 days in ns
        )
        try:
            await self._js.add_stream(cfg)
        except Exception:
            try:
                await self._js.update_stream(cfg)
            except Exception:
                pass

    # ─── publishing ───────────────────────────────────────────────────────

    async def publish_event(self, event: DomainEvent, context: str) -> None:
        subject = event_subject(event, context)
        payload = event.model_dump_json().encode()
        await self._js.publish(subject, payload)

    async def publish_command(
        self, command_name: str, payload: dict[str, Any], context: str
    ) -> None:
        subject = command_subject(command_name, context)
        await self._js.publish(subject, json.dumps(payload).encode())

    async def publish_raw(self, subject: str, payload: bytes) -> None:
        await self._js.publish(subject, payload)

    # ─── subscribing ──────────────────────────────────────────────────────

    async def subscribe(
        self,
        subject: str,
        handler: Callable[[dict[str, Any]], Awaitable[None]],
        *,
        durable: str | None = None,
        manual_ack: bool = True,
    ) -> None:
        """Push subscription. `handler` receives the parsed JSON payload."""

        async def cb(msg: Any) -> None:
            try:
                data = json.loads(msg.data.decode())
                await handler(data)
                if manual_ack:
                    await msg.ack()
            except Exception:
                if manual_ack:
                    await msg.nak()
                raise

        await self._js.subscribe(subject, cb=cb, durable=durable, manual_ack=manual_ack)

    @property
    def js(self) -> JetStreamContext:
        return self._js

    @property
    def nc(self) -> NATSClient:
        return self._nc
