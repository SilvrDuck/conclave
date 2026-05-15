"""Stdout LogAdapter — tails `docker logs -f <pod>`.

Pragmatic for Compose: each pod is a container, `docker logs --since=0 -f` gives
the full stream. For k3d/k8s this would be `kubectl logs -f`; that variant
ships with the k3d runtime adapter when implemented.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import structlog

log = structlog.get_logger(__name__)


class StdoutTailLog:
    def __init__(self, *, container_prefix: str = "conclave-") -> None:
        self._prefix = container_prefix
        self._procs: dict[str, asyncio.subprocess.Process] = {}

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        for proc in self._procs.values():
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except TimeoutError:
                    proc.kill()
        self._procs.clear()

    async def stream(self, pod_name: str) -> AsyncIterator[str]:
        container = f"{self._prefix}{pod_name}"
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "logs",
            "-f",
            "--since",
            "0",
            container,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        self._procs[pod_name] = proc
        assert proc.stdout is not None
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                yield line.decode("utf-8", errors="replace").rstrip("\n")
        finally:
            if proc.returncode is None:
                proc.terminate()
            self._procs.pop(pod_name, None)
