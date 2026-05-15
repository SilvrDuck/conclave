"""decisions MCP — ADR write / read / search / list. Backed by DocsAdapter."""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from fastmcp import FastMCP

from ...adapters import DocsAdapter
from ...core import PodName
from ...core.ids import AdrId

log = structlog.get_logger(__name__)


@dataclass
class DecisionsDeps:
    docs: DocsAdapter


def build_mcp(deps: DecisionsDeps) -> FastMCP:
    mcp: FastMCP = FastMCP(name="conclave-decisions", version="0.1.0")

    @mcp.tool
    async def write_adr(
        title: str,
        body: str,
        affected_pods: list[str],
        proposal_id: str | None = None,
    ) -> dict[str, str]:
        """Write a new ADR. Returns {adr_id}."""
        adr_id = await deps.docs.write_adr(
            title=title,
            body=body,
            affected_pods=[PodName(p) for p in affected_pods],
            proposal_id=proposal_id,
        )
        return {"adr_id": adr_id}

    @mcp.tool
    async def read(adr_id: str) -> dict[str, object] | None:
        """Read an ADR by id. Returns the full record, or None."""
        adr = await deps.docs.read(AdrId(adr_id))
        if adr is None:
            return None
        return adr.model_dump(mode="json")

    @mcp.tool
    async def search(query: str, limit: int = 10) -> list[dict[str, object]]:
        """Full-text search across ADR titles + bodies."""
        hits = await deps.docs.search(query, limit=limit)
        return [a.model_dump(mode="json") for a in hits]

    @mcp.tool
    async def list_adrs(pod: str | None = None, limit: int = 100) -> list[dict[str, object]]:
        """List ADRs, optionally filtered to those affecting `pod`."""
        items = await deps.docs.list(
            pod=PodName(pod) if pod else None, limit=limit
        )
        return [a.model_dump(mode="json") for a in items]

    return mcp


__all__ = ["DecisionsDeps", "build_mcp"]
