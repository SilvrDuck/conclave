"""GitHubRepo — LocalGitRepo plus PR creation over the GitHub REST API."""

from __future__ import annotations

from pathlib import Path

import httpx

from ..base import AdapterError
from .local_git import LocalGitRepo

_DEFAULT_TIMEOUT = 15.0


class GitHubRepo(LocalGitRepo):
    def __init__(
        self,
        *,
        workdir: Path,
        owner: str,
        repo: str,
        token: str,
        api_base: str = "https://api.github.com",
        request_timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(workdir=workdir)
        self._owner = owner
        self._repo = repo
        self._http = httpx.AsyncClient(
            base_url=api_base,
            timeout=request_timeout,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "conclave-platform/0.1",
            },
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def open_pr(
        self,
        *,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> str:
        r = await self._http.post(
            f"/repos/{self._owner}/{self._repo}/pulls",
            json={"title": title, "body": body, "head": head, "base": base},
        )
        if r.status_code not in (200, 201):
            raise AdapterError(f"github.pr.create failed: {r.status_code} {r.text}")
        return str(r.json()["html_url"])
