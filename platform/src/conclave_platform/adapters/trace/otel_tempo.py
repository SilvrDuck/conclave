"""OTel-collector + Tempo TraceAdapter.

Pods export spans to the OTel collector at $OTEL_EXPORTER_OTLP_ENDPOINT; the
collector forwards to Tempo. This adapter polls Tempo's /api/search endpoint
for recent service-to-service spans and yields them as SpanEvents.

Alpha note: Pi itself doesn't currently emit OTel spans for outbound HTTP calls.
The observer covers most call-graph reconstruction by tapping the `coms` MCP's
bus traffic. This adapter is the second source of truth and goes live once
service code (the actual workspace apps) emits HTTP-server spans naturally.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import httpx
import structlog

from ...core import PodName
from ..base import AdapterError
from .base import SpanEvent

log = structlog.get_logger(__name__)

_POLL_INTERVAL_S = 5.0
_DEFAULT_TIMEOUT = 10.0


class OtelTempoTrace:
    def __init__(
        self,
        *,
        tempo_base: str = "http://tempo:3200",
        poll_interval: float = _POLL_INTERVAL_S,
        request_timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._base = tempo_base
        self._poll = poll_interval
        self._client = httpx.AsyncClient(base_url=tempo_base, timeout=request_timeout)
        self._stopped = False
        self._last_query_ts: float | None = None

    async def start(self) -> None:
        self._stopped = False

    async def stop(self) -> None:
        self._stopped = True
        await self._client.aclose()

    async def stream(self) -> AsyncIterator[SpanEvent]:
        while not self._stopped:
            try:
                async for span in self._search_recent():
                    yield span
            except (httpx.HTTPError, AdapterError) as exc:
                log.warning("tempo.poll_failed", exc=str(exc))
            await asyncio.sleep(self._poll)

    async def _search_recent(self) -> AsyncIterator[SpanEvent]:
        r = await self._client.get(
            "/api/search",
            params={"tags": "span.kind=client", "limit": 50},
        )
        if r.status_code != 200:
            raise AdapterError(f"tempo.search: {r.status_code}")
        for trace in r.json().get("traces", []):
            spans = _spans_from_trace(trace)
            for s in spans:
                yield s


def _spans_from_trace(trace: dict[str, Any]) -> list[SpanEvent]:
    out: list[SpanEvent] = []
    for s in trace.get("spans", []):
        attrs = {a["key"]: a["value"] for a in s.get("attributes", [])}
        caller = attrs.get("service.name")
        callee = attrs.get("peer.service") or attrs.get("net.peer.name")
        method = attrs.get("http.method")
        path = attrs.get("http.route") or attrs.get("http.target")
        status = attrs.get("http.status_code")
        if not (caller and callee and method and path):
            continue
        out.append(
            SpanEvent(
                caller=PodName(str(caller)),
                callee=PodName(str(callee)),
                method=str(method),
                path=str(path),
                status_code=int(status or 0),
                duration_ms=float(s.get("durationNanos", 0)) / 1e6,
                at=datetime.fromtimestamp(float(s.get("startTimeUnixNano", 0)) / 1e9),
            )
        )
    return out
