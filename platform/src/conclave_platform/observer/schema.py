"""Request/response models for the observer REST surface."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ..core import (
    AgendaSection,
    AgendaSnapshot,
    Chatroom,
    Endpoint,
    Member,
    MemberStatus,
    PodName,
    utc_now,
)
from ..core.ids import AgendaItemId, ChatroomId


class HealthOut(BaseModel):
    status: str = "ok"


class IngestMemberIn(BaseModel):
    name: PodName
    charter_path: str
    status: MemberStatus = MemberStatus.admitted


class IngestEndpointIn(BaseModel):
    pod: PodName
    method: str
    path: str
    annotation: str | None = None


class IngestCallIn(BaseModel):
    caller: PodName
    callee: PodName
    method: str
    path: str
    rate_per_min: float | None = None


class AgendaItemIn(BaseModel):
    id: AgendaItemId
    section: AgendaSection
    text: str
    since: datetime | None = None
    eta: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class IngestAgendaIn(BaseModel):
    pod: PodName
    items: list[AgendaItemIn]


class IngestChatroomIn(BaseModel):
    chatroom_id: ChatroomId
    topic: str
    participants: list[PodName]
    opened_by: PodName
    opened_at: datetime
    last_active: datetime
    closed_at: datetime | None = None
    summary: str | None = None


class IngestItemCompletedIn(BaseModel):
    pod: PodName
    item_id: AgendaItemId


class MembersOut(BaseModel):
    members: list[Member]


class EndpointsOut(BaseModel):
    endpoints: list[Endpoint]


class ChatroomsOut(BaseModel):
    chatrooms: list[Chatroom]


class AgendaOut(BaseModel):
    snapshot: AgendaSnapshot


class CallersOut(BaseModel):
    callers: list[PodName]


class IngestAck(BaseModel):
    ok: bool = True
    is_new: bool | None = None
