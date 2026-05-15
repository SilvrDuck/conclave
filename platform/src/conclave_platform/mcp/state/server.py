"""state MCP — read-only system view. Thin client over the observer."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog
from fastmcp import FastMCP

log = structlog.get_logger(__name__)


@dataclass
class StateDeps:
    observer: httpx.AsyncClient


def build_mcp(deps: StateDeps) -> FastMCP:
    mcp: FastMCP = FastMCP(name="conclave-state", version="0.1.0")

    @mcp.tool
    async def members() -> list[dict[str, object]]:
        """List all known members + their status (admitted | proposed | exiled)."""
        r = await deps.observer.get("/state/members")
        r.raise_for_status()
        return list(r.json().get("members", []))

    @mcp.tool
    async def endpoints(pod_name: str) -> list[dict[str, object]]:
        """List the observed endpoints for `pod_name`, with any current annotations."""
        r = await deps.observer.get(f"/state/endpoints/{pod_name}")
        r.raise_for_status()
        return list(r.json().get("endpoints", []))

    @mcp.tool
    async def callers_of(method: str, path: str) -> list[str]:
        """Pods observed to call this endpoint."""
        r = await deps.observer.get(
            "/state/callers", params={"method": method, "path": path}
        )
        r.raise_for_status()
        return list(r.json().get("callers", []))

    @mcp.tool
    async def chatrooms() -> list[dict[str, object]]:
        """List active chatrooms — id, topic, participants, last_active."""
        r = await deps.observer.get("/state/chatrooms")
        r.raise_for_status()
        return list(r.json().get("chatrooms", []))

    @mcp.tool
    async def agenda(pod_name: str) -> dict[str, object]:
        """Snapshot of `pod_name`'s agenda (doing / next / blocked_on)."""
        r = await deps.observer.get(f"/state/agenda/{pod_name}")
        if r.status_code == 404:
            return {"error": "no such pod", "pod": pod_name}
        r.raise_for_status()
        return dict(r.json().get("snapshot", {}))

    @mcp.tool
    async def platform_info() -> dict[str, object]:
        """A truncated excerpt of conclave.config.yaml (slots + project_name)."""
        # The observer doesn't currently expose config; we just echo health.
        r = await deps.observer.get("/healthz")
        r.raise_for_status()
        return {"observer": dict(r.json())}

    return mcp


__all__ = ["StateDeps", "build_mcp"]
