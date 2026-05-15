"""Doc backend adapter — slot 5. Backs `decisions` MCP."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ...core import Adr, AdrId, PodName


@runtime_checkable
class DocsAdapter(Protocol):
    async def write_adr(
        self,
        *,
        title: str,
        body: str,
        affected_pods: list[PodName],
        proposal_id: str | None = None,
    ) -> AdrId: ...

    async def read(self, adr_id: AdrId) -> Adr | None: ...

    async def search(self, query: str, *, limit: int = 10) -> list[Adr]: ...

    async def list(self, *, pod: PodName | None = None, limit: int = 100) -> list[Adr]: ...
