"""Jam service — shared listening rooms."""

from __future__ import annotations

import os
import secrets
import time
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="conclave-jam")

_jams: dict[str, dict[str, Any]] = {}


class CreateJam(BaseModel):
    track_id: str
    host: str


class JoinJam(BaseModel):
    listener: str


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "pod": os.environ.get("POD_ID", "?")}


@app.post("/jam")
async def create_jam(req: CreateJam) -> dict:
    jam_id = f"j-{secrets.token_hex(3)}"
    _jams[jam_id] = {
        "id": jam_id,
        "track_id": req.track_id,
        "started_at": time.time(),
        "host": req.host,
        "listeners": [req.host],
    }
    return _jams[jam_id]


@app.get("/jam/{jam_id}")
async def get_jam(jam_id: str) -> dict:
    jam = _jams.get(jam_id)
    if not jam:
        raise HTTPException(404, "unknown jam")
    elapsed = time.time() - jam["started_at"]
    return {**jam, "playhead_s": round(elapsed, 2)}


@app.post("/jam/{jam_id}/join")
async def join_jam(jam_id: str, req: JoinJam) -> dict:
    jam = _jams.get(jam_id)
    if not jam:
        raise HTTPException(404, "unknown jam")
    if req.listener not in jam["listeners"]:
        jam["listeners"].append(req.listener)
    return jam


@app.get("/jams")
async def list_jams() -> list[dict]:
    return list(_jams.values())
