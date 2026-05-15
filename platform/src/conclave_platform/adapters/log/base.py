"""Log adapter — slot 7b. Streams per-pod stdout to the Forum UI."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class LogAdapter(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def stream(self, pod_name: str) -> AsyncIterator[str]: ...
