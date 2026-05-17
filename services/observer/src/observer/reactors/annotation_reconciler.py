"""Periodic reconciler for un-annotated endpoints.

The AnnotationRequester reactor only fires on the FIRST EndpointObserved
for an endpoint. If that NATS publish failed (transient bus hiccup,
reactor crash), the prompt is lost — the pod never gets told to
annotate its endpoint.

This reactor sweeps observer.endpoints every 5 minutes for endpoints
that are:
  - still un-annotated, AND
  - first observed at least 5 minutes ago (so a normal new endpoint has
    time to land through the one-shot reactor first), AND
  - last observed in the last hour (no point waking pods about dead
    endpoints).

For each candidate it re-publishes RequestAnnotation to the owning
pod's inbox.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import asyncpg
from conclave_core import Bus

log = logging.getLogger("observer.reactor.annotation-reconciler")

RECONCILE_INTERVAL_S = 300  # 5 min — matches the SQL freshness gates


class AnnotationReconciler:
    def __init__(self, *, pool: asyncpg.Pool, bus: Bus) -> None:
        self._pool = pool
        self._bus = bus
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop(), name="annotation-reconciler")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=RECONCILE_INTERVAL_S
                )
            except TimeoutError:
                # Normal path — the wait timed out, time to sweep.
                pass
            else:
                # Stop was set — exit cleanly.
                return
            try:
                await self._sweep()
            except Exception:
                log.exception("annotation reconciler sweep failed")

    async def _sweep(self) -> int:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT pod_id, method, path
                     FROM observer.endpoints
                    WHERE annotation IS NULL
                      AND first_seen < now() - interval '5 minutes'
                      AND last_seen > now() - interval '1 hour'"""
            )
        if not rows:
            return 0
        for r in rows:
            body = json.dumps(
                {
                    "event_type": "RequestAnnotation",
                    "pod_id": r["pod_id"],
                    "method": r["method"],
                    "path": r["path"],
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                    "reconciled": True,
                }
            ).encode()
            try:
                await self._bus.nc.publish(
                    f"conclave.inbox.{r['pod_id']}", body
                )
            except Exception:
                log.exception(
                    "reconcile inbox publish to %s failed", r["pod_id"]
                )
        log.info(
            "annotation reconciler: re-poked %d un-annotated endpoint(s)",
            len(rows),
        )
        return len(rows)
