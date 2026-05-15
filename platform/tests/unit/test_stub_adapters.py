"""Stub adapters: construct cleanly, raise AdapterNotImplementedError on use, satisfy Protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from conclave_platform.adapters import (
    AdapterNotImplementedError,
    BusAdapter,
    CIAdapter,
    DocsAdapter,
    LogAdapter,
    NotifyAdapter,
    RepoAdapter,
    RuntimeAdapter,
    TraceAdapter,
)
from conclave_platform.adapters.bus import RedisStreamsBus
from conclave_platform.adapters.ci import GitLabCI
from conclave_platform.adapters.docs import ObsidianVaultDocs
from conclave_platform.adapters.log import LokiLog
from conclave_platform.adapters.notify import EmailNotify
from conclave_platform.adapters.repo import GitLabRepo
from conclave_platform.adapters.runtime import K3dTerraformRuntime
from conclave_platform.adapters.trace import LinkerdTrace


def _redis() -> RedisStreamsBus:
    return RedisStreamsBus(url="redis://localhost:6379")


def _k3d() -> K3dTerraformRuntime:
    return K3dTerraformRuntime(cluster_name="conclave", terraform_dir=Path("/tmp/tf"))


def _gitlab_repo() -> GitLabRepo:
    return GitLabRepo(workdir=Path("/tmp/wd"), project_id=1, token="t")


def _gitlab_ci() -> GitLabCI:
    return GitLabCI(project_id=1, token="t")


def _obsidian() -> ObsidianVaultDocs:
    return ObsidianVaultDocs(vault_path=Path("/tmp/vault"))


def _linkerd() -> LinkerdTrace:
    return LinkerdTrace(viz_url="http://linkerd-viz:8084")


def _loki() -> LokiLog:
    return LokiLog(loki_url="http://loki:3100", grafana_url="http://grafana:3000")


def _email() -> EmailNotify:
    return EmailNotify(
        smtp_host="smtp.example.com",
        smtp_port=587,
        username="u",
        password="p",
        from_addr="from@example.com",
        to_addr="to@example.com",
    )


@pytest.mark.parametrize(
    ("factory", "protocol"),
    [
        (_redis, BusAdapter),
        (_k3d, RuntimeAdapter),
        (_gitlab_repo, RepoAdapter),
        (_gitlab_ci, CIAdapter),
        (_obsidian, DocsAdapter),
        (_linkerd, TraceAdapter),
        (_loki, LogAdapter),
        (_email, NotifyAdapter),
    ],
)
def test_stub_constructs_and_satisfies_protocol(
    factory: Any,
    protocol: type,
) -> None:
    instance = factory()
    assert isinstance(instance, protocol)


@pytest.mark.asyncio
async def test_redis_streams_bus_raises() -> None:
    bus = _redis()
    with pytest.raises(AdapterNotImplementedError):
        await bus.connect()
    with pytest.raises(AdapterNotImplementedError):
        await bus.publish("t", b"x")
    with pytest.raises(AdapterNotImplementedError):
        await bus.request("t", b"x", timeout=1.0)


@pytest.mark.asyncio
async def test_k3d_runtime_raises() -> None:
    rt = _k3d()
    with pytest.raises(AdapterNotImplementedError):
        await rt.ensure_pod("pod", image="img", env={}, mounts=[])
    with pytest.raises(AdapterNotImplementedError):
        await rt.list_pods()


@pytest.mark.asyncio
async def test_gitlab_repo_raises() -> None:
    repo = _gitlab_repo()
    with pytest.raises(AdapterNotImplementedError):
        await repo.ensure_branch("b")
    with pytest.raises(AdapterNotImplementedError):
        await repo.open_pr(title="t", body="b", head="h")


@pytest.mark.asyncio
async def test_gitlab_ci_raises() -> None:
    ci = _gitlab_ci()
    with pytest.raises(AdapterNotImplementedError):
        await ci.ensure_workflow("pod", template="")
    with pytest.raises(AdapterNotImplementedError):
        await ci.last_run("pod")


@pytest.mark.asyncio
async def test_obsidian_docs_raises() -> None:
    docs = _obsidian()
    with pytest.raises(AdapterNotImplementedError):
        await docs.write_adr(title="t", body="b", affected_pods=[])
    with pytest.raises(AdapterNotImplementedError):
        await docs.search("q")


@pytest.mark.asyncio
async def test_linkerd_trace_raises() -> None:
    trace = _linkerd()
    with pytest.raises(AdapterNotImplementedError):
        await trace.start()
    with pytest.raises(AdapterNotImplementedError):
        async for _ in trace.stream():
            pass


@pytest.mark.asyncio
async def test_loki_log_raises() -> None:
    log = _loki()
    with pytest.raises(AdapterNotImplementedError):
        await log.start()
    with pytest.raises(AdapterNotImplementedError):
        async for _ in log.stream("pod"):
            pass


@pytest.mark.asyncio
async def test_email_notify_raises() -> None:
    notify = _email()
    with pytest.raises(AdapterNotImplementedError):
        await notify.notify("hello")
