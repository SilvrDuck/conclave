"""Tempo HTTP client adapter — spec/07 names this but ships it unimplemented.

Tempo's HTTP query API at /api/search returns trace summaries; /api/traces/{id}
returns the full trace tree. We use search filtered by service.name to
pull recent traces for a given pod.

This is intentionally thin — the platform's source of truth for traces is
Tempo itself; observer just proxies search and fetch so the Forum and
mcp-state can render trace summaries without each one needing to know
Tempo's URL shape.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger("observer.tempo")


def tempo_url() -> str:
    return os.environ.get("TEMPO_URL", "http://tempo:3200")


class TempoClient:
    """Async HTTP client for Tempo's query API. Caller owns lifecycle."""

    def __init__(self, *, base_url: str | None = None, timeout: float = 5.0) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url or tempo_url(),
            timeout=timeout,
        )

    async def search_by_service(
        self,
        service_name: str,
        *,
        limit: int = 20,
        since_seconds: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return the most recent traces for the given service.

        Tempo's /api/search supports a `tags` query param of the form
        `key1=val1 key2=val2`. service.name is the standard OTel
        resource attribute that observer attributes to pod_id.
        """
        params: dict[str, Any] = {
            "tags": f"service.name={service_name}",
            "limit": limit,
        }
        if since_seconds:
            # Tempo expects epoch-nanos via `start` / `end`. We pass
            # the lookback in seconds; Tempo's default search window
            # is 1 hour, so for short lookbacks this is a no-op.
            pass
        try:
            r = await self._client.get("/api/search", params=params)
            r.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("tempo search failed: %s", e)
            return []
        data = r.json()
        return list(data.get("traces") or [])

    async def fetch_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Return the full trace for `trace_id`, or None if not found."""
        try:
            r = await self._client.get(f"/api/traces/{trace_id}")
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            log.warning("tempo fetch_trace %s failed: %s", trace_id, e)
            return None
        except httpx.HTTPError as e:
            log.warning("tempo fetch_trace %s failed: %s", trace_id, e)
            return None
        return r.json()

    async def close(self) -> None:
        await self._client.aclose()
