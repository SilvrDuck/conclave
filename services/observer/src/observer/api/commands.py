"""POST /commands — the 4 Forum writes fanout.

Parsed at the edge: a pydantic `RootModel` over a `kind`-discriminated union
gives FastAPI 422 on malformed payloads instead of a 500.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Request
from pydantic import Field, RootModel

from observer.services.command_router import (
    CastBallotPayload,
    CommandRouter,
    EditCharterPayload,
    IssueProclamationPayload,
    RestartPodPayload,
    SendDirectMessagePayload,
)
from observer.services.operator import OperatorService

log = logging.getLogger("observer.api.commands")

router = APIRouter(prefix="/commands", tags=["commands"])


class CommandBody(
    RootModel[
        Annotated[
            IssueProclamationPayload
            | SendDirectMessagePayload
            | EditCharterPayload
            | CastBallotPayload
            | RestartPodPayload,
            Field(discriminator="kind"),
        ]
    ]
):
    """Discriminated union root model for the Forum writes."""


@router.post("")
async def post_command(request: Request, body: CommandBody) -> dict[str, str]:
    state = request.app.state.observer
    cr = CommandRouter(operator=OperatorService(pool=state.pool, bus=state.bus))
    await cr.dispatch_validated(body.root)
    return {"status": "accepted"}
