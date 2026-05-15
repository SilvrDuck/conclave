"""DockerComposeRuntime — YAML round-trip + faked docker subprocess."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import yaml

from conclave_platform.adapters import Mount, MountMode, PodStatus, RuntimeAdapter
from conclave_platform.adapters.runtime.compose import (
    ComposeCommandError,
    DockerComposeRuntime,
)


@dataclass
class _FakeProc:
    returncode: int
    stdout_bytes: bytes
    stderr_bytes: bytes
    sleep_for: float = 0.0
    killed: bool = False

    async def communicate(self) -> tuple[bytes, bytes]:
        if self.sleep_for:
            await asyncio.sleep(self.sleep_for)
        return self.stdout_bytes, self.stderr_bytes

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        return self.returncode


def _ok(_argv: list[str]) -> _FakeProc:
    return _FakeProc(returncode=0, stdout_bytes=b"", stderr_bytes=b"")


@dataclass
class _Recorder:
    calls: list[list[str]] = field(default_factory=list)
    responder: Callable[[list[str]], _FakeProc] = field(default_factory=lambda: _ok)

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def _fake_exec(*argv: str, **_kwargs: object) -> _FakeProc:
            args = list(argv)
            self.calls.append(args)
            return self.responder(args)

        monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_exec)


def _alice_mounts() -> list[Mount]:
    return [
        Mount(host_path="/repo/pods/alice", container_path="/workspace", mode=MountMode.rw),
        Mount(host_path="/repo", container_path="/conclave", mode=MountMode.ro),
    ]


def _runtime(tmp_path: Path) -> DockerComposeRuntime:
    return DockerComposeRuntime(compose_path=tmp_path / "infra" / "compose.yaml")


async def test_ensure_pod_writes_service_and_runs_compose_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = _Recorder()
    rec.install(monkeypatch)
    rt = _runtime(tmp_path)

    await rt.ensure_pod(
        "alice",
        image="conclave/agent:latest",
        env={"POD_NAME": "alice"},
        mounts=_alice_mounts(),
    )

    data = yaml.safe_load((tmp_path / "infra" / "compose.yaml").read_text())
    alice = data["services"]["alice"]
    assert alice["image"] == "conclave/agent:latest"
    assert alice["container_name"] == "conclave-alice"
    assert alice["environment"] == {"POD_NAME": "alice"}
    assert alice["volumes"] == [
        "/repo/pods/alice:/workspace:rw",
        "/repo:/conclave:ro",
    ]
    assert alice["restart"] == "unless-stopped"
    assert alice["networks"] == ["conclave"]
    assert data["networks"]["conclave"] == {"driver": "bridge"}

    up = rec.calls[-1]
    assert up[:3] == ["docker", "compose", "-f"]
    assert "-p" in up and "conclave" in up
    assert up[-3:] == ["-d", "--no-recreate", "alice"]


async def test_ensure_pod_idempotent_same_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = _Recorder()
    rec.install(monkeypatch)
    rt = _runtime(tmp_path)

    await rt.ensure_pod(
        "alice", image="img:1", env={"K": "V"}, mounts=_alice_mounts()
    )
    first = (tmp_path / "infra" / "compose.yaml").read_text()
    await rt.ensure_pod(
        "alice", image="img:1", env={"K": "V"}, mounts=_alice_mounts()
    )
    second = (tmp_path / "infra" / "compose.yaml").read_text()

    assert first == second


async def test_stop_pod_removes_only_target_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = _Recorder()
    rec.install(monkeypatch)
    rt = _runtime(tmp_path)

    await rt.ensure_pod("alice", image="img:1", env={}, mounts=[])
    await rt.ensure_pod("bob", image="img:1", env={}, mounts=[])
    await rt.stop_pod("alice")

    data = yaml.safe_load((tmp_path / "infra" / "compose.yaml").read_text())
    assert "bob" in data["services"]
    assert "alice" not in data["services"]

    rm = [c for c in rec.calls if "rm" in c]
    assert rm and rm[-1][-1] == "alice"


async def test_pod_status_running(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rec = _Recorder(
        responder=lambda _argv: _FakeProc(
            returncode=0, stdout_bytes=b"running\n", stderr_bytes=b""
        )
    )
    rec.install(monkeypatch)
    rt = _runtime(tmp_path)
    assert await rt.pod_status("alice") == PodStatus.running


async def test_pod_status_stopped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rec = _Recorder(
        responder=lambda _argv: _FakeProc(
            returncode=0, stdout_bytes=b"exited\n", stderr_bytes=b""
        )
    )
    rec.install(monkeypatch)
    rt = _runtime(tmp_path)
    assert await rt.pod_status("alice") == PodStatus.stopped


async def test_pod_status_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rec = _Recorder(
        responder=lambda _argv: _FakeProc(
            returncode=1, stdout_bytes=b"", stderr_bytes=b"no such container"
        )
    )
    rec.install(monkeypatch)
    rt = _runtime(tmp_path)
    assert await rt.pod_status("alice") == PodStatus.missing


async def test_list_pods_reads_yaml_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = _Recorder()
    rec.install(monkeypatch)
    rt = _runtime(tmp_path)

    await rt.ensure_pod("bob", image="img:1", env={}, mounts=[])
    await rt.ensure_pod("alice", image="img:1", env={}, mounts=[])

    assert await rt.list_pods() == ["alice", "bob"]


async def test_ensure_pod_timeout_raises_adapter_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = _Recorder(
        responder=lambda _argv: _FakeProc(
            returncode=0, stdout_bytes=b"", stderr_bytes=b"", sleep_for=1.0
        )
    )
    rec.install(monkeypatch)
    rt = DockerComposeRuntime(
        compose_path=tmp_path / "infra" / "compose.yaml",
        up_timeout=0.05,
    )
    with pytest.raises(ComposeCommandError, match="timed out"):
        await rt.ensure_pod("alice", image="img:1", env={}, mounts=[])


def test_satisfies_protocol(tmp_path: Path) -> None:
    rt = DockerComposeRuntime(compose_path=tmp_path / "infra" / "compose.yaml")
    assert isinstance(rt, RuntimeAdapter)
