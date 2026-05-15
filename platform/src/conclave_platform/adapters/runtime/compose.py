"""Docker Compose RuntimeAdapter — slot 1 alpha implementation.

Maintains an `infra/compose.yaml` file as the source of truth for pod
services, mutating it on every ensure_pod / stop_pod. Each pod is one
service named after the pod, with container name `conclave-<pod>` so it
lines up with the stdout LogAdapter's default prefix. All `docker`
shell-outs run through asyncio.subprocess with explicit hard timeouts.
"""

from __future__ import annotations

import asyncio
import shlex
from pathlib import Path
from typing import Any, cast

import structlog
import yaml

from ..base import AdapterError, Mount
from .base import PodStatus

log = structlog.get_logger(__name__)

_DEFAULT_UP_TIMEOUT = 60.0
_DEFAULT_DOWN_TIMEOUT = 10.0
_DEFAULT_INSPECT_TIMEOUT = 5.0

_CONTAINER_PREFIX = "conclave-"
_PROJECT_NAME = "conclave"
_NETWORK_NAME = "conclave"


class ComposeCommandError(AdapterError):
    pass


def _empty_compose() -> dict[str, Any]:
    return {
        "services": {},
        "networks": {_NETWORK_NAME: {"driver": "bridge"}},
    }


def _service_def(
    pod_name: str,
    *,
    image: str,
    env: dict[str, str],
    mounts: list[Mount],
) -> dict[str, Any]:
    volumes = [f"{m.host_path}:{m.container_path}:{m.mode.value}" for m in mounts]
    return {
        "image": image,
        "container_name": f"{_CONTAINER_PREFIX}{pod_name}",
        "environment": dict(env),
        "volumes": volumes,
        "restart": "unless-stopped",
        "networks": [_NETWORK_NAME],
    }


class DockerComposeRuntime:
    def __init__(
        self,
        *,
        compose_path: Path,
        up_timeout: float = _DEFAULT_UP_TIMEOUT,
        down_timeout: float = _DEFAULT_DOWN_TIMEOUT,
        inspect_timeout: float = _DEFAULT_INSPECT_TIMEOUT,
    ) -> None:
        self._path = compose_path
        self._up_timeout = up_timeout
        self._down_timeout = down_timeout
        self._inspect_timeout = inspect_timeout
        self._lock = asyncio.Lock()

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return _empty_compose()
        raw = yaml.safe_load(self._path.read_text()) or {}
        if not isinstance(raw, dict):
            raise ComposeCommandError(f"compose file {self._path} is not a mapping")
        raw.setdefault("services", {})
        raw.setdefault("networks", {_NETWORK_NAME: {"driver": "bridge"}})
        return cast(dict[str, Any], raw)

    def _dump(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(yaml.safe_dump(data, sort_keys=True))

    async def _run(self, cmd: list[str], *, timeout: float) -> tuple[int, str, str]:
        log.debug("compose.run", cmd=" ".join(shlex.quote(a) for a in cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError as e:
            proc.kill()
            await proc.wait()
            raise ComposeCommandError(f"{' '.join(cmd)} timed out after {timeout}s") from e
        rc = proc.returncode or 0
        return rc, stdout_b.decode("utf-8", errors="replace"), stderr_b.decode(
            "utf-8", errors="replace"
        )

    async def ensure_pod(
        self,
        pod_name: str,
        *,
        image: str,
        env: dict[str, str],
        mounts: list[Mount],
    ) -> None:
        service = _service_def(pod_name, image=image, env=env, mounts=mounts)
        async with self._lock:
            data = self._load()
            data["services"][pod_name] = service
            self._dump(data)
        rc, _, stderr = await self._run(
            [
                "docker",
                "compose",
                "-f",
                str(self._path),
                "-p",
                _PROJECT_NAME,
                "up",
                "-d",
                "--no-recreate",
                pod_name,
            ],
            timeout=self._up_timeout,
        )
        if rc != 0:
            raise ComposeCommandError(f"compose up {pod_name} failed: {stderr.strip()}")

    async def stop_pod(self, pod_name: str) -> None:
        rc, _, stderr = await self._run(
            [
                "docker",
                "compose",
                "-f",
                str(self._path),
                "-p",
                _PROJECT_NAME,
                "rm",
                "-sf",
                pod_name,
            ],
            timeout=self._down_timeout,
        )
        if rc != 0:
            raise ComposeCommandError(f"compose rm {pod_name} failed: {stderr.strip()}")
        async with self._lock:
            data = self._load()
            data["services"].pop(pod_name, None)
            self._dump(data)

    async def pod_status(self, pod_name: str) -> PodStatus:
        rc, stdout, _ = await self._run(
            ["docker", "inspect", "-f", "{{.State.Status}}", f"{_CONTAINER_PREFIX}{pod_name}"],
            timeout=self._inspect_timeout,
        )
        if rc != 0:
            return PodStatus.missing
        return PodStatus.running if stdout.strip() == "running" else PodStatus.stopped

    async def list_pods(self) -> list[str]:
        async with self._lock:
            data = self._load()
        services = data.get("services") or {}
        return sorted(services.keys())
