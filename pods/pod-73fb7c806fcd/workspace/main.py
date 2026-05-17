"""Placeholder service the agent will rewrite.

A real pod's agent will replace this file (and surrounding workspace
contents) with whatever shape the service needs. For now it exposes
just `GET /healthz` so the pod's hostname routes correctly through
Traefik and OTel records inbound spans.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="conclave-pod-placeholder")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    import os
    return {
        "pod_id": os.environ.get("POD_ID", "unknown"),
        "display_role": os.environ.get("DISPLAY_ROLE", "unnamed"),
        "note": "Agent has not yet rewritten this workspace.",
    }
