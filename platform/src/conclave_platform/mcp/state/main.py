"""conclave-mcp-state — runs the state MCP over streamable HTTP."""

from __future__ import annotations

import os

import httpx
import structlog

from .server import StateDeps, build_mcp

log = structlog.get_logger(__name__)


def main() -> None:
    observer_url = os.environ.get("OBSERVER_URL", "http://observer:8000")
    port = int(os.environ.get("PORT", "8005"))
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104
    observer = httpx.AsyncClient(base_url=observer_url, timeout=10.0)
    deps = StateDeps(observer=observer)
    mcp = build_mcp(deps)
    log.info("mcp-state.start", port=port, observer=observer_url)
    mcp.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    main()
