"""FastMCP server: pods. Pod lifecycle + traefik writer + image-swap proposal."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from conclave_core import Bus
from conclave_core import pool as conclave_pool
from fastmcp import Context, FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from mcp_pods.service import PodsService
from mcp_pods.spawner import build_template_image

log = logging.getLogger("mcp-pods")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def nats_url() -> str:
    return os.environ.get("NATS_URL", "nats://localhost:4222")


@asynccontextmanager
async def lifespan(server: FastMCP):
    async with conclave_pool(schema="pods", min_size=1, max_size=5) as pool:
        async with Bus.connect(nats_url()) as bus:
            service = PodsService(pool=pool, bus=bus)
            # Pre-build the pod-template image so SpawnFirstPod can bring
            # a pod up in seconds (no docker build on the critical path
            # of spec/08 §2's 5s budget).
            try:
                await build_template_image()
            except Exception:
                log.exception(
                    "template image pre-build failed; SpawnFirstPod will "
                    "still try, but the first spawn will be slow"
                )

            async def on_proposal_closed(data: dict[str, Any]) -> None:
                await service.on_proposal_closed(data)

            async def on_pod_exited(data: dict[str, Any]) -> None:
                await service.on_pod_exited(data)

            async def on_proclamation_issued(data: dict[str, Any]) -> None:
                await service.on_proclamation_issued(data)

            async def on_pod_admitted(data: dict[str, Any]) -> None:
                await service.on_pod_admitted(data)

            async def on_restart_pod(data: dict[str, Any]) -> None:
                await service.on_restart_pod(data)

            async def on_nuke_pods(data: dict[str, Any]) -> None:
                await service.on_nuke_pods(data)

            await bus.subscribe(
                "conclave.events.senate.ProposalClosed",
                on_proposal_closed,
                durable="mcp-pods-prop-closed",
            )
            await bus.subscribe(
                "conclave.events.pods.PodExited",
                on_pod_exited,
                durable="mcp-pods-exit",
            )
            await bus.subscribe(
                "conclave.events.operator.ProclamationIssued",
                on_proclamation_issued,
                durable="mcp-pods-spawn-first",
            )
            await bus.subscribe(
                "conclave.events.pods.PodAdmitted",
                on_pod_admitted,
                durable="mcp-pods-broadcast-membership",
            )
            await bus.subscribe(
                "conclave.commands.pods.RestartPod",
                on_restart_pod,
                durable="mcp-pods-restart",
            )
            await bus.subscribe(
                "conclave.commands.pods.NukePods",
                on_nuke_pods,
                durable="mcp-pods-nuke",
            )
            yield {"service": service}


mcp = FastMCP(name="conclave-pods", lifespan=lifespan)


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _service(ctx: Context | None) -> PodsService:
    assert ctx is not None
    return ctx.request_context.lifespan_context["service"]


@mcp.tool
async def register_self(
    pod_id: str | None,
    display_role: str,
    image_strategy: str = "code",
    main_image: str | None = None,
    charter_path: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Announce a pod to the platform. \`pod_id\` is stable; if None, the
    platform mints one and returns it. Idempotent on the same id."""
    return await _service(ctx).register_self(
        pod_id=pod_id,
        display_role=display_role,
        image_strategy=image_strategy,
        main_image=main_image,
        charter_path=charter_path,
    )


@mcp.tool
async def rename_self(
    pod_id: str,
    new_display_role: str,
    ctx: Context | None = None,
) -> dict[str, str]:
    """Change a pod's display_role. Stable pod_id is unaffected."""
    await _service(ctx).rename_self(pod_id=pod_id, new_display_role=new_display_role)
    return {"status": "renamed"}


@mcp.tool
async def list_pods(ctx: Context | None = None) -> list[dict[str, Any]]:
    """List every pod the platform knows about (admitted or not)."""
    return await _service(ctx).list_pods()


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(transport="http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
