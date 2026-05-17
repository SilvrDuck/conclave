"""FastMCP server: state. Read-only proxy onto the observer's HTTP API.

Pod agents call these tools to learn about the running system without
having to know the observer's URL shape. Every tool maps 1:1 to an
observer read endpoint.

Spec ref: spec/05-ddd-contexts.md §C5 aggregates → MCP tools.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastmcp import Context, FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

log = logging.getLogger("mcp-state")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def observer_url() -> str:
    return os.environ.get("OBSERVER_URL", "http://observer:8000")


@asynccontextmanager
async def lifespan(server: FastMCP):
    async with httpx.AsyncClient(
        base_url=observer_url(), timeout=10.0
    ) as client:
        yield {"client": client}


mcp = FastMCP(name="conclave-state", lifespan=lifespan)


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _client(ctx: Context | None) -> httpx.AsyncClient:
    assert ctx is not None
    return ctx.request_context.lifespan_context["client"]


async def _get(ctx: Context | None, path: str, **params: Any) -> Any:
    r = await _client(ctx).get(path, params=params)
    r.raise_for_status()
    return r.json()


# ─── tools ───────────────────────────────────────────────────────────────


@mcp.tool
async def members(ctx: Context | None = None) -> list[dict[str, Any]]:
    """List every pod the observer knows about, with runtime + admit state."""
    return await _get(ctx, "/state/pods")


@mcp.tool
async def proclamations(ctx: Context | None = None) -> list[dict[str, Any]]:
    """List proclamations issued by Augustus, newest first."""
    return await _get(ctx, "/state/proclamations")


@mcp.tool
async def proposals(ctx: Context | None = None) -> list[dict[str, Any]]:
    """List the most recent 100 proposals with their ballots."""
    return await _get(ctx, "/state/proposals")


@mcp.tool
async def councils(ctx: Context | None = None) -> list[dict[str, Any]]:
    """List the most recent 100 councils."""
    return await _get(ctx, "/state/councils")


@mcp.tool
async def council_messages(
    council_id: str,
    ctx: Context | None = None,
) -> list[dict[str, Any]]:
    """Return the ordered messages of one council."""
    return await _get(ctx, f"/state/councils/{council_id}/messages")


@mcp.tool
async def decisions(ctx: Context | None = None) -> list[dict[str, Any]]:
    """List recent decisions (placeholder + sealed)."""
    return await _get(ctx, "/state/decisions")


@mcp.tool
async def endpoints(
    pod_id: str | None = None,
    ctx: Context | None = None,
) -> list[dict[str, Any]]:
    """List observed endpoints for a pod (or all pods)."""
    return await _get(ctx, "/state/endpoints", **({"pod_id": pod_id} if pod_id else {}))


@mcp.tool
async def calls(since_seconds: int = 60, ctx: Context | None = None) -> list[dict[str, Any]]:
    """List the last `since_seconds` worth of observed pod-to-pod calls."""
    return await _get(ctx, "/state/calls", since_seconds=since_seconds)


@mcp.tool
async def callers_of(
    pod_id: str,
    since_seconds: int = 60,
    ctx: Context | None = None,
) -> list[str]:
    """Distinct pods that called `pod_id` in the recent window."""
    rows = await _get(ctx, "/state/calls", since_seconds=since_seconds)
    return sorted({r["src_pod"] for r in rows if r.get("dst_pod") == pod_id})


@mcp.tool
async def calls_to(
    pod_id: str,
    since_seconds: int = 60,
    ctx: Context | None = None,
) -> list[str]:
    """Distinct pods that `pod_id` called in the recent window."""
    rows = await _get(ctx, "/state/calls", since_seconds=since_seconds)
    return sorted({r["dst_pod"] for r in rows if r.get("src_pod") == pod_id})


@mcp.tool
async def inbox(ctx: Context | None = None) -> list[dict[str, Any]]:
    """Augustus's inbox: open ballots + stuck pods + needs-augustus councils."""
    return await _get(ctx, "/inbox")


@mcp.tool
async def activity(limit: int = 200, ctx: Context | None = None) -> list[dict[str, Any]]:
    """The named-events activity feed; default last 200."""
    return await _get(ctx, "/state/activity", limit=limit)


@mcp.tool
async def traces(
    pod_id: str, limit: int = 20, ctx: Context | None = None
) -> dict[str, Any]:
    """Recent OTel traces involving `pod_id`. Returns a list of trace
    summaries (`trace_id`, `root_service_name`, `start_time`,
    `duration_ms`). Spec/05 §C5 mandates a `traces` surface on the
    state aggregate; this is it."""
    return await _get(ctx, "/state/traces", pod_id=pod_id, limit=limit)


@mcp.tool
async def trace(trace_id: str, ctx: Context | None = None) -> dict[str, Any]:
    """Full span tree for `trace_id`. Use after `traces` returned a
    summary you want to walk."""
    return await _get(ctx, f"/state/traces/{trace_id}")


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(transport="http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
