"""POST /ingest/otel — OTLP HTTP ingestion of traces from the collector.

We accept the full OTLP ExportTraceServiceRequest payload (JSON), translate
through the ACL into our `Call`/`Endpoint` domain types, and project into
observer schema. Tempo remains the source of truth; we only keep the most
recent 1-2 minutes of edge data for the live graph view.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from observer.otel_acl import translate_traces_request

log = logging.getLogger("observer.api.ingest")

router = APIRouter(prefix="/ingest", tags=["ingest"])


# OTel collector's otlphttp exporter appends `/v1/traces` to the endpoint
# base, so we register that path too. The legacy `/ingest/otel` POST stays
# for direct curl tests. We accept raw bytes (the collector may send with
# `application/x-protobuf` or `application/json` and FastAPI's automatic
# body-parsing was tripping on the protobuf payloads with a 400).
@router.post("/otel")
@router.post("/otel/v1/traces")
async def ingest_otel(request: Request) -> dict[str, int]:
    raw = await request.body()
    content_type = request.headers.get("content-type", "")
    if "json" not in content_type:
        # Most likely OTLP/protobuf. We don't parse protobuf at v2 alpha
        # (Tempo is the source of truth). Ack so the collector doesn't
        # back-off; return a no-op.
        return {"calls": 0, "endpoints": 0}
    try:
        body: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"invalid JSON: {e}") from e

    pool = request.app.state.observer.pool
    calls, endpoints = translate_traces_request(body)

    if not calls and not endpoints:
        return {"calls": 0, "endpoints": 0}

    seen_pods: set[str] = set()
    async with pool.acquire() as conn:
        async with conn.transaction():
            for ep in endpoints:
                seen_pods.add(ep.pod_id)
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
                seen_pods.add(c.src_pod)
                seen_pods.add(c.dst_pod)
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
            # Refresh pod_state.last_seen for every pod that emitted a span.
            # Without this, the HealthWatcher's staleness scan would flip every
            # pod 'stopped' while it's actively serving traffic. Also flip a
            # 'stopped' pod back to 'running' on activity returning.
            for pod_id in seen_pods:
                await conn.execute(
                    """UPDATE observer.pod_state
                          SET last_seen = now(),
                              runtime_status = CASE
                                  WHEN runtime_status = 'stopped' THEN 'running'
                                  ELSE runtime_status
                              END
                        WHERE pod_id = $1""",
                    pod_id,
                )
    return {"calls": len(calls), "endpoints": len(endpoints)}
