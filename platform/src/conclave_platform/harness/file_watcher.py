"""Polling file watcher. Calls a handler when mtime changes; debounces writes."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)


async def watch(
    path: Path,
    handler: Callable[[str], Awaitable[None]],
    *,
    interval: float = 1.0,
    stop: asyncio.Event | None = None,
) -> None:
    """Poll `path` mtime; on change, read it and invoke handler(content)."""
    last_mtime: float | None = None
    while True:
        if stop is not None and stop.is_set():
            return
        try:
            if path.exists():
                mtime = path.stat().st_mtime
                if last_mtime is None or mtime != last_mtime:
                    last_mtime = mtime
                    try:
                        content = path.read_text(encoding="utf-8")
                    except OSError as exc:
                        log.warning("watcher.read_failed", path=str(path), exc=str(exc))
                    else:
                        try:
                            await handler(content)
                        except Exception as exc:
                            log.warning(
                                "watcher.handler_failed", path=str(path), exc=str(exc)
                            )
        except OSError as exc:
            log.warning("watcher.stat_failed", path=str(path), exc=str(exc))
        await asyncio.sleep(interval)


__all__ = ["watch"]
