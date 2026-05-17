"""HealthWatcher — span-staleness becomes agent_state, not runtime_status.

Pre-G21 (pass-2 finding): this reactor used OTel-span staleness to flip
`runtime_status` from `running` to `stopped`. The signal is wrong — a
quiet agent emits no spans, but the container is alive. We were marking
live containers as stopped after 2 min of agent silence.

Post-G21 split:
- **runtime_status** flips only on real container death (Docker events
  via mcp-pods — kanban #24). HealthWatcher leaves it alone.
- **agent_state** flips to `idle` when no spans land for STALE_AFTER.
  When activity resumes the ObservationService projection flips it
  back to `thinking` naturally.

Spans coming and going are normal in a long-running pod; treating
their pause as a health signal is wrong. Agent-state staleness is the
honest interpretation.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import asyncpg
from conclave_core import Bus
from conclave_core.events import PodHealthChanged
from conclave_core.models import AgentState

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
                   WHERE runtime_status = 'running'
                     AND agent_state = 'thinking'
                     AND last_seen < $1""",
                cutoff,
            )
            for r in stale:
                await conn.execute(
                    """UPDATE observer.pod_state SET agent_state = 'idle'
                       WHERE pod_id = $1
                         AND agent_state = 'thinking'""",
                    r["pod_id"],
                )
                event = PodHealthChanged(
                    pod_id=r["pod_id"], agent_state=AgentState.IDLE
                )
                await self._bus.publish_event(event, "observer")
                log.info("pod %s agent_state → idle (no spans for >2m)", r["pod_id"])
