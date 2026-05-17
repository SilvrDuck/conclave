"""DockerEventsWatcher — turn container die/stop into PodHealthChanged.

Spec/08 §10 R1: "within 5 s of a pod's container being killed, the
Glance graph turns its node red." Span-staleness (HealthWatcher) is a
2-min signal — far too slow. Docker's own event stream tells us
immediately.

Implementation: spawn `docker events` as a subprocess and read its
JSON line stream. Filter for container `die` / `kill` / `stop` events
where the container name starts with `conclave-pod-`. Map to pod_id
and publish `PodHealthChanged(runtime_status='stopped')` immediately.

A reciprocal `start` event flips the pod back to `running` so a
restart by Augustus is also visible in seconds rather than minutes.

Runs as a long-lived asyncio.Task in mcp-pods's lifespan.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from conclave_core import Bus
from conclave_core.events import PodHealthChanged
from conclave_core.models import PodRuntimeStatus

log = logging.getLogger("mcp-pods.docker-events")

# event Action -> resulting runtime_status. die fires on normal exit,
# kill on signal, stop on `docker stop`. We treat them all as stopped.
_STOP_ACTIONS = {"die", "kill", "stop", "oom"}
_START_ACTIONS = {"start"}

_CONTAINER_PREFIX = "conclave-pod-"


class DockerEventsWatcher:
    def __init__(self, *, bus: Bus) -> None:
        self._bus = bus
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._proc: asyncio.subprocess.Process | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="docker-events")
        log.info("docker events watcher started")

    async def stop(self) -> None:
        self._stop.set()
        if self._proc is not None:
            try:
                self._proc.terminate()
            except ProcessLookupError:
                pass
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    async def _run(self) -> None:
        # Restart the subprocess if it dies — the docker daemon could
        # be transiently unavailable.
        while not self._stop.is_set():
            try:
                await self._one_run()
            except Exception:
                log.exception("docker events subprocess crashed; restarting in 5s")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=5)
            except TimeoutError:
                continue

    async def _one_run(self) -> None:
        cmd = [
            "docker", "events",
            "--format", "{{json .}}",
            "--filter", "type=container",
        ]
        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert self._proc.stdout is not None
        async for line in self._proc.stdout:
            if self._stop.is_set():
                break
            txt = line.decode(errors="replace").strip()
            if not txt:
                continue
            try:
                ev = json.loads(txt)
            except json.JSONDecodeError:
                continue
            await self._handle(ev)
        await self._proc.wait()

    async def _handle(self, ev: dict[str, Any]) -> None:
        action = ev.get("Action")
        attrs = (ev.get("Actor") or {}).get("Attributes") or {}
        name = attrs.get("name") or ""
        if not name.startswith(_CONTAINER_PREFIX):
            return
        pod_id = name[len(_CONTAINER_PREFIX):]
        if not pod_id:
            return
        if action in _STOP_ACTIONS:
            log.info("docker event %s on %s — flipping pod to stopped", action, pod_id)
            await self._bus.publish_event(
                PodHealthChanged(
                    pod_id=pod_id,
                    runtime_status=PodRuntimeStatus.STOPPED,
                ),
                "pods",
            )
        elif action in _START_ACTIONS:
            log.info("docker event %s on %s — flipping pod to running", action, pod_id)
            await self._bus.publish_event(
                PodHealthChanged(
                    pod_id=pod_id,
                    runtime_status=PodRuntimeStatus.RUNNING,
                ),
                "pods",
            )
