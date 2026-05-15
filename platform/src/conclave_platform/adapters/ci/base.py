"""CI/CD adapter — slot 4. Coupled with repo (GitHub→Actions, GitLab→GitLab CI)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable


class WorkflowConclusion(StrEnum):
    success = "success"
    failure = "failure"
    cancelled = "cancelled"
    in_progress = "in_progress"


@dataclass(frozen=True, slots=True)
class WorkflowRun:
    workflow: str
    pod: str
    conclusion: WorkflowConclusion
    url: str
    started_at: datetime


@runtime_checkable
class CIAdapter(Protocol):
    async def ensure_workflow(self, pod_name: str, *, template: str) -> None: ...

    async def last_run(self, pod_name: str) -> WorkflowRun | None: ...
