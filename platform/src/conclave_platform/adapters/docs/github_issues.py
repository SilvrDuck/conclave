"""GitHub-Issues-backed DocsAdapter.

Each ADR is a GitHub issue with the `adr` label. The body is the ADR markdown,
the title is the ADR title, and the issue number is the ADR id (rendered as
`adr-<number>` for cross-system stability). Affected pods become extra labels
(`pod:<name>`). The issue is auto-closed once written — Conclave doesn't use
issue state for discussion.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx
import structlog

from ...core import Adr, AdrId, PodName, ProposalId, utc_now
from ..base import AdapterError

log = structlog.get_logger(__name__)

_ADR_LABEL = "adr"
_POD_LABEL_PREFIX = "pod:"
_DEFAULT_TIMEOUT = 15.0


def _id_to_number(adr_id: AdrId) -> int:
    m = re.fullmatch(r"adr-(\d+)", adr_id)
    if not m:
        raise ValueError(f"not a github-issues adr id: {adr_id}")
    return int(m.group(1))


def _number_to_id(n: int) -> AdrId:
    return AdrId(f"adr-{n}")


class GitHubIssuesDocs:
    def __init__(
        self,
        *,
        owner: str,
        repo: str,
        token: str,
        api_base: str = "https://api.github.com",
        request_timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._owner = owner
        self._repo = repo
        self._client = httpx.AsyncClient(
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
        await self._client.aclose()

    def _repo_path(self, suffix: str = "") -> str:
        return f"/repos/{self._owner}/{self._repo}{suffix}"

    async def _ensure_labels(self, labels: list[str]) -> None:
        # Cheap: create-or-409. We don't care about colors.
        for name in labels:
            r = await self._client.post(
                self._repo_path("/labels"),
                json={"name": name, "color": "ededed"},
            )
            if r.status_code not in (201, 422):
                log.warning("github.label.create_failed", label=name, status=r.status_code)

    async def write_adr(
        self,
        *,
        title: str,
        body: str,
        affected_pods: list[PodName],
        proposal_id: str | None = None,
    ) -> AdrId:
        labels = [_ADR_LABEL, *(f"{_POD_LABEL_PREFIX}{p}" for p in affected_pods)]
        await self._ensure_labels(labels)
        full_body = body if proposal_id is None else f"{body}\n\n---\nproposal: {proposal_id}"
        r = await self._client.post(
            self._repo_path("/issues"),
            json={"title": title, "body": full_body, "labels": labels},
        )
        if r.status_code != 201:
            raise AdapterError(f"github.issues.create failed: {r.status_code} {r.text}")
        n = int(r.json()["number"])
        close = await self._client.patch(self._repo_path(f"/issues/{n}"), json={"state": "closed"})
        if close.status_code != 200:
            log.warning("github.issue.close_failed", number=n, status=close.status_code)
        return _number_to_id(n)

    async def read(self, adr_id: AdrId) -> Adr | None:
        n = _id_to_number(adr_id)
        r = await self._client.get(self._repo_path(f"/issues/{n}"))
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            raise AdapterError(f"github.issues.read failed: {r.status_code} {r.text}")
        return _to_adr(r.json())

    async def search(self, query: str, *, limit: int = 10) -> list[Adr]:
        q = f"repo:{self._owner}/{self._repo} label:{_ADR_LABEL} {query}"
        r = await self._client.get(
            "/search/issues",
            params={"q": q, "per_page": min(limit, 100)},
        )
        if r.status_code != 200:
            raise AdapterError(f"github.search failed: {r.status_code} {r.text}")
        items = r.json().get("items", [])
        return [_to_adr(i) for i in items[:limit]]

    async def list(
        self,
        *,
        pod: PodName | None = None,
        limit: int = 100,
    ) -> list[Adr]:
        labels = [_ADR_LABEL]
        if pod is not None:
            labels.append(f"{_POD_LABEL_PREFIX}{pod}")
        r = await self._client.get(
            self._repo_path("/issues"),
            params={
                "labels": ",".join(labels),
                "state": "all",
                "per_page": min(limit, 100),
                "sort": "created",
                "direction": "desc",
            },
        )
        if r.status_code != 200:
            raise AdapterError(f"github.issues.list failed: {r.status_code} {r.text}")
        return [_to_adr(i) for i in r.json()][:limit]


def _to_adr(issue: dict[str, Any]) -> Adr:
    labels = [
        str(label["name"]) if isinstance(label, dict) else str(label)
        for label in issue.get("labels", [])
    ]
    affected = [
        PodName(label.removeprefix(_POD_LABEL_PREFIX))
        for label in labels
        if label.startswith(_POD_LABEL_PREFIX)
    ]
    body = str(issue.get("body") or "")
    proposal_id: ProposalId | None = None
    m = re.search(r"^proposal:\s*(\S+)\s*$", body, re.MULTILINE)
    if m:
        proposal_id = ProposalId(m.group(1))
    created_raw = issue.get("created_at")
    created = (
        datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
        if created_raw
        else utc_now()
    )
    return Adr(
        id=_number_to_id(int(issue["number"])),
        title=str(issue["title"]),
        body=body,
        affected_pods=affected,
        proposal_id=proposal_id,
        created_at=created,
    )
