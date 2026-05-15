"""Claude Code CliAdapter — stub.

The alpha wires Pi only. This stub satisfies the "two impls per slot" rule and
raises at every entry point so a misconfigured wizard fails loud, not late.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...core import Event
from ..base import AdapterNotImplementedError
from .base import CliSession

_MSG = "ClaudeCode adapter not wired in alpha"


@dataclass(slots=True)
class ClaudeCodeCli:
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    async def start(
        self,
        *,
        charter: str,
        cwd: Path,
        session_dir: Path,
        env: dict[str, str],
        startup_timeout: float,
    ) -> CliSession:
        raise AdapterNotImplementedError(_MSG)

    async def resume(
        self,
        *,
        session: CliSession,
        cwd: Path,
        session_dir: Path,
        env: dict[str, str],
        startup_timeout: float,
    ) -> CliSession:
        raise AdapterNotImplementedError(_MSG)

    async def deliver(self, session: CliSession, event: Event) -> None:
        raise AdapterNotImplementedError(_MSG)

    async def is_alive(self, session: CliSession) -> bool:
        raise AdapterNotImplementedError(_MSG)

    async def stop(self, session: CliSession, *, timeout: float) -> None:
        raise AdapterNotImplementedError(_MSG)

    def stream_output(self, session: CliSession) -> AsyncIterator[str]:
        raise AdapterNotImplementedError(_MSG)
