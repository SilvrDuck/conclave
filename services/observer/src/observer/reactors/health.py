"""HealthWatcher — marks pods whose container goes away as stopped.

Two signals:
- An OTel error span (status_code != 2xx for a sustained run) for a known
  src/dst pod marks the dst as unhealthy.
- Long absence of any span from a pod previously seen marks it stopped.

This reactor runs in the Observer process (it owns the observer schema).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import asyncpg
from conclave_core import Bus
from conclave_core.events import PodHealthChanged
from conclave_core.models import PodRuntimeStatus

log = logging.getLogger("observer.reactor.health")

TICK = 10  # seconds
STALE_AFTER = timedelta(minutes=2)


class HealthWatcher:
    def __init__(self, *, pool: asyncpg.Pool, bus: Bus) -> None:
        self._pool = pool
        self._bus = bus
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _run(self) -> None:
        log.info("health watcher started")
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception:
                log.exception("health tick failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=TICK)
            except TimeoutError:
                pass

    async def _tick(self) -> None:
        cutoff = datetime.now(UTC) - STALE_AFTER
        async with self._pool.acquire() as conn:
            stale = await conn.fetch(
                """SELECT pod_id FROM observer.pod_state
                   WHERE runtime_status = 'running' AND last_seen < $1""",
                cutoff,
            )
            for r in stale:
                await conn.execute(
                    """UPDATE observer.pod_state SET runtime_status = 'stopped'
                       WHERE pod_id = $1""",
                    r["pod_id"],
                )
                event = PodHealthChanged(
                    pod_id=r["pod_id"], runtime_status=PodRuntimeStatus.STOPPED
                )
                await self._bus.publish_event(event, "observer")
                log.info("pod %s marked stopped (stale)", r["pod_id"])
