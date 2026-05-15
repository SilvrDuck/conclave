"""In-memory DocsAdapter — tests and lightweight founder-only quickstart."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from ...core import Adr, AdrId, PodName, ProposalId, utc_now


class InMemoryDocs:
    def __init__(self) -> None:
        self._store: dict[AdrId, Adr] = {}
        self._lock = asyncio.Lock()
        self._counter = 0

    async def write_adr(
        self,
        *,
        title: str,
        body: str,
        affected_pods: list[PodName],
        proposal_id: str | None = None,
    ) -> AdrId:
        async with self._lock:
            self._counter += 1
            adr_id = AdrId(f"adr-{self._counter:04d}")
            self._store[adr_id] = Adr(
                id=adr_id,
                title=title,
                body=body,
                affected_pods=affected_pods,
                proposal_id=ProposalId(proposal_id) if proposal_id else None,
                created_at=utc_now(),
            )
            return adr_id

    async def read(self, adr_id: AdrId) -> Adr | None:
        return self._store.get(adr_id)

    async def search(self, query: str, *, limit: int = 10) -> list[Adr]:
        needle = query.lower()
        hits: Iterable[Adr] = (
            a for a in self._store.values() if needle in a.title.lower() or needle in a.body.lower()
        )
        return list(hits)[:limit]

    async def list(
        self,
        *,
        pod: PodName | None = None,
        limit: int = 100,
    ) -> list[Adr]:
        items = list(self._store.values())
        if pod is not None:
            items = [a for a in items if pod in a.affected_pods]
        items.sort(key=lambda a: a.created_at, reverse=True)
        return items[:limit]
