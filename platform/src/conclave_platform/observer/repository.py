"""Read + write helpers over the ORM.

Keep these short — they're called by both the REST ingest layer and the
state MCP server.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import (
    AgendaItem,
    AgendaSection,
    AgendaSnapshot,
    CallEdge,
    Chatroom,
    Endpoint,
    EndpointKey,
    Member,
    MemberStatus,
    PodName,
    endpoint_key,
    utc_now,
)
from ..core.ids import AgendaItemId, ChatroomId
from .orm import (
    AgendaItemRow,
    CallEdgeRow,
    ChatroomRow,
    EndpointRow,
    MemberRow,
)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


async def upsert_member(
    session: AsyncSession,
    *,
    name: PodName,
    charter_path: str,
    status: MemberStatus,
) -> Member:
    row = await session.get(MemberRow, name)
    now = utc_now()
    if row is None:
        row = MemberRow(name=name, status=status, charter_path=charter_path)
        if status == MemberStatus.admitted:
            row.admitted_at = now
        session.add(row)
    else:
        row.status = status
        row.charter_path = charter_path
        if status == MemberStatus.admitted and row.admitted_at is None:
            row.admitted_at = now
        if status == MemberStatus.exiled and row.exiled_at is None:
            row.exiled_at = now
    await session.flush()
    return _to_member(row)


async def list_members(session: AsyncSession) -> list[Member]:
    rows = (await session.execute(select(MemberRow))).scalars().all()
    return [_to_member(r) for r in rows]


def _to_member(row: MemberRow) -> Member:
    return Member(
        name=PodName(row.name),
        status=MemberStatus(row.status),
        charter_path=row.charter_path,
        admitted_at=_utc(row.admitted_at),
        exiled_at=_utc(row.exiled_at),
    )


async def upsert_endpoint(
    session: AsyncSession,
    *,
    pod: PodName,
    method: str,
    path: str,
    annotation: str | None,
) -> tuple[Endpoint, bool]:
    """Returns (endpoint, is_new). is_new triggers annotation_requested events."""
    method = method.upper()
    stmt = select(EndpointRow).where(
        EndpointRow.pod == pod, EndpointRow.method == method, EndpointRow.path == path
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    now = utc_now()
    is_new = row is None
    if row is None:
        row = EndpointRow(
            pod=pod,
            method=method,
            path=path,
            annotation=annotation,
            first_seen=now,
            last_seen=now,
        )
        session.add(row)
    else:
        row.last_seen = now
        if annotation is not None:
            row.annotation = annotation
    await session.flush()
    return _to_endpoint(row), is_new


async def list_endpoints(session: AsyncSession, pod: PodName) -> list[Endpoint]:
    rows = (
        (await session.execute(select(EndpointRow).where(EndpointRow.pod == pod)))
        .scalars()
        .all()
    )
    return [_to_endpoint(r) for r in rows]


def _to_endpoint(row: EndpointRow) -> Endpoint:
    first = _utc(row.first_seen)
    last = _utc(row.last_seen)
    assert first is not None
    assert last is not None
    return Endpoint(
        pod=PodName(row.pod),
        method=row.method,
        path=row.path,
        annotation=row.annotation,
        first_seen=first,
        last_seen=last,
    )


async def record_call(
    session: AsyncSession,
    *,
    caller: PodName,
    callee: PodName,
    endpoint: EndpointKey,
    rate_per_min: float | None = None,
) -> None:
    row = await session.get(CallEdgeRow, (caller, callee, endpoint))
    now = utc_now()
    if row is None:
        row = CallEdgeRow(
            caller=caller,
            callee=callee,
            endpoint_key=endpoint,
            rate_per_min=rate_per_min or 0.0,
            last_seen=now,
        )
        session.add(row)
    else:
        if rate_per_min is not None:
            row.rate_per_min = rate_per_min
        row.last_seen = now
    await session.flush()


async def callers_of(session: AsyncSession, endpoint: EndpointKey) -> list[PodName]:
    rows = (
        (await session.execute(select(CallEdgeRow).where(CallEdgeRow.endpoint_key == endpoint)))
        .scalars()
        .all()
    )
    return [PodName(r.caller) for r in rows]


async def calls_to(session: AsyncSession, pod: PodName) -> list[CallEdge]:
    rows = (
        (await session.execute(select(CallEdgeRow).where(CallEdgeRow.callee == pod)))
        .scalars()
        .all()
    )
    return [
        CallEdge(
            caller=PodName(r.caller),
            callee=PodName(r.callee),
            endpoint=EndpointKey(r.endpoint_key),
            rate_per_min=r.rate_per_min,
            last_seen=_utc(r.last_seen) or datetime.now(UTC),
        )
        for r in rows
    ]


async def upsert_chatroom(
    session: AsyncSession,
    *,
    chatroom_id: ChatroomId,
    topic: str,
    participants: list[PodName],
    opened_by: PodName,
    opened_at: datetime,
    last_active: datetime,
    closed_at: datetime | None,
    summary: str | None,
) -> Chatroom:
    row = await session.get(ChatroomRow, chatroom_id)
    if row is None:
        row = ChatroomRow(
            id=chatroom_id,
            topic=topic,
            participants=list(participants),
            opened_by=opened_by,
            opened_at=opened_at,
            last_active=last_active,
            closed_at=closed_at,
            summary=summary,
        )
        session.add(row)
    else:
        row.topic = topic
        row.participants = list(participants)
        row.last_active = last_active
        row.closed_at = closed_at
        row.summary = summary
    await session.flush()
    return _to_chatroom(row)


async def list_chatrooms(session: AsyncSession) -> list[Chatroom]:
    rows = (await session.execute(select(ChatroomRow))).scalars().all()
    return [_to_chatroom(r) for r in rows]


def _to_chatroom(row: ChatroomRow) -> Chatroom:
    opened = _utc(row.opened_at)
    active = _utc(row.last_active)
    assert opened is not None
    assert active is not None
    return Chatroom(
        id=ChatroomId(row.id),
        topic=row.topic,
        participants=[PodName(p) for p in row.participants],
        opened_by=PodName(row.opened_by),
        opened_at=opened,
        last_active=active,
        closed_at=_utc(row.closed_at),
        summary=row.summary,
    )


async def replace_agenda(
    session: AsyncSession,
    *,
    pod: PodName,
    items: list[AgendaItem],
) -> AgendaSnapshot:
    # Atomic replace: delete then bulk insert. Small N per pod so this is fine.
    await session.execute(delete(AgendaItemRow).where(AgendaItemRow.pod == pod))
    for item in items:
        session.add(
            AgendaItemRow(
                id=item.id,
                pod=pod,
                section=item.section.value,
                text=item.text,
                since=item.since,
                eta=item.eta,
                updated_at=item.updated_at,
            )
        )
    await session.flush()
    return await read_agenda(session, pod)


async def read_agenda(session: AsyncSession, pod: PodName) -> AgendaSnapshot:
    rows = (
        (await session.execute(select(AgendaItemRow).where(AgendaItemRow.pod == pod)))
        .scalars()
        .all()
    )
    doing: list[AgendaItem] = []
    nxt: list[AgendaItem] = []
    blocked: list[AgendaItem] = []
    latest = utc_now()
    for r in rows:
        updated = _utc(r.updated_at)
        assert updated is not None
        item = AgendaItem(
            id=AgendaItemId(r.id),
            pod=pod,
            section=AgendaSection(r.section),
            text=r.text,
            since=_utc(r.since),
            eta=r.eta,
            updated_at=updated,
        )
        if r.section == AgendaSection.doing.value:
            doing.append(item)
        elif r.section == AgendaSection.next.value:
            nxt.append(item)
        else:
            blocked.append(item)
        latest = max(latest, updated)
    return AgendaSnapshot(
        pod=pod, doing=doing, next=nxt, blocked_on=blocked, updated_at=latest
    )


async def mark_item_completed(
    session: AsyncSession,
    *,
    pod: PodName,
    item_id: AgendaItemId,
) -> bool:
    row = await session.get(AgendaItemRow, item_id)
    if row is None or row.pod != pod:
        return False
    if row.section == AgendaSection.doing.value:
        await session.delete(row)
        await session.flush()
        return True
    return False


__all__ = [
    "callers_of",
    "calls_to",
    "list_chatrooms",
    "list_endpoints",
    "list_members",
    "mark_item_completed",
    "read_agenda",
    "record_call",
    "replace_agenda",
    "upsert_chatroom",
    "upsert_endpoint",
    "upsert_member",
]


def endpoint_key_for(method: str, path: str) -> EndpointKey:
    return endpoint_key(method, path)
