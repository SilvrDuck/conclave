"""GitLabRepo — stub for alpha. See `github` for the wired pair."""

from __future__ import annotations

from pathlib import Path

from ..base import AdapterNotImplementedError, Commit

_MSG = "GitLab repo not wired in alpha"


class GitLabRepo:
    def __init__(self, workdir: Path, project_id: int, token: str) -> None:
        self._workdir = workdir
        self._project_id = project_id
        self._token = token

    async def ensure_branch(self, branch: str, *, from_ref: str = "main") -> None:
        raise AdapterNotImplementedError(_MSG)

    async def read_file(self, path: str, *, ref: str = "HEAD") -> str | None:
        raise AdapterNotImplementedError(_MSG)

    async def write_file(
        self,
        path: str,
        content: str,
        *,
        message: str,
        branch: str,
    ) -> Commit:
        raise AdapterNotImplementedError(_MSG)

    async def list_files(self, prefix: str = "", *, ref: str = "HEAD") -> list[str]:
        raise AdapterNotImplementedError(_MSG)

    async def open_pr(
        self,
        *,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> str:
        raise AdapterNotImplementedError(_MSG)
