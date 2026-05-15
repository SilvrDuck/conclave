"""Adapter Protocols are runtime-checkable; minimal fake impls satisfy them."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import cast

from conclave_platform.adapters import (
    BusAdapter,
    CIAdapter,
    CliAdapter,
    CliSession,
    Commit,
    DocsAdapter,
    LogAdapter,
    Mount,
    NotifyAdapter,
    PodStatus,
    RepoAdapter,
    RuntimeAdapter,
    SpanEvent,
    Subscription,
    TraceAdapter,
    WorkflowRun,
)
from conclave_platform.adapters.bus import Handler
from conclave_platform.adapters.notify import NotifyLevel
from conclave_platform.core import AdrId, Event, PodName


class _FakeSub:
    async def unsubscribe(self) -> None:
        pass


class _FakeBus:
    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def publish(
        self, topic: str, payload: bytes, *, headers: dict[str, str] | None = None
    ) -> None:
        pass

    async def subscribe(self, topic: str, handler: Handler) -> Subscription:
        return _FakeSub()

    async def request(self, topic: str, payload: bytes, *, timeout: float) -> bytes:
        return b""


class _FakeRuntime:
    async def ensure_pod(
        self, pod_name: str, *, image: str, env: dict[str, str], mounts: list[Mount]
    ) -> None:
        pass

    async def stop_pod(self, pod_name: str) -> None:
        pass

    async def pod_status(self, pod_name: str) -> PodStatus:
        return PodStatus.running

    async def list_pods(self) -> list[str]:
        return []


class _FakeRepo:
    async def ensure_branch(self, branch: str, *, from_ref: str = "main") -> None:
        pass

    async def read_file(self, path: str, *, ref: str = "HEAD") -> str | None:
        return None

    async def write_file(
        self, path: str, content: str, *, message: str, branch: str
    ) -> Commit:
        return Commit(sha="0" * 40)

    async def list_files(self, prefix: str = "", *, ref: str = "HEAD") -> list[str]:
        return []

    async def open_pr(self, *, title: str, body: str, head: str, base: str = "main") -> str:
        return "https://example.com/pr/1"


class _FakeCI:
    async def ensure_workflow(self, pod_name: str, *, template: str) -> None:
        pass

    async def last_run(self, pod_name: str) -> WorkflowRun | None:
        return None


class _FakeDocs:
    async def write_adr(
        self,
        *,
        title: str,
        body: str,
        affected_pods: list[PodName],
        proposal_id: str | None = None,
    ) -> AdrId:
        return AdrId("adr-1")

    async def read(self, adr_id: AdrId) -> None:
        return None

    async def search(self, query: str, *, limit: int = 10) -> list:
        return []

    async def list(self, *, pod: PodName | None = None, limit: int = 100) -> list:
        return []


class _FakeTrace:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def stream(self) -> AsyncIterator[SpanEvent]:
        if False:  # pragma: no cover - empty async generator
            yield  # type: ignore[unreachable]


class _FakeLog:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def stream(self, pod_name: str) -> AsyncIterator[str]:
        if False:  # pragma: no cover
            yield  # type: ignore[unreachable]


class _FakeNotify:
    async def notify(self, message: str, *, level: NotifyLevel = NotifyLevel.info) -> None:
        pass


class _FakeCli:
    async def start(
        self,
        *,
        charter: str,
        cwd: Path,
        session_dir: Path,
        env: dict[str, str],
        startup_timeout: float,
    ) -> CliSession:
        return CliSession(session_id="s-1", pid=1)

    async def resume(
        self,
        *,
        session: CliSession,
        cwd: Path,
        session_dir: Path,
        env: dict[str, str],
        startup_timeout: float,
    ) -> CliSession:
        return session

    async def deliver(self, session: CliSession, event: Event) -> None:
        pass

    async def is_alive(self, session: CliSession) -> bool:
        return True

    async def stop(self, session: CliSession, *, timeout: float) -> None:
        pass

    async def stream_output(self, session: CliSession) -> AsyncIterator[str]:
        if False:  # pragma: no cover
            yield  # type: ignore[unreachable]


def test_all_interfaces_runtime_checkable() -> None:
    # Each Protocol is @runtime_checkable; isinstance is a structural check.
    assert isinstance(_FakeBus(), BusAdapter)
    assert isinstance(_FakeRuntime(), RuntimeAdapter)
    assert isinstance(_FakeRepo(), RepoAdapter)
    assert isinstance(_FakeCI(), CIAdapter)
    assert isinstance(_FakeDocs(), DocsAdapter)
    assert isinstance(_FakeTrace(), TraceAdapter)
    assert isinstance(_FakeLog(), LogAdapter)
    assert isinstance(_FakeNotify(), NotifyAdapter)
    assert isinstance(_FakeCli(), CliAdapter)


def test_cast_works_for_typing() -> None:
    # mypy: structural typing → no special imports needed at call sites.
    bus = cast(BusAdapter, _FakeBus())
    assert bus is not None
