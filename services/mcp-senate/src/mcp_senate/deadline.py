"""Deadline closer reactor. Runs in the senate process; closes overdue."""

from __future__ import annotations

import asyncio
import logging

from mcp_senate.service import SenateService

log = logging.getLogger("mcp-senate.deadline")

TICK = 10  # seconds


class DeadlineCloser:
    def __init__(self, *, service: SenateService) -> None:
        self._service = service
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _run(self) -> None:
        log.info("deadline closer started")
        while not self._stop.is_set():
            try:
                closed = await self._service.close_overdue()
                if closed:
                    log.info("closed %d overdue proposals", closed)
            except Exception:
                log.exception("deadline tick failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=TICK)
            except TimeoutError:
                pass
