"""GitLab CI adapter — stub for alpha. See `github_actions` for the wired pair."""

from __future__ import annotations

from ..base import AdapterNotImplementedError
from .base import WorkflowRun

_MSG = "GitLab CI not wired in alpha"


class GitLabCI:
    def __init__(self, project_id: int, token: str) -> None:
        self._project_id = project_id
        self._token = token

    async def ensure_workflow(self, pod_name: str, *, template: str) -> None:
        raise AdapterNotImplementedError(_MSG)

    async def last_run(self, pod_name: str) -> WorkflowRun | None:
        raise AdapterNotImplementedError(_MSG)
