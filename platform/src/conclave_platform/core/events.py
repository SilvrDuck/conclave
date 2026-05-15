"""Inbound event stream — what the harness delivers to a pod's CLI via recv.

All events share a common envelope (type, ts, target_pod) for routing on the bus.
The payload is discriminated by `type`, so each consumer can type-narrow with
`match`. Subjects on the bus follow `pod/<name>/inbox` for per-pod inboxes and
`system/<topic>` for broadcasts the observer cares about.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from .ids import (
    AgendaItemId,
    ChatroomId,
    CouncilId,
    EndpointKey,
    MessageId,
    PodName,
    ProposalId,
)
from .time import utc_now


class EventType(StrEnum):
    message_received = "message_received"
    direct_message = "direct_message"
    council_invited = "council_invited"
    vote_open = "vote_open"
    vote_closed = "vote_closed"
    annotation_requested = "annotation_requested"
    item_completed = "item_completed"
    agenda_updated = "agenda_updated"
    member_admitted = "member_admitted"
    member_exiled = "member_exiled"
    contract_change_proposed = "contract_change_proposed"
    goal_updated = "goal_updated"


class _BaseEvent(BaseModel):
    target_pod: PodName | None = None  # None == broadcast
    ts: datetime = Field(default_factory=utc_now)


class MessageReceived(_BaseEvent):
    type: Literal[EventType.message_received] = EventType.message_received
    chatroom_id: ChatroomId
    message_id: MessageId
    from_pod: PodName
    body: str


class DirectMessage(_BaseEvent):
    type: Literal[EventType.direct_message] = EventType.direct_message
    message_id: MessageId
    from_pod: PodName
    body: str


class CouncilInvited(_BaseEvent):
    type: Literal[EventType.council_invited] = EventType.council_invited
    council_id: CouncilId
    topic: str
    convened_by: PodName


class VoteOpen(_BaseEvent):
    type: Literal[EventType.vote_open] = EventType.vote_open
    proposal_id: ProposalId
    kind: str
    proposer: PodName
    rationale: str


class VoteClosed(_BaseEvent):
    type: Literal[EventType.vote_closed] = EventType.vote_closed
    proposal_id: ProposalId
    outcome: str


class AnnotationRequested(_BaseEvent):
    type: Literal[EventType.annotation_requested] = EventType.annotation_requested
    endpoint: EndpointKey
    pod: PodName


class ItemCompleted(_BaseEvent):
    type: Literal[EventType.item_completed] = EventType.item_completed
    pod: PodName
    item_id: AgendaItemId


class AgendaUpdated(_BaseEvent):
    type: Literal[EventType.agenda_updated] = EventType.agenda_updated
    pod: PodName


class MemberAdmitted(_BaseEvent):
    type: Literal[EventType.member_admitted] = EventType.member_admitted
    pod: PodName


class MemberExiled(_BaseEvent):
    type: Literal[EventType.member_exiled] = EventType.member_exiled
    pod: PodName


class ContractChangeProposed(_BaseEvent):
    type: Literal[EventType.contract_change_proposed] = EventType.contract_change_proposed
    proposer: PodName
    endpoints: list[EndpointKey]
    rationale: str
    proposal_id: ProposalId


class GoalUpdated(_BaseEvent):
    type: Literal[EventType.goal_updated] = EventType.goal_updated
    goal: str


type Event = Annotated[
    MessageReceived
    | DirectMessage
    | CouncilInvited
    | VoteOpen
    | VoteClosed
    | AnnotationRequested
    | ItemCompleted
    | AgendaUpdated
    | MemberAdmitted
    | MemberExiled
    | ContractChangeProposed
    | GoalUpdated,
    Field(discriminator="type"),
]


class EventEnvelope(BaseModel):
    """Wrapper used on the bus so subscribers can deserialize before dispatching."""

    event: Event


SYSTEM_MANDATE_TOPIC = "system/mandate"
SYSTEM_OBSERVER_TOPIC = "system/observer"


def pod_inbox_topic(pod: PodName) -> str:
    return f"pod/{pod}/inbox"
