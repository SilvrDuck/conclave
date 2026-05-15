"""ConclaveConfig — the single source of platform truth.

Emitted by the wizard, read by every service at startup. The set of slot values
determines which adapter implementations are instantiated.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, Field, model_validator


class RuntimeSlot(StrEnum):
    compose = "compose"
    k3d_terraform = "k3d_terraform"


class BusSlot(StrEnum):
    nats = "nats"
    redis_streams = "redis_streams"


class RepoSlot(StrEnum):
    github = "github"
    gitlab = "gitlab"


class CISlot(StrEnum):
    github_actions = "github_actions"
    gitlab_ci = "gitlab_ci"


class DocsSlot(StrEnum):
    github_issues = "github_issues"
    obsidian = "obsidian"


class CliSlot(StrEnum):
    pi = "pi"
    claude_code = "claude_code"


class TraceSlot(StrEnum):
    otel_tempo = "otel_tempo"
    linkerd = "linkerd"


class LogSlot(StrEnum):
    stdout = "stdout"
    loki = "loki"


class NotifySlot(StrEnum):
    telegram = "telegram"
    email = "email"


class Slots(BaseModel):
    runtime: RuntimeSlot = RuntimeSlot.compose
    bus: BusSlot = BusSlot.nats
    repo: RepoSlot = RepoSlot.github
    ci: CISlot = CISlot.github_actions
    docs: DocsSlot = DocsSlot.github_issues
    cli: CliSlot = CliSlot.pi
    trace: TraceSlot = TraceSlot.otel_tempo
    log: LogSlot = LogSlot.stdout
    notify: NotifySlot = NotifySlot.telegram

    @model_validator(mode="after")
    def repo_ci_coupling(self) -> Self:
        # CI is coupled to repo host: GitHub → Actions, GitLab → GitLab CI.
        if self.repo == RepoSlot.github and self.ci != CISlot.github_actions:
            raise ValueError("repo=github requires ci=github_actions")
        if self.repo == RepoSlot.gitlab and self.ci != CISlot.gitlab_ci:
            raise ValueError("repo=gitlab requires ci=gitlab_ci")
        return self


class RepoConfig(BaseModel):
    owner: str
    name: str
    default_branch: str = "main"

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


class NotifyConfig(BaseModel):
    telegram_chat_id: str | None = None
    email_to: str | None = None


class Limits(BaseModel):
    max_concurrent_pi: int = Field(default=1, ge=1, le=32)
    pi_idle_seconds: int = Field(default=120, ge=10)
    senate_default_timeout_seconds: int = Field(default=900, ge=30)


class ConclaveConfig(BaseModel):
    """Loaded from conclave.config.yaml at the monorepo root."""

    project_name: str
    slots: Slots = Field(default_factory=Slots)
    repo: RepoConfig
    notify: NotifyConfig = Field(default_factory=NotifyConfig)
    limits: Limits = Field(default_factory=Limits)
    bus_url: str = "nats://bus:4222"
    observer_url: str = "http://observer:8000"
    senate_url: str = "http://senate-ledger:8001"
    mcp_coms_url: str = "http://mcp-coms:8002"
    mcp_senate_url: str = "http://mcp-senate:8003"
    mcp_decisions_url: str = "http://mcp-decisions:8004"
    mcp_state_url: str = "http://mcp-state:8005"

    @classmethod
    def load(cls, path: Path) -> ConclaveConfig:
        data = yaml.safe_load(path.read_text())
        return cls.model_validate(data)

    def dump(self, path: Path) -> None:
        path.write_text(yaml.safe_dump(self.model_dump(mode="json"), sort_keys=False))
