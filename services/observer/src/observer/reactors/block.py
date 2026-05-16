"""BlockDetector — surfaces pods whose agent has been thinking too long.

Conservative heuristic: if a pod has an open `agent_turns` row with no
`ended_at`, started more than THRESHOLD ago, and is not already marked
stuck, set agent_state='stuck' and emit PodMarkedStuck.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import asyncpg
from conclave_core import Bus
from conclave_core.events import PodMarkedStuck

log = logging.getLogger("observer.reactor.block")

TICK = 30  # seconds
STUCK_AFTER = timedelta(minutes=5)


class BlockDetector:
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
        log.info("block detector started")
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception:
                log.exception("block tick failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=TICK)
            except TimeoutError:
                pass

    async def _tick(self) -> None:
        cutoff = datetime.now(UTC) - STUCK_AFTER
        async with self._pool.acquire() as conn:
            stuck = await conn.fetch(
                """SELECT DISTINCT t.pod_id
                     FROM observer.agent_turns t
                     JOIN observer.pod_state s ON s.pod_id = t.pod_id
                    WHERE t.ended_at IS NULL
                      AND t.started_at < $1
                      AND s.agent_state <> 'stuck'""",
                cutoff,
            )
            for r in stuck:
                await conn.execute(
                    "UPDATE observer.pod_state SET agent_state = 'stuck' WHERE pod_id = $1",
                    r["pod_id"],
                )
                event = PodMarkedStuck(pod_id=r["pod_id"], reason="agent_turn_too_long")
                await self._bus.publish_event(event, "observer")
                log.info("pod %s marked stuck (turn > %s)", r["pod_id"], STUCK_AFTER)
