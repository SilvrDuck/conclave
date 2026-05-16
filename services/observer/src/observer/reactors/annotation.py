"""RequestAnnotation reactor — spec/02 Phase 5.

On every EndpointObserved, check whether the endpoint is still
un-annotated and, if so, wake the owning pod with a one-shot inbox
message: "document your new endpoint."

The agent's bootstrap subscribes to conclave.inbox.<pod_id>; this
reactor just gives it something to receive. Published on core NATS
(not JetStream) because annotation requests are best-effort prompts,
not persisted state — a pod that boots later already knows its
endpoints via state.endpoints.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import asyncpg
from conclave_core import Bus

log = logging.getLogger("observer.reactor.annotation")


class AnnotationRequester:
    def __init__(self, *, pool: asyncpg.Pool, bus: Bus) -> None:
        self._pool = pool
        self._bus = bus

    async def start(self) -> None:
        await self._bus.subscribe(
            "conclave.events.observer.EndpointObserved",
            self._on_endpoint_observed,
            durable="observer-annotation-requester",
        )

    async def stop(self) -> None:
        # Subscription closes when the connection drains in main lifespan.
        return

    async def _on_endpoint_observed(self, data: dict[str, Any]) -> None:
        pod_id = data["pod_id"]
        method = data["method"]
        path = data["path"]
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT annotation FROM observer.endpoints
                    WHERE pod_id = $1 AND method = $2 AND path = $3""",
                pod_id,
                method,
                path,
            )
        if row is None or row["annotation"]:
            return
        body = json.dumps(
            {
                "event_type": "RequestAnnotation",
                "pod_id": pod_id,
                "method": method,
                "path": path,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
        ).encode()
        try:
            await self._bus.nc.publish(f"conclave.inbox.{pod_id}", body)
        except Exception:
            log.exception("RequestAnnotation publish to %s failed", pod_id)
            return
        log.info("RequestAnnotation: %s %s on %s", method, path, pod_id)
