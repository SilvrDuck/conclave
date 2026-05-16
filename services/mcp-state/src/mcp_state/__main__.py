"""Stub entry point: minimal HTTP server with /healthz so compose can start.

Replaced by the FastMCP server in feat/mcp-state.
"""

from __future__ import annotations

import logging
import os

import uvicorn
from fastapi import FastAPI

log = logging.getLogger("mcp-state")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="conclave-mcp-state")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "mcp-state"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
