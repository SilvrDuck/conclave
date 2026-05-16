"""Web service — the music UI + proxy endpoints to peers.

All inter-pod calls go through the conclave network; OTel auto-
instrumentation records HTTP spans visible on the Forum's Glance graph.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

CATALOG_URL = os.environ.get("CATALOG_URL", "http://catalog:8000")
LYRICS_URL = os.environ.get("LYRICS_URL", "http://lyrics:8000")
JAM_URL = os.environ.get("JAM_URL", "http://jam:8000")

_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _client
    _client = httpx.AsyncClient(timeout=10.0)
    try:
        yield
    finally:
        await _client.aclose()
        _client = None


app = FastAPI(title="conclave-web", lifespan=lifespan)


def client() -> httpx.AsyncClient:
    assert _client is not None
    return _client


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "pod": os.environ.get("POD_ID", "?")}


@app.get("/api/tracks")
async def tracks() -> list[dict]:
    r = await client().get(f"{CATALOG_URL}/tracks")
    r.raise_for_status()
    return r.json()


@app.get("/api/lyrics/{track_id}")
async def lyrics(track_id: str, t: float = 0) -> dict:
    r = await client().get(f"{LYRICS_URL}/lyrics/{track_id}/at", params={"t": t})
    if r.status_code == 404:
        raise HTTPException(404, "no lyrics")
    r.raise_for_status()
    return r.json()


@app.post("/api/jam")
async def jam_create(body: dict) -> dict:
    r = await client().post(f"{JAM_URL}/jam", json=body)
    r.raise_for_status()
    return r.json()


@app.get("/api/jam/{jam_id}")
async def jam_get(jam_id: str) -> dict:
    r = await client().get(f"{JAM_URL}/jam/{jam_id}")
    r.raise_for_status()
    return r.json()


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>conclave / music</title>
  <style>
    body { font-family: ui-sans-serif, system-ui; background:#0f172a; color:#e2e8f0;
           margin:0; padding:2rem; max-width:780px; margin-left:auto; margin-right:auto; }
    h1 { font-weight: 600; letter-spacing: -0.02em; }
    button { background:#6366f1; color:white; border:0; padding:.5rem 1rem;
             border-radius:.5rem; cursor:pointer; font-size:.95rem; }
    .track { padding:.75rem 1rem; background:#1e293b; border-radius:.5rem;
             margin-bottom:.5rem; display:flex; justify-content:space-between; align-items:center; }
    .lyric { font-size:1.4rem; margin:1.5rem 0; min-height:2rem; color:#f1f5f9;
             text-align:center; font-style:italic; }
    .now { padding:1rem; background:#1e293b; border-radius:.5rem; margin-top:1rem; }
    audio { width:100%; margin-top:.5rem; }
    .jam-row { display:flex; gap:.5rem; align-items:center; margin-top:1rem; }
    .jam-row input { flex:1; padding:.5rem; background:#0f172a; color:#e2e8f0;
                     border:1px solid #334155; border-radius:.5rem; }
    .badge { font-size:.7rem; padding:.15rem .5rem; background:#334155; border-radius:1rem; }
  </style>
</head>
<body>
  <h1>♪ conclave / music</h1>
  <p style="color:#94a3b8">Multi-pod: web → catalog → lyrics → jam.</p>
  <div id="tracks">loading…</div>
  <div class="now" id="player" style="display:none">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <strong id="now-title"></strong>
      <span class="badge" id="now-artist"></span>
    </div>
    <audio id="audio" controls></audio>
    <div class="lyric" id="lyric">♪</div>
    <div class="jam-row">
      <button id="jam-create">Start a jam</button>
      <input id="jam-id" placeholder="or jam id…" />
      <button id="jam-join">Join</button>
      <span class="badge" id="jam-status"></span>
    </div>
  </div>
  <script>
  async function loadTracks() {
    const r = await fetch('/api/tracks');
    const tracks = await r.json();
    const el = document.getElementById('tracks');
    el.innerHTML = '';
    for (const t of tracks) {
      const row = document.createElement('div');
      row.className = 'track';
      row.innerHTML = '<span><strong>' + t.title + '</strong> · <span style="color:#94a3b8">' + t.artist + '</span></span>' +
                      '<button data-id="' + t.id + '">Play</button>';
      row.querySelector('button').onclick = () => play(t);
      el.appendChild(row);
    }
  }
  let lyricTimer = null;
  function play(t) {
    document.getElementById('player').style.display = 'block';
    document.getElementById('now-title').textContent = t.title;
    document.getElementById('now-artist').textContent = t.artist;
    const a = document.getElementById('audio');
    a.src = t.audio_url; a.currentTime = 0; a.play().catch(()=>{});
    if (lyricTimer) clearInterval(lyricTimer);
    lyricTimer = setInterval(async () => {
      const r = await fetch('/api/lyrics/' + t.id + '?t=' + a.currentTime);
      if (r.ok) document.getElementById('lyric').textContent = (await r.json()).line || '♪';
    }, 500);
  }
  document.getElementById('jam-create').onclick = async () => {
    const title = document.getElementById('now-title').textContent;
    const tracks = await (await fetch('/api/tracks')).json();
    const t = tracks.find(x => x.title === title);
    if (!t) return;
    const r = await fetch('/api/jam', {method:'POST', headers:{'content-type':'application/json'},
                                      body: JSON.stringify({track_id: t.id, host: 'augustus'})});
    const j = await r.json();
    document.getElementById('jam-status').textContent = 'jam ' + j.id;
    document.getElementById('jam-id').value = j.id;
  };
  document.getElementById('jam-join').onclick = async () => {
    const id = document.getElementById('jam-id').value.trim();
    if (!id) return;
    const r = await fetch('/api/jam/' + id);
    if (r.ok) {
      const j = await r.json();
      document.getElementById('jam-status').textContent =
        'jam ' + id + ' (' + j.listeners.length + ' listeners, ' + j.playhead_s + 's)';
    }
  };
  loadTracks();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return INDEX_HTML
