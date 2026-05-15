"""Domain entities shared by observer, senate, and MCP layers.

These are transport-level models — the database layer keeps its own ORM types
and converts at the boundary. Same name, different responsibilities: this file
is the wire and code contract; storage is an implementation detail.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from .ids import (
    AdrId,
    AgendaItemId,
    ChatroomId,
    CouncilId,
    EndpointKey,
    MessageId,
    PodName,
    ProposalId,
    endpoint_key,
)
from .time import utc_now


class MemberStatus(StrEnum):
    proposed = "proposed"
    admitted = "admitted"
    exiled = "exiled"


class VotingStrategy(StrEnum):
    majority = "majority"
    supermajority = "supermajority"
    consensus_omnium = "consensus_omnium"
    sortition = "sortition"


class ProposalKind(StrEnum):
    member = "member"
    exile = "exile"
    revival = "revival"
    contract_change = "contract_change"
    completion = "completion"


class BallotChoice(StrEnum):
    yes = "yes"
    no = "no"
    abstain = "abstain"


class ProposalOutcome(StrEnum):
    approved = "approved"
    rejected = "rejected"
    timeout = "timeout"


class AgendaSection(StrEnum):
    doing = "doing"
    next = "next"
    blocked_on = "blocked_on"


class Member(BaseModel):
    name: PodName
    status: MemberStatus
    charter_path: str
    admitted_at: datetime | None = None
    exiled_at: datetime | None = None


class Endpoint(BaseModel):
    pod: PodName
    method: str
    path: str
    annotation: str | None = None
    first_seen: datetime
    last_seen: datetime

    @property
    def key(self) -> EndpointKey:
        return endpoint_key(self.method, self.path)


class CallEdge(BaseModel):
    caller: PodName
    callee: PodName
    endpoint: EndpointKey
    rate_per_min: float = 0.0
    last_seen: datetime


class AgendaItem(BaseModel):
    id: AgendaItemId
    pod: PodName
    section: AgendaSection
    text: str
    since: datetime | None = None
    eta: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class AgendaSnapshot(BaseModel):
    pod: PodName
    doing: list[AgendaItem] = []
    next: list[AgendaItem] = []
    blocked_on: list[AgendaItem] = []
    updated_at: datetime = Field(default_factory=utc_now)


class Chatroom(BaseModel):
    id: ChatroomId
    topic: str
    participants: list[PodName]
    opened_by: PodName
    opened_at: datetime
    last_active: datetime
    closed_at: datetime | None = None
    summary: str | None = None


class Council(BaseModel):
    id: CouncilId
    topic: str
    participants: list[PodName]
    convened_by: PodName
    convened_at: datetime
    closed_at: datetime | None = None
    summary: str | None = None


class Message(BaseModel):
    id: MessageId
    chatroom_id: ChatroomId | CouncilId | None = None  # None for direct_message
    from_pod: PodName
    to_pod: PodName | None = None
    body: str
    sent_at: datetime


class Proposal(BaseModel):
    id: ProposalId
    kind: ProposalKind
    proposer: PodName
    strategy: VotingStrategy
    payload: dict[str, str | int | float | bool | list[str] | None]
    affected: list[PodName]
    opened_at: datetime
    deadline: datetime
    outcome: ProposalOutcome | None = None
    decided_at: datetime | None = None


class Ballot(BaseModel):
    proposal_id: ProposalId
    voter: PodName
    choice: BallotChoice
    comment: str | None = None
    cast_at: datetime


class Adr(BaseModel):
    id: AdrId
    title: str
    body: str
    affected_pods: list[PodName]
    proposal_id: ProposalId | None = None
    created_at: datetime
