"""PiCli adapter — subprocess spawn, deliver, stop. Plus ClaudeCode stub."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Iterable
from pathlib import Path
from typing import Any

import pytest

from conclave_platform.adapters import AdapterNotImplementedError, CliAdapter, CliSession
from conclave_platform.adapters.cli import ClaudeCodeCli, PiCli
from conclave_platform.adapters.cli.pi import PiStartupError
from conclave_platform.core import DirectMessage, MessageId, PodName

# ---------- fakes ----------


class _FakeStdout:
    def __init__(self, lines: Iterable[bytes]) -> None:
        self._lines = list(lines)
        self._idx = 0

    def __aiter__(self) -> _FakeStdout:
        return self

    async def __anext__(self) -> bytes:
        if self._idx >= len(self._lines):
            raise StopAsyncIteration
        line = self._lines[self._idx]
        self._idx += 1
        return line

    async def read(self) -> bytes:
        out = b"".join(self._lines[self._idx :])
        self._idx = len(self._lines)
        return out


class _FakeStdin:
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.drained = 0

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    async def drain(self) -> None:
        self.drained += 1


class _FakeProc:
    def __init__(
        self,
        *,
        pid: int = 4242,
        stdout_lines: Iterable[bytes] = (),
        wait_behavior: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self.pid = pid
        self.returncode: int | None = None
        self.stdout = _FakeStdout(stdout_lines)
        self.stdin = _FakeStdin()
        self.terminated = False
        self.killed = False
        self._wait_behavior = wait_behavior

    def terminate(self) -> None:
        self.terminated = True
        if self._wait_behavior is None:
            self.returncode = -15

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    async def wait(self) -> int:
        if self._wait_behavior is not None:
            await self._wait_behavior()
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


def _patch_spawn(
    monkeypatch: pytest.MonkeyPatch, proc: _FakeProc
) -> dict[str, Any]:
    """Replace asyncio.create_subprocess_exec; record argv/cwd/env."""
    capture: dict[str, Any] = {}

    async def fake_exec(*argv: str, **kwargs: Any) -> _FakeProc:
        capture["argv"] = list(argv)
        capture["cwd"] = kwargs.get("cwd")
        capture["env"] = kwargs.get("env")
        return proc

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    return capture


def _session_start(session_id: str = "sess-abc") -> bytes:
    return (
        json.dumps({"type": "session_start", "sessionId": session_id, "reason": "new"})
        + "\n"
    ).encode()


def _direct_message() -> DirectMessage:
    return DirectMessage(
        target_pod=PodName("alice"),
        message_id=MessageId("m1"),
        from_pod=PodName("bob"),
        body="hi",
    )


# ---------- tests ----------


async def test_start_returns_session_with_pid_and_pod_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    proc = _FakeProc(pid=1234, stdout_lines=[])
    cap = _patch_spawn(monkeypatch, proc)
    cli = PiCli()

    sess = await cli.start(
        charter="be helpful",
        cwd=tmp_path,
        session_dir=tmp_path / "pi",
        env={"POD_NAME": "alice"},
        startup_timeout=1.0,
    )

    assert sess.session_id == "alice"
    assert sess.pid == 1234
    assert cap["argv"][0] == "pi"
    assert "--mode" in cap["argv"] and "rpc" in cap["argv"]
    assert "--system-prompt" in cap["argv"]
    assert cap["argv"][cap["argv"].index("--system-prompt") + 1] == "be helpful"
    assert "--session-dir" in cap["argv"]
    # New spawns must NOT pass --session (Pi treats that as resume-or-die).
    assert "--session" not in cap["argv"]
    assert cap["cwd"] == str(tmp_path)
    assert cap["env"] == {"POD_NAME": "alice"}
    await cli.stop(sess, timeout=1.0)


async def test_resume_reloads_charter_from_workspace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "charter.md").write_text("be helpful (resumed)")
    proc = _FakeProc(pid=99, stdout_lines=[])
    cap = _patch_spawn(monkeypatch, proc)
    cli = PiCli()

    sess = await cli.resume(
        session=CliSession(session_id="alice", pid=0),
        cwd=tmp_path,
        session_dir=tmp_path,
        env={},
        startup_timeout=1.0,
    )

    assert sess.session_id == "alice"
    assert "--system-prompt" in cap["argv"]
    assert cap["argv"][cap["argv"].index("--system-prompt") + 1] == "be helpful (resumed)"
    assert "--session" not in cap["argv"]
    await cli.stop(sess, timeout=1.0)


async def test_start_raises_when_pi_exits_immediately(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    proc = _FakeProc(stdout_lines=[b"Error: No API key for provider: anthropic\n"])
    proc.returncode = 1
    _patch_spawn(monkeypatch, proc)
    cli = PiCli()

    with pytest.raises(PiStartupError):
        await cli.start(
            charter="x",
            cwd=tmp_path,
            session_dir=tmp_path,
            env={"POD_NAME": "alice"},
            startup_timeout=0.05,
        )


async def test_deliver_writes_event_json_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    proc = _FakeProc(stdout_lines=[])
    _patch_spawn(monkeypatch, proc)
    cli = PiCli()
    sess = await cli.start(
        charter="c",
        cwd=tmp_path,
        session_dir=tmp_path,
        env={"POD_NAME": "alice"},
        startup_timeout=1.0,
    )

    event = _direct_message()
    await cli.deliver(sess, event)

    written = bytes(proc.stdin.buffer).decode()
    assert written.endswith("\n")
    msg = json.loads(written)
    assert msg["type"] == "prompt"
    inner = json.loads(msg["message"])
    assert inner["type"] == "direct_message"
    assert inner["body"] == "hi"
    assert proc.stdin.drained == 1


async def test_is_alive_tracks_returncode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    proc = _FakeProc(stdout_lines=[])
    _patch_spawn(monkeypatch, proc)
    cli = PiCli()
    sess = await cli.start(
        charter="c",
        cwd=tmp_path,
        session_dir=tmp_path,
        env={"POD_NAME": "alice"},
        startup_timeout=1.0,
    )
    assert await cli.is_alive(sess) is True
    proc.returncode = 0
    assert await cli.is_alive(sess) is False


async def test_stop_terminates_and_waits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    proc = _FakeProc(stdout_lines=[])
    _patch_spawn(monkeypatch, proc)
    cli = PiCli()
    sess = await cli.start(
        charter="c",
        cwd=tmp_path,
        session_dir=tmp_path,
        env={"POD_NAME": "alice"},
        startup_timeout=1.0,
    )

    await cli.stop(sess, timeout=1.0)

    assert proc.terminated is True
    assert proc.killed is False
    assert await cli.is_alive(sess) is False


async def test_stop_kills_hanging_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """terminate() leaves returncode=None; first wait() hangs → fallback kill."""
    waits: list[float] = []

    async def hang_first_then_return() -> None:
        # First call hangs; the second (after kill) returns immediately.
        waits.append(0.0)
        if len(waits) == 1:
            await asyncio.sleep(10)

    proc = _FakeProc(stdout_lines=[_session_start()], wait_behavior=hang_first_then_return)
    _patch_spawn(monkeypatch, proc)
    cli = PiCli()
    sess = await cli.start(
        charter="c",
        cwd=tmp_path,
        session_dir=tmp_path,
        env={"POD_NAME": "alice"},
        startup_timeout=1.0,
    )

    await cli.stop(sess, timeout=0.05)

    assert proc.terminated is True
    assert proc.killed is True


async def test_stream_output_yields_decoded_lines(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lines = [
        b'{"type":"agent_start"}\n',
        b'{"type":"message_update","delta":"hello"}\n',
        b'{"type":"agent_end"}\n',
    ]
    proc = _FakeProc(stdout_lines=lines)
    _patch_spawn(monkeypatch, proc)
    cli = PiCli()
    sess = await cli.start(
        charter="c",
        cwd=tmp_path,
        session_dir=tmp_path,
        env={"POD_NAME": "alice"},
        startup_timeout=1.0,
    )
    # Let the drain task consume the fake stdout.
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    out = [line async for line in cli.stream_output(sess)]
    assert out == [
        '{"type":"agent_start"}',
        '{"type":"message_update","delta":"hello"}',
        '{"type":"agent_end"}',
    ]
    await cli.stop(sess, timeout=1.0)


async def test_pi_satisfies_cli_adapter_protocol() -> None:
    assert isinstance(PiCli(), CliAdapter)


async def test_claude_code_satisfies_cli_adapter_protocol() -> None:
    assert isinstance(ClaudeCodeCli(), CliAdapter)


async def test_claude_code_start_raises_not_implemented(tmp_path: Path) -> None:
    cli = ClaudeCodeCli(some_arg="ignored")
    with pytest.raises(AdapterNotImplementedError):
        await cli.start(
            charter="x",
            cwd=tmp_path,
            session_dir=tmp_path,
            env={},
            startup_timeout=1.0,
        )


async def test_claude_code_deliver_raises_not_implemented(tmp_path: Path) -> None:
    cli = ClaudeCodeCli()
    with pytest.raises(AdapterNotImplementedError):
        await cli.deliver(CliSession(session_id="x", pid=1), _direct_message())
