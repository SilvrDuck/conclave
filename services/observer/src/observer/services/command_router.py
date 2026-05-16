"""CommandRouter — translates the 4 Forum writes into bus commands.

Forum POSTs to `/commands` with `{kind, ...payload}`. The router validates
the kind and routes via OperatorService. The router itself never writes
to the DB; the owning context's process (or, for IssueProclamation, the
OperatorService in the observer process) does that.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from observer.services.operator import OperatorService

FOUR_WRITES = {"IssueProclamation", "SendDirectMessage", "EditCharter", "CastBallot"}


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
    choice: str  # 'yes' | 'no' | 'abstain' — validated in senate
    comment: str | None = None


class CommandRouter:
    def __init__(self, *, operator: OperatorService) -> None:
        self._operator = operator

    async def dispatch(self, body: dict[str, Any]) -> None:
        kind = body.get("kind")
        if kind not in FOUR_WRITES:
            raise ValueError(
                f"unsupported command kind: {kind!r}; expected one of {sorted(FOUR_WRITES)}"
            )

        match kind:
            case "IssueProclamation":
                validated = IssueProclamationPayload.model_validate(body)
                payload = validated.model_dump(exclude={"kind"})
            case "SendDirectMessage":
                validated_dm = SendDirectMessagePayload.model_validate(body)
                payload = validated_dm.model_dump(exclude={"kind"})
            case "EditCharter":
                validated_ce = EditCharterPayload.model_validate(body)
                payload = validated_ce.model_dump(exclude={"kind"})
            case "CastBallot":
                validated_cb = CastBallotPayload.model_validate(body)
                payload = validated_cb.model_dump(exclude={"kind"})
            case _:
                raise ValueError(f"unhandled kind: {kind}")

        await self._operator.fan_out_forum_command(kind, payload)
