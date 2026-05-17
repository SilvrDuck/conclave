"""IdentifyCallers reactor — spec/02 Phase 6.

On every EndpointObserved, look up other pods that have called this
pod (cross-reference observer.calls.dst_pod). If there are existing
callers, the pod's surface just expanded *under them* — emit
EndpointContractChanged so mcp-coms can convene a council before the
change goes to a senate ballot. The council gives callers a chance
to negotiate the shape.

The "changed" qualifier in the spec is implementation-defined: at v2
alpha we don't capture request/response schemas, so any newly-observed
endpoint on a pod that already has callers counts as a contract
change. Endpoints on isolated pods (no callers yet) get the lighter
RequestAnnotation reactor instead, never a council.
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg
from conclave_core import Bus, EndpointContractChanged

log = logging.getLogger("observer.reactor.identify-callers")


class IdentifyCallers:
    def __init__(self, *, pool: asyncpg.Pool, bus: Bus) -> None:
        self._pool = pool
        self._bus = bus

    async def start(self) -> None:
        await self._bus.subscribe(
            "conclave.events.observer.EndpointObserved",
            self._on_endpoint_observed,
            durable="observer-identify-callers",
        )

    async def stop(self) -> None:
        # Subscription closes when the connection drains in main lifespan.
        return

    async def _on_endpoint_observed(self, data: dict[str, Any]) -> None:
        pod_id = data["pod_id"]
        method = data["method"]
        path = data["path"]
        # Callers = distinct src_pod values that have ever hit this
        # pod (any method/path). If empty, this is the first endpoint
        # on a pod that no one has called yet — nothing to identify.
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT DISTINCT src_pod
                     FROM observer.calls
                    WHERE dst_pod = $1 AND src_pod <> $1""",
                pod_id,
            )
        callers = [r["src_pod"] for r in rows]
        if not callers:
            return
        await self._bus.publish_event(
            EndpointContractChanged(
                pod_id=pod_id,
                method=method,
                path=path,
                callers=callers,
            ),
            "observer",
        )
        log.info(
            "EndpointContractChanged on %s %s %s — callers=%s",
            pod_id, method, path, callers,
        )
