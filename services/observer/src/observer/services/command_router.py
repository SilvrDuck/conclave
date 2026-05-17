"""CommandRouter — translates the 4 Forum writes into bus commands.

Pydantic payloads are validated at the FastAPI edge (`api/commands.py`).
This router only fans the validated model out via OperatorService.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from observer.services.operator import OperatorService


class IssueProclamationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["IssueProclamation"] = "IssueProclamation"
    text: str = Field(min_length=1)


class SendDirectMessagePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["SendDirectMessage"] = "SendDirectMessage"
    pod_id: str = Field(min_length=1)
    body: str = Field(min_length=1)


class EditCharterPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["EditCharter"] = "EditCharter"
    pod_id: str = Field(min_length=1)
    body: str


class CastBallotPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["CastBallot"] = "CastBallot"
    proposal_id: str
    voter: str
    choice: Literal["yes", "no", "abstain"]
    comment: str | None = None


class RestartPodPayload(BaseModel):
    """ATAM Op4 — Augustus restarts a pod that's stuck or
    misbehaving without exiling it. Implemented as `docker restart
    conclave-<pod_id>` on the host daemon via mcp-pods."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["RestartPod"] = "RestartPod"
    pod_id: str = Field(min_length=1)


ValidatedCommand = (
    IssueProclamationPayload
    | SendDirectMessagePayload
    | EditCharterPayload
    | CastBallotPayload
    | RestartPodPayload
)


class CommandRouter:
    def __init__(self, *, operator: OperatorService) -> None:
        self._operator = operator

    async def dispatch_validated(self, body: ValidatedCommand) -> None:
        payload = body.model_dump(exclude={"kind"})
        await self._operator.fan_out_forum_command(body.kind, payload)
