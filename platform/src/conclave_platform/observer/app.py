"""FastAPI factory for the observer service.

Two surfaces:
  • REST ingest (POST /ingest/*) — harness dual-writes, control-plane events.
  • REST read  (GET /state/*)    — used by the state MCP server.
The state MCP is a thin layer on top; it lives in conclave_platform.mcp.state.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from ..adapters import BusAdapter
from ..core import AgendaItem, EventEnvelope, GoalUpdated, MemberStatus, endpoint_key
from ..core.events import SYSTEM_OBSERVER_TOPIC, AnnotationRequested, pod_inbox_topic
from ..core.ids import EndpointKey, PodName
from . import repository as repo
from .db import make_engine, make_session_factory, session_scope
from .orm import Base
from .schema import (
    AgendaOut,
    CallersOut,
    ChatroomsOut,
    EndpointsOut,
    HealthOut,
    IngestAck,
    IngestAgendaIn,
    IngestCallIn,
    IngestChatroomIn,
    IngestEndpointIn,
    IngestItemCompletedIn,
    IngestMemberIn,
    MembersOut,
)


class MandateIn(BaseModel):
    pod: PodName = PodName("founder")
    goal: str


@dataclass
class ObserverDeps:
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]
    bus: BusAdapter | None = None


def create_app(*, dsn: str, bus: BusAdapter | None = None) -> FastAPI:
    engine = make_engine(dsn)
    sessions = make_session_factory(engine)
    deps = ObserverDeps(engine=engine, sessions=sessions, bus=bus)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="conclave-observer", version="0.1.0", lifespan=lifespan)

    async def session() -> AsyncIterator[AsyncSession]:
        async with session_scope(deps.sessions) as s:
            yield s

    @app.get("/healthz", response_model=HealthOut)
    async def healthz() -> HealthOut:
        return HealthOut()

    @app.post("/ingest/member", response_model=IngestAck)
    async def ingest_member(
        body: IngestMemberIn,
        s: Annotated[AsyncSession, Depends(session)],
    ) -> IngestAck:
        await repo.upsert_member(
            s, name=body.name, charter_path=body.charter_path, status=body.status
        )
        return IngestAck()

    @app.post("/ingest/endpoint", response_model=IngestAck)
    async def ingest_endpoint(
        body: IngestEndpointIn,
        s: Annotated[AsyncSession, Depends(session)],
    ) -> IngestAck:
        _, is_new = await repo.upsert_endpoint(
            s, pod=body.pod, method=body.method, path=body.path, annotation=body.annotation
        )
        if is_new and deps.bus is not None:
            ev = EventEnvelope(
                event=AnnotationRequested(
                    target_pod=body.pod,
                    endpoint=endpoint_key(body.method, body.path),
                    pod=body.pod,
                )
            )
            await deps.bus.publish(
                f"{SYSTEM_OBSERVER_TOPIC}/annotation_requested",
                ev.model_dump_json().encode(),
            )
        return IngestAck(is_new=is_new)

    @app.post("/ingest/call", response_model=IngestAck)
    async def ingest_call(
        body: IngestCallIn,
        s: Annotated[AsyncSession, Depends(session)],
    ) -> IngestAck:
        await repo.record_call(
            s,
            caller=body.caller,
            callee=body.callee,
            endpoint=endpoint_key(body.method, body.path),
            rate_per_min=body.rate_per_min,
        )
        return IngestAck()

    @app.post("/ingest/agenda", response_model=IngestAck)
    async def ingest_agenda(
        body: IngestAgendaIn,
        s: Annotated[AsyncSession, Depends(session)],
    ) -> IngestAck:
        items = [
            AgendaItem(
                id=i.id,
                pod=body.pod,
                section=i.section,
                text=i.text,
                since=i.since,
                eta=i.eta,
                updated_at=i.updated_at,
            )
            for i in body.items
        ]
        await repo.replace_agenda(s, pod=body.pod, items=items)
        return IngestAck()

    @app.post("/ingest/chatroom", response_model=IngestAck)
    async def ingest_chatroom(
        body: IngestChatroomIn,
        s: Annotated[AsyncSession, Depends(session)],
    ) -> IngestAck:
        await repo.upsert_chatroom(
            s,
            chatroom_id=body.chatroom_id,
            topic=body.topic,
            participants=body.participants,
            opened_by=body.opened_by,
            opened_at=body.opened_at,
            last_active=body.last_active,
            closed_at=body.closed_at,
            summary=body.summary,
        )
        return IngestAck()

    @app.post("/ingest/item-completed", response_model=IngestAck)
    async def ingest_item_completed(
        body: IngestItemCompletedIn,
        s: Annotated[AsyncSession, Depends(session)],
    ) -> IngestAck:
        moved = await repo.mark_item_completed(s, pod=body.pod, item_id=body.item_id)
        return IngestAck(ok=moved)

    @app.get("/state/members", response_model=MembersOut)
    async def state_members(s: Annotated[AsyncSession, Depends(session)]) -> MembersOut:
        return MembersOut(members=await repo.list_members(s))

    @app.get("/state/endpoints/{pod}", response_model=EndpointsOut)
    async def state_endpoints(
        pod: PodName, s: Annotated[AsyncSession, Depends(session)]
    ) -> EndpointsOut:
        return EndpointsOut(endpoints=await repo.list_endpoints(s, pod))

    @app.get("/state/callers", response_model=CallersOut)
    async def state_callers(
        method: str, path: str, s: Annotated[AsyncSession, Depends(session)]
    ) -> CallersOut:
        key: EndpointKey = endpoint_key(method, path)
        return CallersOut(callers=await repo.callers_of(s, key))

    @app.get("/state/chatrooms", response_model=ChatroomsOut)
    async def state_chatrooms(s: Annotated[AsyncSession, Depends(session)]) -> ChatroomsOut:
        return ChatroomsOut(chatrooms=await repo.list_chatrooms(s))

    @app.get("/state/agenda/{pod}", response_model=AgendaOut)
    async def state_agenda(
        pod: PodName, s: Annotated[AsyncSession, Depends(session)]
    ) -> AgendaOut:
        snap = await repo.read_agenda(s, pod)
        if not (snap.doing or snap.next or snap.blocked_on):
            # Surface 404 only when caller looks up a pod that has no agenda *and*
            # no member row — otherwise empty snapshot is fine.
            members = await repo.list_members(s)
            if not any(m.name == pod and m.status != MemberStatus.exiled for m in members):
                raise HTTPException(status_code=404, detail=f"no such pod: {pod}")
        return AgendaOut(snapshot=snap)

    @app.post("/control/mandate")
    async def control_mandate(body: MandateIn) -> dict[str, str]:
        """User-facing mandate publisher — wakes the founder pod (or any pod)
        with a goal_updated event. Used by the Forum UI's mandate input."""
        if deps.bus is None:
            raise HTTPException(status_code=503, detail="bus not wired")
        envelope = EventEnvelope(
            event=GoalUpdated(target_pod=body.pod, goal=body.goal),
        )
        await deps.bus.publish(
            pod_inbox_topic(body.pod), envelope.model_dump_json().encode("utf-8")
        )
        return {"pod": body.pod, "ok": "published"}

    app.state.deps = deps
    return app
