"""k3d + Terraform RuntimeAdapter — stub for alpha."""

from __future__ import annotations

from pathlib import Path

from ..base import AdapterNotImplementedError, Mount
from .base import PodStatus

_MSG = "k3d/Terraform runtime not wired in alpha"


class K3dTerraformRuntime:
    def __init__(self, cluster_name: str, terraform_dir: Path) -> None:
        self._cluster_name = cluster_name
        self._terraform_dir = terraform_dir

    async def ensure_pod(
        self,
        pod_name: str,
        *,
        image: str,
        env: dict[str, str],
        mounts: list[Mount],
    ) -> None:
        raise AdapterNotImplementedError(_MSG)

    async def stop_pod(self, pod_name: str) -> None:
        raise AdapterNotImplementedError(_MSG)

    async def pod_status(self, pod_name: str) -> PodStatus:
        raise AdapterNotImplementedError(_MSG)

    async def list_pods(self) -> list[str]:
        raise AdapterNotImplementedError(_MSG)
