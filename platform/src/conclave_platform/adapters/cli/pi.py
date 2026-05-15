"""Pi (pi.dev coding agent) CliAdapter.

Pi runs as a subprocess in `--mode rpc`: newline-delimited JSON on stdin/stdout.
- Charter   → `--system-prompt <text>`.
- Session   → `--session <name> --session-dir <dir>`; we pick the name (pod
  slug + suffix) and Pi persists transcripts under that name.
- Resume    → same `--session <name>` re-attaches to the saved transcript.
- Deliver   → write `{"type":"prompt","message":<event-json>}\n` to stdin.

Pi's first stdout line lands only AFTER the first prompt (`response` ack +
`agent_start` + message stream). So start/resume don't block on a
session-ready event; the harness spawns and trusts the process is up. A
background drain task consumes stdout so the pipe doesn't backpressure.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from ...core import Event
from ..base import AdapterError
from .base import CliSession

log = structlog.get_logger(__name__)


class PiStartupError(AdapterError):
    """Pi process exited before we could deliver the first prompt."""


@dataclass(slots=True)
class _Running:
    proc: asyncio.subprocess.Process
    session_id: str
    drain_task: asyncio.Task[None]
    output_tail: list[str]


@dataclass(slots=True)
class PiCli:
    binary: str = "pi"
    mode: str = "rpc"
    model: str | None = None
    extra_args: tuple[str, ...] = ()
    _running: dict[str, _Running] = field(default_factory=dict)

    def _common_args(self) -> list[str]:
        args: list[str] = [self.binary, "--mode", self.mode]
        if self.model:
            args.extend(["--model", self.model])
        return args

    async def start(
        self,
        *,
        charter: str,
        cwd: Path,
        session_dir: Path,
        env: dict[str, str],
        startup_timeout: float,
    ) -> CliSession:
        # Pi --session <name> only resumes an existing session, never creates
        # one — so we omit it on first spawn and let Pi mint an id. We track
        # the process under a local pod-scoped key for is_alive/deliver/stop.
        session_name = env.get("POD_NAME", f"pod-{uuid.uuid4().hex[:8]}")
        argv = [
            *self._common_args(),
            "--system-prompt",
            charter,
            "--session-dir",
            str(session_dir),
            *self.extra_args,
        ]
        return await self._spawn(
            argv,
            cwd=cwd,
            env=env,
            startup_timeout=startup_timeout,
            session_id=session_name,
        )

    async def resume(
        self,
        *,
        session: CliSession,
        cwd: Path,
        session_dir: Path,
        env: dict[str, str],
        startup_timeout: float,
    ) -> CliSession:
        # No real session persistence yet — re-spawn from the charter on disk.
        # The pod's mandate context lives in charter.md / agenda.md /
        # endpoints.md inside the workspace, which Pi can re-read at any time.
        charter_path = Path(cwd) / "charter.md"
        charter = charter_path.read_text(encoding="utf-8") if charter_path.exists() else ""
        argv = [
            *self._common_args(),
            "--system-prompt",
            charter,
            "--session-dir",
            str(session_dir),
            *self.extra_args,
        ]
        return await self._spawn(
            argv,
            cwd=cwd,
            env=env,
            startup_timeout=startup_timeout,
            session_id=session.session_id,
        )

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
        running.drain_task.cancel()
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
        while running.output_tail:
            yield running.output_tail.pop(0)

    async def _spawn(
        self,
        argv: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        startup_timeout: float,
        session_id: str,
    ) -> CliSession:
        del startup_timeout  # Pi rpc mode doesn't gate on a startup handshake
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(cwd),
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        # A tiny window so the process either has its stdin pipe ready or
        # crashes outright (e.g. bad model id).
        await asyncio.sleep(0.5)
        if proc.returncode is not None:
            stdout = b""
            if proc.stdout is not None:
                stdout = await proc.stdout.read()
            raise PiStartupError(
                f"Pi exited rc={proc.returncode} during start: "
                f"{stdout.decode('utf-8', errors='replace')[:400]}"
            )
        output_tail: list[str] = []
        drain_task = asyncio.create_task(
            _drain_stdout(proc, output_tail, session_id), name=f"pi-drain-{session_id}"
        )
        self._running[session_id] = _Running(
            proc=proc,
            session_id=session_id,
            drain_task=drain_task,
            output_tail=output_tail,
        )
        log.info("pi.spawned", session_id=session_id, pid=proc.pid)
        return CliSession(session_id=session_id, pid=proc.pid)

    def _require(self, session: CliSession) -> _Running:
        running = self._running.get(session.session_id)
        if running is None:
            raise AdapterError(f"Pi session {session.session_id} is not tracked")
        return running


async def _drain_stdout(
    proc: asyncio.subprocess.Process,
    output_tail: list[str],
    session_id: str,
) -> None:
    """Keep Pi's stdout pipe draining; capture a rolling tail for stream_output()."""
    stdout = proc.stdout
    if stdout is None:
        return
    try:
        async for raw in stdout:
            line = raw.decode("utf-8", errors="replace").rstrip("\n")
            if not line:
                continue
            output_tail.append(line)
            if len(output_tail) > 200:
                del output_tail[: len(output_tail) - 200]
            # Surface high-signal events; everything else stays in the tail.
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = msg.get("type")
            if kind in {"agent_start", "agent_end", "turn_start", "turn_end"}:
                log.debug("pi.event", session_id=session_id, type=kind)
            elif kind == "response" and not msg.get("success", True):
                log.warning(
                    "pi.command_failed",
                    session_id=session_id,
                    command=msg.get("command"),
                    error=msg.get("error"),
                )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        log.warning("pi.drain.error", session_id=session_id, exc=str(exc))
