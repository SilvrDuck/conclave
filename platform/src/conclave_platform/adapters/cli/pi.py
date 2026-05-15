"""Pi (pi.dev coding agent) CliAdapter.

Pi runs as a subprocess in `--mode rpc`: newline-delimited JSON on stdin/stdout.
- Charter   → `--system-prompt <text>`.
- Session   → `--session-dir <dir>`; first `session_start` event yields the id.
- Resume    → `--session <id>` with the same session-dir.
- Deliver   → write `{"type":"prompt","message":<event-json>}\n` to stdin.

Readiness is the first JSONL line from stdout, which is a `session_start` event
carrying the session id (and reason: "new" | "resume" | …).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from ...core import Event
from ..base import AdapterError
from .base import CliSession


class PiStartupError(AdapterError):
    """Pi did not emit a valid `session_start` event before startup_timeout."""


@dataclass(slots=True)
class _Running:
    proc: asyncio.subprocess.Process
    session_id: str


@dataclass(slots=True)
class PiCli:
    binary: str = "pi"
    mode: str = "rpc"
    extra_args: tuple[str, ...] = ()
    _running: dict[str, _Running] = field(default_factory=dict)

    async def start(
        self,
        *,
        charter: str,
        cwd: Path,
        session_dir: Path,
        env: dict[str, str],
        startup_timeout: float,
    ) -> CliSession:
        argv = [
            self.binary,
            "--mode",
            self.mode,
            "--system-prompt",
            charter,
            "--session-dir",
            str(session_dir),
            *self.extra_args,
        ]
        return await self._spawn(argv, cwd=cwd, env=env, startup_timeout=startup_timeout)

    async def resume(
        self,
        *,
        session: CliSession,
        cwd: Path,
        session_dir: Path,
        env: dict[str, str],
        startup_timeout: float,
    ) -> CliSession:
        argv = [
            self.binary,
            "--mode",
            self.mode,
            "--session",
            session.session_id,
            "--session-dir",
            str(session_dir),
            *self.extra_args,
        ]
        return await self._spawn(argv, cwd=cwd, env=env, startup_timeout=startup_timeout)

    async def deliver(self, session: CliSession, event: Event) -> None:
        running = self._require(session)
        stdin = running.proc.stdin
        if stdin is None:
            raise AdapterError(f"Pi session {session.session_id} has no stdin pipe")
        payload = {"type": "prompt", "message": event.model_dump_json()}
        line = (json.dumps(payload) + "\n").encode("utf-8")
        stdin.write(line)
        await stdin.drain()

    async def is_alive(self, session: CliSession) -> bool:
        running = self._running.get(session.session_id)
        if running is None:
            return False
        return running.proc.returncode is None

    async def stop(self, session: CliSession, *, timeout: float) -> None:
        running = self._running.pop(session.session_id, None)
        if running is None:
            return
        proc = running.proc
        if proc.returncode is not None:
            return
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            await proc.wait()

    async def stream_output(self, session: CliSession) -> AsyncIterator[str]:
        running = self._require(session)
        stdout = running.proc.stdout
        if stdout is None:
            raise AdapterError(f"Pi session {session.session_id} has no stdout pipe")
        async for raw in stdout:
            yield raw.decode("utf-8", errors="replace").rstrip("\n")

    async def _spawn(
        self,
        argv: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        startup_timeout: float,
    ) -> CliSession:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(cwd),
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            session_id = await asyncio.wait_for(
                _read_session_id(proc), timeout=startup_timeout
            )
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise PiStartupError(
                f"Pi did not announce session_start within {startup_timeout}s"
            ) from exc
        self._running[session_id] = _Running(proc=proc, session_id=session_id)
        return CliSession(session_id=session_id, pid=proc.pid)

    def _require(self, session: CliSession) -> _Running:
        running = self._running.get(session.session_id)
        if running is None:
            raise AdapterError(f"Pi session {session.session_id} is not tracked")
        return running


async def _read_session_id(proc: asyncio.subprocess.Process) -> str:
    stdout = proc.stdout
    if stdout is None:
        raise AdapterError("Pi subprocess has no stdout pipe")
    async for raw in stdout:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        msg = json.loads(line)
        if msg.get("type") != "session_start":
            continue
        session_id = msg.get("sessionId") or msg.get("session_id")
        if not isinstance(session_id, str):
            raise PiStartupError(f"session_start missing sessionId: {msg!r}")
        return session_id
    raise PiStartupError("Pi exited before emitting session_start")
