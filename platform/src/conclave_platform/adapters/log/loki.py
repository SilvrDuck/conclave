"""Loki LogAdapter — stub for alpha. See `stdout` for the wired pair."""

from __future__ import annotations

from collections.abc import AsyncIterator

from ..base import AdapterNotImplementedError

_MSG = "Loki log not wired in alpha"


class LokiLog:
    def __init__(self, loki_url: str, grafana_url: str) -> None:
        self._loki_url = loki_url
        self._grafana_url = grafana_url

    async def start(self) -> None:
        raise AdapterNotImplementedError(_MSG)

    async def stop(self) -> None:
        raise AdapterNotImplementedError(_MSG)

    async def stream(self, pod_name: str) -> AsyncIterator[str]:
        raise AdapterNotImplementedError(_MSG)
        yield
