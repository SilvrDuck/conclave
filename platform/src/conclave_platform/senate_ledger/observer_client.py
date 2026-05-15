"""Thin HTTP client to the observer. Only the queries the senate needs."""

from __future__ import annotations

import httpx

from ..core import PodName

_DEFAULT_TIMEOUT = 10.0


class ObserverClient:
    def __init__(self, *, base_url: str, request_timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=request_timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def list_admitted_members(self) -> list[PodName]:
        r = await self._client.get("/state/members")
        r.raise_for_status()
        return [
            PodName(m["name"])
            for m in r.json().get("members", [])
            if m.get("status") == "admitted"
        ]

    async def callers_of(self, *, method: str, path: str) -> list[PodName]:
        r = await self._client.get("/state/callers", params={"method": method, "path": path})
        r.raise_for_status()
        return [PodName(p) for p in r.json().get("callers", [])]

    async def upsert_member(
        self, *, name: PodName, charter_path: str, status: str
    ) -> None:
        await self._client.post(
            "/ingest/member",
            json={"name": name, "charter_path": charter_path, "status": status},
        )
