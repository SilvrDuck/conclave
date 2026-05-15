"""Runtime / IaC adapter — slot 1.

Owns the lifecycle of pod containers and the supporting services (bus, observer,
MCP servers). Wired in alpha: Docker Compose. Stubbed: Terraform-k3d.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from ..base import Mount


class PodStatus(StrEnum):
    running = "running"
    stopped = "stopped"
    missing = "missing"


@runtime_checkable
class RuntimeAdapter(Protocol):
    async def ensure_pod(
        self,
        pod_name: str,
        *,
        image: str,
        env: dict[str, str],
        mounts: list[Mount],
    ) -> None: ...

    async def stop_pod(self, pod_name: str) -> None: ...

    async def pod_status(self, pod_name: str) -> PodStatus: ...

    async def list_pods(self) -> list[str]: ...
