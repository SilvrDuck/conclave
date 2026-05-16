"""GET /inbox — Augustus's joined inbox view."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from observer.services.inbox import InboxReadModel

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("")
async def get_inbox(request: Request) -> list[dict[str, Any]]:
    pool = request.app.state.observer.pool
    return await InboxReadModel(pool=pool).read()
