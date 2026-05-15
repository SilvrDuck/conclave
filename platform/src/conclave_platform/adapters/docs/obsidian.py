"""ObsidianVaultDocs — stub for alpha. See `github_issues` / `inmemory` for wired pairs."""

from __future__ import annotations

from pathlib import Path

from ...core import Adr, AdrId, PodName
from ..base import AdapterNotImplementedError

_MSG = "Obsidian vault docs not wired in alpha"


class ObsidianVaultDocs:
    def __init__(self, vault_path: Path) -> None:
        self._vault_path = vault_path

    async def write_adr(
        self,
        *,
        title: str,
        body: str,
        affected_pods: list[PodName],
        proposal_id: str | None = None,
    ) -> AdrId:
        raise AdapterNotImplementedError(_MSG)

    async def read(self, adr_id: AdrId) -> Adr | None:
        raise AdapterNotImplementedError(_MSG)

    async def search(self, query: str, *, limit: int = 10) -> list[Adr]:
        raise AdapterNotImplementedError(_MSG)

    async def list(self, *, pod: PodName | None = None, limit: int = 100) -> list[Adr]:
        raise AdapterNotImplementedError(_MSG)
