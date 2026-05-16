"""Lyrics service — timed lyric lines per track."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

app = FastAPI(title="conclave-lyrics")

LYRICS: dict[str, list[dict]] = {
    "t1": [
        {"at_s": 0, "line": "Da-dun-da, da-dun-dun-dun…"},
        {"at_s": 4, "line": "Empire's coming down the wire,"},
        {"at_s": 8, "line": "Sortition swaps the regime."},
        {"at_s": 12, "line": "Supermajority of bytes,"},
        {"at_s": 16, "line": "Vote it in or vote it out —"},
        {"at_s": 20, "line": "The pods keep marching on."},
    ],
    "t2": [
        {"at_s": 0, "line": "I tapped the bus and it tapped me back,"},
        {"at_s": 6, "line": "Sealed a decision, never looked back."},
        {"at_s": 12, "line": "Postgres in the corner, replicas in tow,"},
        {"at_s": 18, "line": "Where's the data? Only WAL knows."},
    ],
    "t3": [
        {"at_s": 0, "line": "We reached the quorum, raise a glass,"},
        {"at_s": 6, "line": "Every voter said yes at last."},
        {"at_s": 12, "line": "Consensus omnium, here we go,"},
        {"at_s": 18, "line": "ADR sealed in the afterglow."},
    ],
}


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "pod": os.environ.get("POD_ID", "?")}


@app.get("/lyrics/{track_id}")
async def get_lyrics(track_id: str) -> list[dict]:
    if track_id not in LYRICS:
        raise HTTPException(status_code=404, detail=f"no lyrics for {track_id}")
    return LYRICS[track_id]


@app.get("/lyrics/{track_id}/at")
async def lyric_at(track_id: str, t: float) -> dict:
    """Return the lyric line whose at_s ≤ t (latest match)."""
    if track_id not in LYRICS:
        raise HTTPException(status_code=404, detail=f"no lyrics for {track_id}")
    current = {"at_s": 0, "line": ""}
    for line in LYRICS[track_id]:
        if line["at_s"] <= t:
            current = line
        else:
            break
    return current
