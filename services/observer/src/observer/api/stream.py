"""GET /stream — SSE stream of bus events for the Forum.

Each event the projection sees gets fanned out through the in-process
broadcaster. SSE clients subscribe to their own bounded queue.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

log = logging.getLogger("observer.api.stream")

router = APIRouter(tags=["stream"])

KEEPALIVE_SECONDS = 15.0


@router.get("/stream")
async def stream(request: Request) -> EventSourceResponse:
    broadcaster = request.app.state.observer.event_broadcaster
    queue = await broadcaster.subscribe()

    async def gen() -> AsyncIterator[dict[str, str]]:
        try:
            while True:
                if await request.is_disconnected():
                    return
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SECONDS)
                except TimeoutError:
                    yield {"event": "keepalive", "data": ""}
                    continue
                yield {"event": "domain", "data": payload}
        finally:
            await broadcaster.unsubscribe(queue)

    return EventSourceResponse(gen())
