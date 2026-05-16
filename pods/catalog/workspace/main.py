"""Catalog service — track metadata for the music UI.

Provides a tiny library of demo tracks. The audio URL points to a
public-domain Wikipedia commons sample; in a real run an agent would
wire up a richer source.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

app = FastAPI(title="conclave-catalog")

AUDIO = "https://upload.wikimedia.org/wikipedia/commons/0/01/Onestepforward.ogg"

TRACKS = [
    {"id": "t1", "title": "Imperial March (8-bit)", "artist": "The Sortition Boys",
     "duration_s": 32, "audio_url": AUDIO},
    {"id": "t2", "title": "Bus Tap Blues", "artist": "Postgres & The Replicas",
     "duration_s": 28, "audio_url": AUDIO},
    {"id": "t3", "title": "Quorum Reached", "artist": "Consensus Omnium",
     "duration_s": 24, "audio_url": AUDIO},
]


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "pod": os.environ.get("POD_ID", "?")}


@app.get("/tracks")
async def list_tracks() -> list[dict]:
    return TRACKS


@app.get("/tracks/{track_id}")
async def get_track(track_id: str) -> dict:
    for t in TRACKS:
        if t["id"] == track_id:
            return t
    raise HTTPException(status_code=404, detail=f"unknown track {track_id}")
