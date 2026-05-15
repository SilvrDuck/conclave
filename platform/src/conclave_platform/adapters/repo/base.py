"""Repo host adapter — slot 3.

Backs git operations (per-pod commits from the harness) and PR creation.
Filesystem ops should be branch-scoped and atomic per commit.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..base import Commit


@runtime_checkable
class RepoAdapter(Protocol):
    async def ensure_branch(self, branch: str, *, from_ref: str = "main") -> None: ...

    async def read_file(self, path: str, *, ref: str = "HEAD") -> str | None: ...

    async def write_file(
        self,
        path: str,
        content: str,
        *,
        message: str,
        branch: str,
    ) -> Commit: ...

    async def list_files(self, prefix: str = "", *, ref: str = "HEAD") -> list[str]: ...

    async def open_pr(
        self,
        *,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> str:
        """Return the PR URL."""
        ...
