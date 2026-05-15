"""Dual-write: filesystem (git commit) + observer ingest.

The harness watches `pods/<self>/endpoints.md` and `pods/<self>/agenda.md`. On
change it parses the file and pushes to the observer; the file itself is
already on disk inside the bind-mounted monorepo, so committing it goes
through RepoAdapter.write_file (no rewrite, just `git add . && commit`).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import httpx
import structlog

from ..adapters import RepoAdapter
from ..core import PodName
from .agenda_parser import parse_agenda
from .endpoints_parser import parse_endpoints

log = structlog.get_logger(__name__)

_DEFAULT_TIMEOUT = 10.0


@dataclass
class DualWriter:
    pod: PodName
    workspace_root: Path  # absolute path of the bind-mounted monorepo
    branch: str
    repo: RepoAdapter
    observer: httpx.AsyncClient
    request_timeout: float = _DEFAULT_TIMEOUT
    _lock: asyncio.Lock = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._lock = asyncio.Lock()

    @property
    def endpoints_path(self) -> Path:
        return self.workspace_root / "pods" / self.pod / "endpoints.md"

    @property
    def agenda_path(self) -> Path:
        return self.workspace_root / "pods" / self.pod / "agenda.md"

    async def write_endpoints(self, content: str, *, message: str | None = None) -> None:
        async with self._lock:
            await self.repo.ensure_branch(self.branch)
            await self.repo.write_file(
                f"pods/{self.pod}/endpoints.md",
                content,
                message=message or f"docs({self.pod}): update endpoints.md",
                branch=self.branch,
            )
            for entry in parse_endpoints(content):
                await self.observer.post(
                    "/ingest/endpoint",
                    json={
                        "pod": self.pod,
                        "method": entry.method,
                        "path": entry.path,
                        "annotation": entry.annotation or None,
                    },
                )

    async def write_agenda(self, content: str, *, message: str | None = None) -> None:
        async with self._lock:
            await self.repo.ensure_branch(self.branch)
            await self.repo.write_file(
                f"pods/{self.pod}/agenda.md",
                content,
                message=message or f"docs({self.pod}): update agenda.md",
                branch=self.branch,
            )
            items = parse_agenda(self.pod, content)
            await self.observer.post(
                "/ingest/agenda",
                json={
                    "pod": self.pod,
                    "items": [
                        {
                            "id": i.id,
                            "section": i.section.value,
                            "text": i.text,
                            "eta": i.eta,
                            "updated_at": i.updated_at.isoformat(),
                        }
                        for i in items
                    ],
                },
            )


__all__ = ["DualWriter"]
