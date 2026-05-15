"""SenateProxyDocs — DocsAdapter that delegates to senate-ledger's /adrs REST.

This is the standard wiring in compose: the senate-ledger owns the docs store
(InMemoryDocs in alpha, GitHubIssuesDocs in prod). Every other process — most
importantly mcp-decisions — reads through this proxy so there's exactly one
writer per ADR row.
"""

from __future__ import annotations

import httpx

from ...core import Adr, AdrId, PodName
from ..base import AdapterError

_DEFAULT_TIMEOUT = 15.0


class SenateProxyDocs:
    def __init__(self, *, senate_url: str, request_timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._client = httpx.AsyncClient(base_url=senate_url, timeout=request_timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def write_adr(
        self,
        *,
        title: str,
        body: str,
        affected_pods: list[PodName],
        proposal_id: str | None = None,
    ) -> AdrId:
        r = await self._client.post(
            "/adrs",
            json={
                "title": title,
                "body": body,
                "affected_pods": list(affected_pods),
                "proposal_id": proposal_id,
            },
        )
        if r.status_code not in (200, 201):
            raise AdapterError(f"senate.write_adr failed: {r.status_code} {r.text}")
        return AdrId(r.json()["adr_id"])

    async def read(self, adr_id: AdrId) -> Adr | None:
        r = await self._client.get(f"/adrs/{adr_id}")
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            raise AdapterError(f"senate.read_adr failed: {r.status_code} {r.text}")
        body = r.json()
        return None if body is None else Adr.model_validate(body)

    async def search(self, query: str, *, limit: int = 10) -> list[Adr]:
        r = await self._client.get("/adrs/search", params={"q": query, "limit": limit})
        if r.status_code != 200:
            raise AdapterError(f"senate.search_adrs failed: {r.status_code} {r.text}")
        return [Adr.model_validate(a) for a in r.json().get("adrs", [])]

    async def list(
        self,
        *,
        pod: PodName | None = None,
        limit: int = 100,
    ) -> list[Adr]:
        params: dict[str, str | int] = {"limit": limit}
        if pod is not None:
            params["pod"] = pod
        r = await self._client.get("/adrs", params=params)
        if r.status_code != 200:
            raise AdapterError(f"senate.list_adrs failed: {r.status_code} {r.text}")
        return [Adr.model_validate(a) for a in r.json().get("adrs", [])]
