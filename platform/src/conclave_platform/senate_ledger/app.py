"""FastAPI factory for the senate ledger."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from ..adapters import BusAdapter, DocsAdapter
from ..core import Proposal
from ..core.ids import ProposalId
from ..observer.db import make_engine, make_session_factory, session_scope
from . import repository as repo
from . import service
from .observer_client import ObserverClient
from .orm import Base
from .schema import (
    CastBallotIn,
    MembersAdmitOut,
    OutcomeOut,
    ProposalOut,
    ProposalsOut,
    ProposeIn,
)
from .service import _reevaluate


class _AdrCreateIn(BaseModel):
    title: str
    body: str
    affected_pods: list[str]
    proposal_id: str | None = None


@dataclass
class SenateDeps:
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]
    observer: ObserverClient
    docs: DocsAdapter
    bus: BusAdapter | None = None


def create_app(
    *,
    dsn: str,
    observer: ObserverClient,
    docs: DocsAdapter,
    bus: BusAdapter | None = None,
) -> FastAPI:
    engine = make_engine(dsn)
    sessions = make_session_factory(engine)
    deps = SenateDeps(engine=engine, sessions=sessions, observer=observer, docs=docs, bus=bus)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="conclave-senate-ledger", version="0.1.0", lifespan=lifespan)

    async def session() -> AsyncIterator[AsyncSession]:
        async with session_scope(deps.sessions) as s:
            yield s

    session_dep = Annotated[AsyncSession, Depends(session)]

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/proposals", response_model=ProposalOut)
    async def propose(body: ProposeIn, s: session_dep) -> ProposalOut:
        inp = service.ProposeInput(
            kind=body.kind,
            proposer=body.proposer,
            strategy=body.strategy,
            payload=body.payload,
            rationale=body.rationale,
            affected_override=body.affected_override,
            deadline_seconds=body.deadline_seconds,
        )
        proposal = await service.propose(
            s, observer=deps.observer, bus=deps.bus, inp=inp
        )
        # If N=1 auto-yes happened in propose(), re-evaluate to close out.
        if proposal.proposer in proposal.affected and len(proposal.affected) == 1:
            proposal, _ = await _reevaluate(
                s,
                observer=deps.observer,
                docs=deps.docs,
                bus=deps.bus,
                proposal_id=proposal.id,
            )
        return ProposalOut(proposal=proposal)

    @app.get("/proposals", response_model=ProposalsOut)
    async def list_open(s: session_dep) -> ProposalsOut:
        return ProposalsOut(proposals=await repo.list_open_proposals(s))

    @app.get("/proposals/{proposal_id}", response_model=ProposalOut)
    async def get_one(proposal_id: ProposalId, s: session_dep) -> ProposalOut:
        p = await repo.get_proposal(s, proposal_id)
        if p is None:
            raise HTTPException(status_code=404, detail="proposal not found")
        return ProposalOut(proposal=p)

    @app.post("/proposals/{proposal_id}/ballots", response_model=ProposalOut)
    async def ballot(
        proposal_id: ProposalId, body: CastBallotIn, s: session_dep
    ) -> ProposalOut:
        try:
            proposal, _result = await service.cast_and_maybe_close(
                s,
                observer=deps.observer,
                docs=deps.docs,
                bus=deps.bus,
                proposal_id=proposal_id,
                voter=body.voter,
                choice=body.choice,
                comment=body.comment,
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail="proposal not found") from e
        return ProposalOut(proposal=proposal)

    @app.get("/proposals/{proposal_id}/outcome", response_model=OutcomeOut)
    async def outcome(proposal_id: ProposalId, s: session_dep) -> OutcomeOut:
        p = await repo.get_proposal(s, proposal_id)
        if p is None:
            raise HTTPException(status_code=404, detail="proposal not found")
        return OutcomeOut(
            proposal_id=p.id,
            outcome=p.outcome,
            adr_id=p.adr_id,
            decided_at=p.decided_at,
        )

    @app.get("/members", response_model=MembersAdmitOut)
    async def members(s: session_dep) -> MembersAdmitOut:
        return MembersAdmitOut(members=await repo.list_admitted(s))

    # ADR pass-through. mcp-decisions is a thin REST client over these — one
    # writer, one reader, no SQLite races.
    @app.post("/adrs")
    async def write_adr(body: _AdrCreateIn) -> dict[str, str]:
        from ..core import PodName  # noqa: PLC0415

        adr_id = await deps.docs.write_adr(
            title=body.title,
            body=body.body,
            affected_pods=[PodName(p) for p in body.affected_pods],
            proposal_id=body.proposal_id,
        )
        return {"adr_id": adr_id}

    @app.get("/adrs")
    async def list_adrs(
        pod: str | None = None, limit: int = 100
    ) -> dict[str, object]:
        from ..core import PodName  # noqa: PLC0415

        items = await deps.docs.list(pod=PodName(pod) if pod else None, limit=limit)
        return {"adrs": [a.model_dump(mode="json") for a in items]}

    @app.get("/adrs/search")
    async def search_adrs(q: str, limit: int = 10) -> dict[str, object]:
        items = await deps.docs.search(q, limit=limit)
        return {"adrs": [a.model_dump(mode="json") for a in items]}

    @app.get("/adrs/{adr_id}")
    async def read_adr(adr_id: str) -> dict[str, object] | None:
        from ..core.ids import AdrId  # noqa: PLC0415

        adr = await deps.docs.read(AdrId(adr_id))
        return None if adr is None else adr.model_dump(mode="json")

    app.state.deps = deps
    return app


__all__ = ["SenateDeps", "create_app"]


def _quiet_proposal(p: Proposal) -> Proposal:
    return p
