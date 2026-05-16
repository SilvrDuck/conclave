"""POST /commands — the 4 Forum writes fanout.

This is the *only* write path the Forum has into the platform. The router
validates the payload and dispatches via OperatorService.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from observer.services.command_router import CommandRouter
from observer.services.operator import OperatorService

log = logging.getLogger("observer.api.commands")

router = APIRouter(prefix="/commands", tags=["commands"])


@router.post("")
async def post_command(request: Request, body: dict) -> dict[str, str]:
    state = request.app.state.observer
    cr = CommandRouter(operator=OperatorService(pool=state.pool, bus=state.bus))
    try:
        await cr.dispatch(body)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"status": "accepted"}
