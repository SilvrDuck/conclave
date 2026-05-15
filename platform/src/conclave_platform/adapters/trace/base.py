"""Trace adapter — slot 7a. Feeds observer's call-graph projection."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from ...core import PodName


@dataclass(frozen=True, slots=True)
class SpanEvent:
    caller: PodName
    callee: PodName
    method: str
    path: str
    status_code: int
    duration_ms: float
    at: datetime


@runtime_checkable
class TraceAdapter(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def stream(self) -> AsyncIterator[SpanEvent]: ...
