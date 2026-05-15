"""Wizard: artifact generation, CLI quickstart, founder seed."""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from conclave_platform.core.config import ConclaveConfig
from conclave_platform.wizard import (
    Credentials,
    init_project,
    render_compose,
    render_pod_workflow,
    seed_founder,
)
from conclave_platform.wizard.main import _quickstart_slots, cli


def _creds() -> Credentials:
    return Credentials(
        github_token="ghp_x",
        telegram_bot_token="T",
        telegram_chat_id="107650898",
    )


def test_init_project_writes_all_artifacts(tmp_path: Path) -> None:
    init_project(
        project_root=tmp_path,
        project_name="todo-api",
        founder_name="founder",
        mandate="build a TODO API",
        slots=_quickstart_slots(),
        repo_owner="SilvrDuck",
        repo_name="conclave-playground",
        credentials=_creds(),
    )
    assert (tmp_path / "conclave.config.yaml").is_file()
    assert (tmp_path / "infra" / "compose.yaml").is_file()
    assert (tmp_path / ".github" / "workflows" / "founder.yml").is_file()
    assert (tmp_path / ".env").is_file()
    assert (tmp_path / "pods" / "founder" / "charter.md").is_file()
    assert (tmp_path / "pods" / "founder" / "workspace" / ".gitkeep").is_file()


def test_generated_config_round_trips(tmp_path: Path) -> None:
    init_project(
        project_root=tmp_path,
        project_name="todo-api",
        founder_name="founder",
        mandate="ship it",
        slots=_quickstart_slots(),
        repo_owner="SilvrDuck",
        repo_name="conclave-playground",
        credentials=_creds(),
    )
    loaded = ConclaveConfig.load(tmp_path / "conclave.config.yaml")
    assert loaded.project_name == "todo-api"
    assert loaded.repo.full_name == "SilvrDuck/conclave-playground"


def test_compose_contains_required_services() -> None:
    config = ConclaveConfig(
        project_name="todo-api",
        repo={"owner": "o", "name": "r"},  # type: ignore[arg-type]
    )
    body = render_compose(config)
    data = yaml.safe_load(body)
    assert "bus" in data["services"]
    assert "observer" in data["services"]
    assert "senate-ledger" in data["services"]
    assert data["services"]["bus"]["image"].startswith("nats:")


def test_pod_workflow_references_workspace() -> None:
    body = render_pod_workflow("founder")
    assert "pods/founder/workspace" in body
    assert "name: founder-ci" in body


def test_seed_founder_charter_mentions_propose_member(tmp_path: Path) -> None:
    seed_founder(project_root=tmp_path, founder_name="founder", mandate="ship it")
    charter = (tmp_path / "pods" / "founder" / "charter.md").read_text()
    assert "senate.propose_member" in charter
    assert (tmp_path / "pods" / "founder" / "endpoints.md").read_text() == "# Endpoints\n"


def test_env_appends_when_existing(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("EXISTING=1\n")
    init_project(
        project_root=tmp_path,
        project_name="todo-api",
        founder_name="founder",
        mandate="ship it",
        slots=_quickstart_slots(),
        repo_owner="o",
        repo_name="r",
        credentials=_creds(),
    )
    env = (tmp_path / ".env").read_text()
    assert "EXISTING=1" in env
    assert "GITHUB_TOKEN=ghp_x" in env


def test_cli_quickstart(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "init",
            "--quickstart",
            "--project-root",
            str(tmp_path),
            "--founder-name",
            "founder",
            "--mandate",
            "build TODO API",
            "--github-token",
            "ghp_x",
            "--telegram-bot-token",
            "T",
            "--telegram-chat-id",
            "107650898",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "conclave.config.yaml").is_file()
    assert (tmp_path / "infra" / "compose.yaml").is_file()
    assert (tmp_path / ".github" / "workflows" / "founder.yml").is_file()


def test_cli_quickstart_requires_token(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["init", "--quickstart", "--project-root", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "github-token" in result.output.lower()
