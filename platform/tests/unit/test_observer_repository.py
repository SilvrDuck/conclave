"""Repository layer against in-memory aiosqlite."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from conclave_platform.core import (
    AgendaItem,
    AgendaSection,
    MemberStatus,
    PodName,
    endpoint_key,
)
from conclave_platform.core.ids import AgendaItemId, ChatroomId
from conclave_platform.observer import repository as repo
from conclave_platform.observer.db import (
    make_engine,
    make_session_factory,
    session_scope,
)
from conclave_platform.observer.orm import Base


@pytest_asyncio.fixture
async def sessions() -> async_sessionmaker:
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield make_session_factory(engine)
    await engine.dispose()


async def test_upsert_member_is_idempotent(sessions: async_sessionmaker) -> None:
    async with session_scope(sessions) as s:
        m1 = await repo.upsert_member(
            s,
            name=PodName("alice"),
            charter_path="pods/alice/charter.md",
            status=MemberStatus.admitted,
        )
    async with session_scope(sessions) as s:
        m2 = await repo.upsert_member(
            s,
            name=PodName("alice"),
            charter_path="pods/alice/charter.md",
            status=MemberStatus.admitted,
        )
    assert m1.admitted_at == m2.admitted_at


async def test_upsert_endpoint_first_call_is_new(sessions: async_sessionmaker) -> None:
    async with session_scope(sessions) as s:
        _, is_new = await repo.upsert_endpoint(
            s, pod=PodName("alice"), method="get", path="/users", annotation=None
        )
    assert is_new is True
    async with session_scope(sessions) as s:
        _, again_new = await repo.upsert_endpoint(
            s, pod=PodName("alice"), method="GET", path="/users", annotation="list users"
        )
    assert again_new is False
    async with session_scope(sessions) as s:
        endpoints = await repo.list_endpoints(s, PodName("alice"))
    assert len(endpoints) == 1
    assert endpoints[0].annotation == "list users"
    assert endpoints[0].method == "GET"


async def test_record_call_and_callers_of(sessions: async_sessionmaker) -> None:
    key = endpoint_key("get", "/users/{id}")
    async with session_scope(sessions) as s:
        await repo.record_call(
            s, caller=PodName("alice"), callee=PodName("bob"), endpoint=key
        )
        await repo.record_call(
            s, caller=PodName("carol"), callee=PodName("bob"), endpoint=key
        )
    async with session_scope(sessions) as s:
        callers = await repo.callers_of(s, key)
    assert set(callers) == {PodName("alice"), PodName("carol")}


async def test_replace_agenda_replaces_atomically(
    sessions: async_sessionmaker,
) -> None:
    now = datetime(2026, 5, 15, tzinfo=UTC)
    a = AgendaItem(
        id=AgendaItemId("alice-1"),
        pod=PodName("alice"),
        section=AgendaSection.doing,
        text="ship pagination",
        updated_at=now,
    )
    b = AgendaItem(
        id=AgendaItemId("alice-2"),
        pod=PodName("alice"),
        section=AgendaSection.next,
        text="swap session store",
        updated_at=now,
    )
    async with session_scope(sessions) as s:
        await repo.replace_agenda(s, pod=PodName("alice"), items=[a, b])
    async with session_scope(sessions) as s:
        snap = await repo.read_agenda(s, PodName("alice"))
    assert [i.id for i in snap.doing] == [AgendaItemId("alice-1")]
    assert [i.id for i in snap.next] == [AgendaItemId("alice-2")]
    # Replace shrinks to just one item.
    async with session_scope(sessions) as s:
        await repo.replace_agenda(s, pod=PodName("alice"), items=[a])
    async with session_scope(sessions) as s:
        snap = await repo.read_agenda(s, PodName("alice"))
    assert snap.next == []


async def test_mark_item_completed_removes_from_doing(
    sessions: async_sessionmaker,
) -> None:
    now = datetime(2026, 5, 15, tzinfo=UTC)
    item = AgendaItem(
        id=AgendaItemId("alice-42"),
        pod=PodName("alice"),
        section=AgendaSection.doing,
        text="ship pagination",
        updated_at=now,
    )
    async with session_scope(sessions) as s:
        await repo.replace_agenda(s, pod=PodName("alice"), items=[item])
    async with session_scope(sessions) as s:
        ok = await repo.mark_item_completed(
            s, pod=PodName("alice"), item_id=AgendaItemId("alice-42")
        )
    assert ok is True
    async with session_scope(sessions) as s:
        snap = await repo.read_agenda(s, PodName("alice"))
    assert snap.doing == []


async def test_upsert_chatroom_round_trip(sessions: async_sessionmaker) -> None:
    now = datetime(2026, 5, 15, tzinfo=UTC)
    async with session_scope(sessions) as s:
        cr = await repo.upsert_chatroom(
            s,
            chatroom_id=ChatroomId("c-1"),
            topic="auth design",
            participants=[PodName("alice"), PodName("bob")],
            opened_by=PodName("alice"),
            opened_at=now,
            last_active=now,
            closed_at=None,
            summary=None,
        )
    assert cr.topic == "auth design"
    async with session_scope(sessions) as s:
        rooms = await repo.list_chatrooms(s)
    assert len(rooms) == 1
