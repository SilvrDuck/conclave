"""FastMCP server: decisions."""

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

from mcp_decisions.service import DecisionsService

log = logging.getLogger("mcp-decisions")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def nats_url() -> str:
    return os.environ.get("NATS_URL", "nats://localhost:4222")


@asynccontextmanager
async def lifespan(server: FastMCP):
    async with conclave_pool(schema="decisions", min_size=1, max_size=5) as pool:
        async with Bus.connect(nats_url()) as bus:
            service = DecisionsService(pool=pool, bus=bus)

            async def on_proclamation_issued(data: dict[str, Any]) -> None:
                await service.on_proclamation_issued(data)

            async def on_proposal_closed(data: dict[str, Any]) -> None:
                await service.on_proposal_closed(data)

            async def on_council_closed(data: dict[str, Any]) -> None:
                await service.on_council_closed(data)

            await bus.subscribe(
                "conclave.events.operator.ProclamationIssued",
                on_proclamation_issued,
                durable="mcp-decisions-proc",
            )
            await bus.subscribe(
                "conclave.events.senate.ProposalClosed",
                on_proposal_closed,
                durable="mcp-decisions-prop",
            )
            await bus.subscribe(
                "conclave.events.council.CouncilClosed",
                on_council_closed,
                durable="mcp-decisions-coun",
            )
            yield {"service": service}


mcp = FastMCP(name="conclave-decisions", lifespan=lifespan)


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _service(ctx: Context | None) -> DecisionsService:
    assert ctx is not None
    return ctx.request_context.lifespan_context["service"]


@mcp.tool
async def read(decision_id: str, ctx: Context | None = None) -> dict[str, Any] | None:
    """Read one decision by id."""
    return await _service(ctx).read(decision_id)


@mcp.tool(name="list")
async def list_decisions(
    status: str | None = None,
    origin_kind: str | None = None,
    limit: int = 100,
    ctx: Context | None = None,
) -> list[dict[str, Any]]:
    """List decisions, optionally filtered by status/origin_kind."""
    return await _service(ctx).list(status=status, origin_kind=origin_kind, limit=limit)


@mcp.tool
async def search(query: str, limit: int = 50, ctx: Context | None = None) -> list[dict[str, Any]]:
    """ILIKE-match against title and body."""
    return await _service(ctx).search(query=query, limit=limit)


@mcp.tool
async def seal(
    decision_id: str,
    body: str,
    affected: list[str] | None = None,
    ctx: Context | None = None,
) -> dict[str, str]:
    """Seal a placeholder decision. Rejects empty/template bodies."""
    await _service(ctx).seal(decision_id=decision_id, body=body, affected=affected)
    return {"status": "sealed"}


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(transport="http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
