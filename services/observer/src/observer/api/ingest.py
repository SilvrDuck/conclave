"""POST /ingest/otel — OTLP HTTP ingestion of traces from the collector.

We accept the full OTLP ExportTraceServiceRequest payload (JSON), translate
through the ACL into our `Call`/`Endpoint` domain types, and project into
observer schema. Tempo remains the source of truth; we only keep the most
recent 1-2 minutes of edge data for the live graph view.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from observer.otel_acl import translate_traces_request

log = logging.getLogger("observer.api.ingest")

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/otel")
async def ingest_otel(request: Request, body: dict[str, Any]) -> dict[str, int]:
    pool = request.app.state.observer.pool
    calls, endpoints = translate_traces_request(body)

    if not calls and not endpoints:
        return {"calls": 0, "endpoints": 0}

    async with pool.acquire() as conn:
        async with conn.transaction():
            for ep in endpoints:
                await conn.execute(
                    """INSERT INTO observer.endpoints(pod_id, method, path)
                       VALUES($1, $2, $3)
                       ON CONFLICT (pod_id, method, path) DO UPDATE
                           SET last_seen = now()""",
                    ep.pod_id,
                    ep.method,
                    ep.path,
                )
            for c in calls:
                await conn.execute(
                    """INSERT INTO observer.calls(src_pod, dst_pod, method, path,
                            status, latency_ms, observed_at)
                       VALUES($1, $2, $3, $4, $5, $6, $7)""",
                    c.src_pod,
                    c.dst_pod,
                    c.method,
                    c.path,
                    c.status,
                    c.latency_ms,
                    c.observed_at,
                )
    return {"calls": len(calls), "endpoints": len(endpoints)}
