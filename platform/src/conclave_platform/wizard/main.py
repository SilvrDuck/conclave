"""conclave-wizard CLI entry point.

Three-step interactive flow (or `--quickstart`) that emits:
- conclave.config.yaml
- infra/compose.yaml
- .github/workflows/<founder>.yml
- .env (or appends to existing one)
- pods/<founder>/ skeleton
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import click
import questionary

from ..core.config import (
    BusSlot,
    CISlot,
    CliSlot,
    ConclaveConfig,
    DocsSlot,
    Limits,
    LogSlot,
    NotifyConfig,
    NotifySlot,
    RepoConfig,
    RepoSlot,
    RuntimeSlot,
    Slots,
    TraceSlot,
)
from .seed import seed_founder
from .templates import render_compose, render_env, render_pod_workflow


@dataclass(frozen=True)
class Credentials:
    github_token: str
    telegram_bot_token: str | None
    telegram_chat_id: str | None


def _quickstart_slots() -> Slots:
    return Slots(
        runtime=RuntimeSlot.compose,
        bus=BusSlot.nats,
        repo=RepoSlot.github,
        ci=CISlot.github_actions,
        docs=DocsSlot.github_issues,
        cli=CliSlot.pi,
        trace=TraceSlot.otel_tempo,
        log=LogSlot.stdout,
        notify=NotifySlot.telegram,
    )


def _build_config(
    *,
    project_name: str,
    slots: Slots,
    repo_owner: str,
    repo_name: str,
    telegram_chat_id: str | None,
) -> ConclaveConfig:
    return ConclaveConfig(
        project_name=project_name,
        slots=slots,
        repo=RepoConfig(owner=repo_owner, name=repo_name),
        notify=NotifyConfig(telegram_chat_id=telegram_chat_id),
        limits=Limits(),
    )


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _append_env(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text()
        separator = "" if existing.endswith("\n") else "\n"
        path.write_text(existing + separator + content)
        return
    path.write_text(content)


def init_project(
    *,
    project_root: Path,
    project_name: str,
    founder_name: str,
    mandate: str,
    slots: Slots,
    repo_owner: str,
    repo_name: str,
    credentials: Credentials,
) -> ConclaveConfig:
    """Write every wizard artifact under project_root. Returns the config."""
    config = _build_config(
        project_name=project_name,
        slots=slots,
        repo_owner=repo_owner,
        repo_name=repo_name,
        telegram_chat_id=credentials.telegram_chat_id,
    )
    config.dump(project_root / "conclave.config.yaml")
    _write_file(project_root / "infra" / "compose.yaml", render_compose(config))
    _write_file(
        project_root / ".github" / "workflows" / f"{founder_name}.yml",
        render_pod_workflow(founder_name),
    )
    _append_env(
        project_root / ".env",
        render_env(
            config,
            github_token=credentials.github_token,
            telegram_bot_token=credentials.telegram_bot_token,
            telegram_chat_id=credentials.telegram_chat_id,
        ),
    )
    seed_founder(project_root=project_root, founder_name=founder_name, mandate=mandate)
    return config


def _prompt_slots(default: Slots) -> Slots:
    runtime = questionary.select(
        "Runtime",
        choices=[s.value for s in RuntimeSlot],
        default=default.runtime.value,
    ).unsafe_ask()
    bus = questionary.select(
        "Bus", choices=[s.value for s in BusSlot], default=default.bus.value
    ).unsafe_ask()
    repo = questionary.select(
        "Repo host", choices=[s.value for s in RepoSlot], default=default.repo.value
    ).unsafe_ask()
    ci = CISlot.github_actions if repo == RepoSlot.github.value else CISlot.gitlab_ci
    docs = questionary.select(
        "Docs", choices=[s.value for s in DocsSlot], default=default.docs.value
    ).unsafe_ask()
    cli = questionary.select(
        "CLI runtime", choices=[s.value for s in CliSlot], default=default.cli.value
    ).unsafe_ask()
    trace = questionary.select(
        "Traces", choices=[s.value for s in TraceSlot], default=default.trace.value
    ).unsafe_ask()
    log_ = questionary.select(
        "Logs", choices=[s.value for s in LogSlot], default=default.log.value
    ).unsafe_ask()
    notify = questionary.select(
        "Notifications",
        choices=[s.value for s in NotifySlot],
        default=default.notify.value,
    ).unsafe_ask()
    return Slots(
        runtime=RuntimeSlot(runtime),
        bus=BusSlot(bus),
        repo=RepoSlot(repo),
        ci=ci,
        docs=DocsSlot(docs),
        cli=CliSlot(cli),
        trace=TraceSlot(trace),
        log=LogSlot(log_),
        notify=NotifySlot(notify),
    )


def _prompt_credentials(slots: Slots) -> Credentials:
    github_token = questionary.password("GITHUB_TOKEN").unsafe_ask()
    if slots.notify == NotifySlot.telegram:
        telegram_bot_token = questionary.password("TELEGRAM_BOT_TOKEN").unsafe_ask()
        telegram_chat_id = questionary.text("TELEGRAM_CHAT_ID").unsafe_ask()
        return Credentials(github_token, telegram_bot_token, telegram_chat_id)
    return Credentials(github_token, None, None)


@click.group()
def cli() -> None:
    """Conclave wizard."""


@cli.command()
@click.option("--project-root", type=click.Path(file_okay=False, path_type=Path), default=Path())
@click.option("--quickstart", is_flag=True, help="Skip prompts, use Local Demo preset.")
@click.option("--project-name", default="conclave-project")
@click.option("--founder-name", default="founder")
@click.option("--mandate", default="ship the project end-to-end")
@click.option("--repo-owner", default="SilvrDuck")
@click.option("--repo-name", default="conclave-playground")
@click.option("--github-token", default=None, help="Used in --quickstart mode.")
@click.option("--telegram-bot-token", default=None)
@click.option("--telegram-chat-id", default=None)
def init(
    project_root: Path,
    quickstart: bool,
    project_name: str,
    founder_name: str,
    mandate: str,
    repo_owner: str,
    repo_name: str,
    github_token: str | None,
    telegram_bot_token: str | None,
    telegram_chat_id: str | None,
) -> None:
    """Initialize a Conclave project."""
    project_root = project_root.resolve()
    if quickstart:
        slots = _quickstart_slots()
        if github_token is None:
            raise click.UsageError("--github-token is required with --quickstart")
        credentials = Credentials(github_token, telegram_bot_token, telegram_chat_id)
    else:
        slots = _prompt_slots(_quickstart_slots())
        credentials = _prompt_credentials(slots)
    init_project(
        project_root=project_root,
        project_name=project_name,
        founder_name=founder_name,
        mandate=mandate,
        slots=slots,
        repo_owner=repo_owner,
        repo_name=repo_name,
        credentials=credentials,
    )
    click.echo(f"Conclave initialized at {project_root}")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
