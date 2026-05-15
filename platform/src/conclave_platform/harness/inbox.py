"""Inbox loop — subscribes to pod/<self>/inbox and delivers events to the CLI.

The harness owns the CLI lifecycle: it spawns Pi at startup with the charter,
then on every inbox event:

  • If Pi is awake, deliver the event over its stdin.
  • If Pi is asleep, resume with --session <id> and then deliver.

If Pi exits with a non-zero status we re-spawn after a backoff.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from ..adapters import BusAdapter, CliAdapter, CliSession
from ..core import EventEnvelope, PodName, pod_inbox_topic

log = structlog.get_logger(__name__)


@dataclass
class InboxLoop:
    pod: PodName
    bus: BusAdapter
    cli: CliAdapter
    charter: str
    pod_workspace: Path  # cwd for Pi
    session_dir: Path  # rw mount for --session-dir
    env: dict[str, str]
    startup_timeout: float = 60.0
    stop_timeout: float = 10.0
    session: CliSession | None = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _stop: asyncio.Event = field(default_factory=asyncio.Event)

    async def start(self) -> None:
        await self._ensure_alive()
        await self.bus.subscribe(pod_inbox_topic(self.pod), self._on_event)

    async def stop(self) -> None:
        self._stop.set()
        if self.session is not None:
            await self.cli.stop(self.session, timeout=self.stop_timeout)
            self.session = None

    async def _ensure_alive(self) -> None:
        async with self._lock:
            if self.session is not None and await self.cli.is_alive(self.session):
                return
            if self.session is None:
                self.session = await self.cli.start(
                    charter=self.charter,
                    cwd=self.pod_workspace,
                    session_dir=self.session_dir,
                    env=self.env,
                    startup_timeout=self.startup_timeout,
                )
                log.info("harness.pi.started", pod=self.pod, sid=self.session.session_id)
            else:
                self.session = await self.cli.resume(
                    session=self.session,
                    cwd=self.pod_workspace,
                    session_dir=self.session_dir,
                    env=self.env,
                    startup_timeout=self.startup_timeout,
                )
                log.info("harness.pi.resumed", pod=self.pod, sid=self.session.session_id)

    async def _on_event(self, payload: bytes) -> None:
        try:
            envelope = EventEnvelope.model_validate_json(payload)
        except Exception as exc:
            log.warning("harness.event.parse_failed", pod=self.pod, exc=str(exc))
            return
        await self._ensure_alive()
        if self.session is None:
            return
        try:
            await self.cli.deliver(self.session, envelope.event)
        except Exception as exc:
            log.warning("harness.deliver.failed", pod=self.pod, exc=str(exc))
            # Try one resume + retry.
            self.session = None
            await self._ensure_alive()
            if self.session is not None:
                await self.cli.deliver(self.session, envelope.event)


__all__ = ["InboxLoop"]
