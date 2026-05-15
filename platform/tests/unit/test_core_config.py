"""ConclaveConfig round-trip + repo/CI coupling validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from conclave_platform.core import (
    BusSlot,
    CISlot,
    ConclaveConfig,
    Limits,
    NotifyConfig,
    RepoConfig,
    RepoSlot,
    Slots,
)


def _make_config(**slot_overrides: object) -> ConclaveConfig:
    return ConclaveConfig(
        project_name="todo-api",
        repo=RepoConfig(owner="SilvrDuck", name="conclave-playground"),
        slots=Slots(**slot_overrides),  # type: ignore[arg-type]
        notify=NotifyConfig(telegram_chat_id="107650898"),
        limits=Limits(max_concurrent_pi=1),
    )


def test_round_trip_yaml(tmp_path: Path) -> None:
    cfg = _make_config()
    path = tmp_path / "conclave.config.yaml"
    cfg.dump(path)
    loaded = ConclaveConfig.load(path)
    assert loaded == cfg


def test_repo_full_name() -> None:
    cfg = _make_config()
    assert cfg.repo.full_name == "SilvrDuck/conclave-playground"


def test_github_requires_actions() -> None:
    with pytest.raises(ValidationError, match="ci=github_actions"):
        _make_config(repo=RepoSlot.github, ci=CISlot.gitlab_ci)


def test_gitlab_requires_gitlab_ci() -> None:
    with pytest.raises(ValidationError, match="ci=gitlab_ci"):
        _make_config(repo=RepoSlot.gitlab, ci=CISlot.github_actions)


def test_defaults_are_quickstart() -> None:
    cfg = _make_config()
    assert cfg.slots.bus == BusSlot.nats
    assert cfg.slots.repo == RepoSlot.github
    assert cfg.limits.max_concurrent_pi == 1
