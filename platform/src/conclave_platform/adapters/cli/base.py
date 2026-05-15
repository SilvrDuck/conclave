"""CLI runtime adapter — slot 6. Pi (wired) or Claude Code (stub).

The harness drives a CLI subprocess. Each call is bounded by a timeout (no
unbounded waits). The adapter handles the spawn / resume / send-event / sleep
semantics that differ between Pi and Claude Code.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ...core import Event


@dataclass(frozen=True, slots=True)
class CliSession:
    """Opaque handle to a running CLI process + its session id for --resume."""

    session_id: str
    pid: int


@runtime_checkable
class CliAdapter(Protocol):
    async def start(
        self,
        *,
        charter: str,
        cwd: Path,
        session_dir: Path,
        env: dict[str, str],
        startup_timeout: float,
    ) -> CliSession: ...

    async def resume(
        self,
        *,
        session: CliSession,
        cwd: Path,
        session_dir: Path,
        env: dict[str, str],
        startup_timeout: float,
    ) -> CliSession: ...

    async def deliver(self, session: CliSession, event: Event) -> None:
        """Push one event into the CLI's stdin (or via MCP, depending on impl)."""
        ...

    async def is_alive(self, session: CliSession) -> bool: ...

    async def stop(self, session: CliSession, *, timeout: float) -> None: ...

    def stream_output(self, session: CliSession) -> AsyncIterator[str]: ...
