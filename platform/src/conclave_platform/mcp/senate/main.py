"""conclave-mcp-senate — runs the senate MCP over streamable HTTP."""

from __future__ import annotations

import os

import httpx
import structlog

from .server import SenateDeps, build_mcp

log = structlog.get_logger(__name__)


def main() -> None:
    senate_url = os.environ.get("SENATE_URL", "http://senate-ledger:8001")
    port = int(os.environ.get("PORT", "8003"))
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104
    senate = httpx.AsyncClient(base_url=senate_url, timeout=15.0)
    deps = SenateDeps(senate=senate)
    mcp = build_mcp(deps)
    log.info("mcp-senate.start", port=port, senate=senate_url)
    mcp.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    main()
