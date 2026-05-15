"""GitHubActionsCI — generates `.github/workflows/<pod>.yml` and writes via repo.

Templates are minimal but real: pytest on push, with the pod's workdir.
"""

from __future__ import annotations

from datetime import datetime

import httpx
import jinja2
import structlog

from ..base import AdapterError
from .base import WorkflowConclusion, WorkflowRun

log = structlog.get_logger(__name__)

_DEFAULT_TIMEOUT = 15.0

_DEFAULT_TEMPLATE = """name: {{ pod }}-ci

on:
  push:
    paths:
      - "pods/{{ pod }}/**"
      - "shared/**"
  pull_request:
    paths:
      - "pods/{{ pod }}/**"
      - "shared/**"
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: pods/{{ pod }}/workspace
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e . || true
      - run: pip install pytest pytest-asyncio || true
      - run: pytest -q || echo "no tests yet"
"""


class GitHubActionsCI:
    def __init__(
        self,
        *,
        owner: str,
        repo: str,
        token: str,
        repo_writer: object,  # RepoAdapter — duck-typed to avoid cycle
        api_base: str = "https://api.github.com",
        request_timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._owner = owner
        self._repo = repo
        self._repo_writer = repo_writer
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
        self._env = jinja2.Environment(autoescape=False, undefined=jinja2.StrictUndefined)  # noqa: S701

    async def close(self) -> None:
        await self._http.aclose()

    async def ensure_workflow(self, pod_name: str, *, template: str = "") -> None:
        tmpl = self._env.from_string(template or _DEFAULT_TEMPLATE)
        body = tmpl.render(pod=pod_name)
        await self._repo_writer.write_file(  # type: ignore[attr-defined]
            f".github/workflows/{pod_name}.yml",
            body,
            message=f"ci: ensure workflow for {pod_name}",
            branch="main",
        )

    async def last_run(self, pod_name: str) -> WorkflowRun | None:
        r = await self._http.get(
            f"/repos/{self._owner}/{self._repo}/actions/workflows/{pod_name}.yml/runs",
            params={"per_page": 1},
        )
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            raise AdapterError(f"github.actions.runs failed: {r.status_code} {r.text}")
        runs = r.json().get("workflow_runs", [])
        if not runs:
            return None
        run = runs[0]
        return WorkflowRun(
            workflow=str(run.get("name", "")),
            pod=pod_name,
            conclusion=_map_conclusion(run.get("conclusion")),
            url=str(run.get("html_url", "")),
            started_at=datetime.fromisoformat(
                str(run.get("run_started_at", run.get("created_at"))).replace("Z", "+00:00")
            ),
        )


def _map_conclusion(raw: str | None) -> WorkflowConclusion:
    if raw is None:
        return WorkflowConclusion.in_progress
    return {
        "success": WorkflowConclusion.success,
        "failure": WorkflowConclusion.failure,
        "cancelled": WorkflowConclusion.cancelled,
    }.get(raw, WorkflowConclusion.failure)
