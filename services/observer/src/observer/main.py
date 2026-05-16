"""Minimal FastAPI app — full implementation comes in feat/observer-service."""

from fastapi import FastAPI

app = FastAPI(title="conclave-observer")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
