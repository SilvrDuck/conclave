"""ActivityDigester — hourly digest rows for the J3 "catch up" view.

Once per hour, scans new entries in observer.activity, produces a one-line
summary per event-type, and writes a row into observer.digests keyed by
hour bucket. Marks each consumed activity row as digested.
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import UTC, datetime, timedelta

import asyncpg

log = logging.getLogger("observer.reactor.digester")

TICK = 600  # 10 minutes


class ActivityDigester:
    def __init__(self, *, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _run(self) -> None:
        log.info("activity digester started")
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception:
                log.exception("digester tick failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=TICK)
            except TimeoutError:
                pass

    async def _tick(self) -> None:
        # Bucket: the closed hour preceding now.
        now = datetime.now(UTC)
        hour = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, event_type FROM observer.activity
                     WHERE digested = FALSE AND occurred_at >= $1 AND occurred_at < $2""",
                hour,
                hour + timedelta(hours=1),
            )
            if not rows:
                return
            counts = Counter(r["event_type"] for r in rows)
            summary = ", ".join(f"{n} {t}" for t, n in counts.most_common())
            await conn.execute(
                """INSERT INTO observer.digests(hour_bucket, summary, item_count)
                   VALUES($1, $2, $3)
                   ON CONFLICT (hour_bucket) DO UPDATE
                       SET summary = EXCLUDED.summary, item_count = EXCLUDED.item_count""",
                hour,
                summary,
                len(rows),
            )
            await conn.execute(
                "UPDATE observer.activity SET digested = TRUE WHERE id = ANY($1)",
                [r["id"] for r in rows],
            )
        log.info("digest written for %s: %s", hour.isoformat(), summary)
