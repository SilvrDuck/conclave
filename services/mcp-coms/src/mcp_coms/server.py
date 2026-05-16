"""FastMCP server: coms (councils + DMs)."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from conclave_core import Bus
from conclave_core import pool as conclave_pool
from conclave_core.models import AUGUSTUS
from fastmcp import Context, FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from mcp_coms.service import ComsService

log = logging.getLogger("mcp-coms")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def nats_url() -> str:
    return os.environ.get("NATS_URL", "nats://localhost:4222")


@asynccontextmanager
async def lifespan(server: FastMCP):
    async with conclave_pool(schema="council", min_size=1, max_size=5) as pool:
        async with Bus.connect(nats_url()) as bus:
            service = ComsService(pool=pool, bus=bus)

            async def on_send_dm_cmd(data: dict[str, Any]) -> None:
                try:
                    await service.dm(
                        from_pod=AUGUSTUS,
                        to_pod=data["pod_id"],
                        body=data["body"],
                    )
                except Exception:
                    log.exception("SendDirectMessage cmd handler failed")

            await bus.subscribe(
                "conclave.commands.council.SendDirectMessage",
                on_send_dm_cmd,
                durable="mcp-coms-dm",
            )
            yield {"service": service}


mcp = FastMCP(name="conclave-coms", lifespan=lifespan)


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _service(ctx: Context | None) -> ComsService:
    assert ctx is not None
    return ctx.request_context.lifespan_context["service"]


@mcp.tool
async def convene_council(
    topic: str,
    participants: list[str],
    private: bool = False,
    needs_augustus: bool = False,
    ctx: Context | None = None,
) -> dict[str, str]:
    """Open a new council (multi-agent thread). Returns the new council_id."""
    council_id = await _service(ctx).convene_council(
        topic=topic,
        participants=participants,
        private=private,
        needs_augustus=needs_augustus,
    )
    return {"council_id": council_id}


@mcp.tool
async def post_message(
    council_id: str,
    from_pod: str,
    body: str,
    ctx: Context | None = None,
) -> dict[str, int]:
    """Append a message to a council. Returns the new sequence number."""
    seq = await _service(ctx).post_message(
        council_id=council_id, from_pod=from_pod, body=body
    )
    return {"seq": seq}


@mcp.tool
async def close_council(
    council_id: str,
    summary: str,
    decision_id: str | None = None,
    ctx: Context | None = None,
) -> dict[str, str]:
    """Close a council with a one-paragraph summary (will become an ADR body)."""
    await _service(ctx).close_council(
        council_id=council_id, summary=summary, decision_id=decision_id
    )
    return {"status": "closed"}


@mcp.tool
async def dm(
    from_pod: str,
    to_pod: str,
    body: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Send a DM. Opens or reuses a 2-party private council; appends the message."""
    return await _service(ctx).dm(from_pod=from_pod, to_pod=to_pod, body=body)


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(transport="http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
