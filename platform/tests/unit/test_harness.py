"""Harness unit tests — parsers + dual-write + inbox loop with fake CLI."""

from __future__ import annotations

import asyncio
import subprocess
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
import respx

from conclave_platform.adapters.bus import InMemoryBus
from conclave_platform.adapters.cli import CliSession
from conclave_platform.adapters.repo import LocalGitRepo
from conclave_platform.core import (
    AgendaSection,
    DirectMessage,
    Event,
    EventEnvelope,
    PodName,
    pod_inbox_topic,
)
from conclave_platform.core.ids import MessageId
from conclave_platform.harness.agenda_parser import parse_agenda
from conclave_platform.harness.dual_writer import DualWriter
from conclave_platform.harness.endpoints_parser import parse_endpoints
from conclave_platform.harness.inbox import InboxLoop

# --- agenda parser ---


def test_parse_agenda_full() -> None:
    text = """
## doing
- [alice-42] ship pagination · since 14:02 · eta ~30min

## next
- [alice-43] migrate sessions

## blocked-on
- [alice-41] waiting on bob
""".strip()
    items = parse_agenda(PodName("alice"), text)
    sections = {i.id: i.section for i in items}
    assert sections == {
        "alice-42": AgendaSection.doing,
        "alice-43": AgendaSection.next,
        "alice-41": AgendaSection.blocked_on,
    }


def test_parse_agenda_empty() -> None:
    assert parse_agenda(PodName("alice"), "") == []


# --- endpoints parser ---


def test_parse_endpoints_with_annotations() -> None:
    text = """
# Endpoints

## GET /users/{id}
Returns the user record. 404 when missing.

## POST /users
Create a user; idempotent on email.
""".strip()
    out = parse_endpoints(text)
    assert {(e.method, e.path) for e in out} == {("GET", "/users/{id}"), ("POST", "/users")}
    assert "Returns the user" in out[0].annotation


def test_parse_endpoints_ignores_pre_heading_text() -> None:
    assert parse_endpoints("# Endpoints\n\nNo endpoints yet.\n") == []


# --- dual writer ---


@pytest_asyncio.fixture
async def workspace(tmp_path: Path) -> AsyncIterator[Path]:
    subprocess.run(  # noqa: ASYNC221
        ["git", "init", "-q", "-b", "main", str(tmp_path)], check=True
    )
    (tmp_path / "README.md").write_text("seed\n")
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(  # noqa: ASYNC221
        ["git", "-C", str(tmp_path), "add", "."], check=True, env=env
    )
    subprocess.run(  # noqa: ASYNC221
        ["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True, env=env
    )
    yield tmp_path


@respx.mock
async def test_dual_writer_endpoints_round_trip(workspace: Path) -> None:
    repo = LocalGitRepo(workdir=workspace)
    obs = httpx.AsyncClient(base_url="http://observer", timeout=5.0)
    ingest = respx.post("http://observer/ingest/endpoint").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    dw = DualWriter(
        pod=PodName("alice"), workspace_root=workspace, branch="proto/x",
        repo=repo, observer=obs,
    )
    await dw.write_endpoints("## GET /users\nReturns users.\n")
    # File committed under the branch?
    assert (workspace / "pods/alice/endpoints.md").read_text().startswith("## GET /users")
    assert ingest.called
    body = ingest.calls.last.request.read()
    assert b'"method":"GET"' in body
    assert b'"path":"/users"' in body
    await obs.aclose()


@respx.mock
async def test_dual_writer_agenda_round_trip(workspace: Path) -> None:
    repo = LocalGitRepo(workdir=workspace)
    obs = httpx.AsyncClient(base_url="http://observer", timeout=5.0)
    ingest = respx.post("http://observer/ingest/agenda").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    dw = DualWriter(
        pod=PodName("alice"), workspace_root=workspace, branch="proto/x",
        repo=repo, observer=obs,
    )
    text = "## doing\n- [alice-1] ship pagination\n## next\n## blocked-on\n"
    await dw.write_agenda(text)
    assert ingest.called
    body = ingest.calls.last.request.read()
    assert b"alice-1" in body
    await obs.aclose()


# --- inbox loop with a fake CLI ---


@dataclass
class _FakeCli:
    started: list[CliSession] = field(default_factory=list)
    delivered: list[Event] = field(default_factory=list)
    alive: bool = True
    stopped: bool = False

    async def start(self, **kw: object) -> CliSession:
        sess = CliSession(session_id=f"s-{len(self.started)}", pid=1000 + len(self.started))
        self.started.append(sess)
        return sess

    async def resume(self, *, session: CliSession, **kw: object) -> CliSession:
        return session

    async def deliver(self, session: CliSession, event: Event) -> None:
        self.delivered.append(event)

    async def is_alive(self, session: CliSession) -> bool:
        return self.alive

    async def stop(self, session: CliSession, *, timeout: float) -> None:
        self.stopped = True

    async def stream_output(self, session: CliSession) -> AsyncIterator[str]:
        if False:  # pragma: no cover
            yield  # type: ignore[unreachable]


@pytest.mark.asyncio
async def test_inbox_loop_delivers_event_to_pi(tmp_path: Path) -> None:
    bus = InMemoryBus()
    await bus.connect()
    cli = _FakeCli()
    loop = InboxLoop(
        pod=PodName("alice"),
        bus=bus,
        cli=cli,  # type: ignore[arg-type]
        charter="I am alice",
        pod_workspace=tmp_path,
        session_dir=tmp_path / ".pi",
        env={},
    )
    await loop.start()
    # Send a DM through the inbox topic.
    envelope = EventEnvelope(
        event=DirectMessage(
            target_pod=PodName("alice"),
            message_id=MessageId("m-1"),
            from_pod=PodName("bob"),
            body="hi alice",
        )
    )
    await bus.publish(pod_inbox_topic(PodName("alice")), envelope.model_dump_json().encode())
    # Let the subscribe task run.
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert len(cli.delivered) == 1
    assert isinstance(cli.delivered[0], DirectMessage)
    await loop.stop()
    await bus.close()
    assert cli.stopped is True
