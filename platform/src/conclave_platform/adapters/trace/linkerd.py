"""Linkerd TraceAdapter — stub for alpha. See `otel_tempo` for the wired pair."""

from __future__ import annotations

from collections.abc import AsyncIterator

from ..base import AdapterNotImplementedError
from .base import SpanEvent

_MSG = "Linkerd trace not wired in alpha"


class LinkerdTrace:
    def __init__(self, viz_url: str) -> None:
        self._viz_url = viz_url

    async def start(self) -> None:
        raise AdapterNotImplementedError(_MSG)

    async def stop(self) -> None:
        raise AdapterNotImplementedError(_MSG)

    async def stream(self) -> AsyncIterator[SpanEvent]:
        raise AdapterNotImplementedError(_MSG)
        yield
