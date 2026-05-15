"""Request/response models for the senate ledger HTTP surface."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ..core import (
    BallotChoice,
    PodName,
    Proposal,
    ProposalKind,
    ProposalOutcome,
    VotingStrategy,
)
from ..core.ids import ProposalId


class ProposeIn(BaseModel):
    kind: ProposalKind
    proposer: PodName
    strategy: VotingStrategy
    payload: dict[str, object] = {}
    rationale: str = ""
    affected_override: list[PodName] | None = None
    deadline_seconds: int = 900


class ProposalOut(BaseModel):
    proposal: Proposal


class CastBallotIn(BaseModel):
    voter: PodName
    choice: BallotChoice
    comment: str | None = None


class OutcomeOut(BaseModel):
    proposal_id: ProposalId
    outcome: ProposalOutcome | None = None
    adr_id: str | None = None
    decided_at: datetime | None = None
    reason: str = ""


class ProposalsOut(BaseModel):
    proposals: list[Proposal]


class MembersAdmitOut(BaseModel):
    members: list[PodName]
