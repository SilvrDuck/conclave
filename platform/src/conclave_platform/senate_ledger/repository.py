"""Persistence helpers for proposals, ballots, and the member mirror."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import (
    Ballot,
    BallotChoice,
    MemberStatus,
    PodName,
    Proposal,
    ProposalKind,
    ProposalOutcome,
    VotingStrategy,
    utc_now,
)
from ..core.ids import AdrId, ProposalId
from .orm import BallotRow, MemberRow, ProposalRow


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


async def add_member(session: AsyncSession, pod: PodName) -> None:
    row = await session.get(MemberRow, pod)
    if row is None:
        session.add(MemberRow(name=pod, status="admitted", admitted_at=utc_now()))
    else:
        row.status = "admitted"
        if row.admitted_at is None:
            row.admitted_at = utc_now()
    await session.flush()


async def exile_member(session: AsyncSession, pod: PodName) -> None:
    row = await session.get(MemberRow, pod)
    if row is None:
        return
    row.status = "exiled"
    if row.exiled_at is None:
        row.exiled_at = utc_now()
    await session.flush()


async def list_admitted(session: AsyncSession) -> list[PodName]:
    rows = (
        (await session.execute(select(MemberRow).where(MemberRow.status == "admitted")))
        .scalars()
        .all()
    )
    return [PodName(r.name) for r in rows]


async def create_proposal(
    session: AsyncSession,
    *,
    proposal_id: ProposalId,
    kind: ProposalKind,
    proposer: PodName,
    strategy: VotingStrategy,
    payload: dict[str, object],
    affected: list[PodName],
    deadline: datetime,
    sortition_pool: list[PodName] | None = None,
) -> Proposal:
    row = ProposalRow(
        id=proposal_id,
        kind=kind.value,
        proposer=proposer,
        strategy=strategy.value,
        payload=payload,
        affected=list(affected),
        sortition_pool=list(sortition_pool) if sortition_pool else None,
        opened_at=utc_now(),
        deadline=deadline,
    )
    session.add(row)
    await session.flush()
    return _to_proposal(row)


async def get_proposal(session: AsyncSession, proposal_id: ProposalId) -> Proposal | None:
    row = await session.get(ProposalRow, proposal_id)
    return None if row is None else _to_proposal(row)


async def list_open_proposals(session: AsyncSession) -> list[Proposal]:
    rows = (
        (await session.execute(select(ProposalRow).where(ProposalRow.outcome.is_(None))))
        .scalars()
        .all()
    )
    return [_to_proposal(r) for r in rows]


async def cast_ballot(
    session: AsyncSession,
    *,
    proposal_id: ProposalId,
    voter: PodName,
    choice: BallotChoice,
    comment: str | None,
) -> None:
    existing = await session.get(BallotRow, (proposal_id, voter))
    now = utc_now()
    if existing is None:
        session.add(
            BallotRow(
                proposal_id=proposal_id,
                voter=voter,
                choice=choice.value,
                comment=comment,
                cast_at=now,
            )
        )
    else:
        existing.choice = choice.value
        existing.comment = comment
        existing.cast_at = now
    await session.flush()


async def list_ballots(session: AsyncSession, proposal_id: ProposalId) -> list[Ballot]:
    rows = (
        (
            await session.execute(
                select(BallotRow).where(BallotRow.proposal_id == proposal_id)
            )
        )
        .scalars()
        .all()
    )
    return [
        Ballot(
            proposal_id=ProposalId(r.proposal_id),
            voter=PodName(r.voter),
            choice=BallotChoice(r.choice),
            comment=r.comment,
            cast_at=_utc(r.cast_at) or utc_now(),
        )
        for r in rows
    ]


async def close_proposal(
    session: AsyncSession,
    *,
    proposal_id: ProposalId,
    outcome: ProposalOutcome,
    adr_id: str | None,
) -> Proposal:
    row = await session.get(ProposalRow, proposal_id)
    if row is None:
        raise KeyError(proposal_id)
    row.outcome = outcome.value
    row.decided_at = utc_now()
    row.adr_id = adr_id
    await session.flush()
    return _to_proposal(row)


def _to_proposal(row: ProposalRow) -> Proposal:
    opened = _utc(row.opened_at) or utc_now()
    deadline = _utc(row.deadline) or opened
    return Proposal(
        id=ProposalId(row.id),
        kind=ProposalKind(row.kind),
        proposer=PodName(row.proposer),
        strategy=VotingStrategy(row.strategy),
        payload=row.payload,
        affected=[PodName(p) for p in row.affected],
        opened_at=opened,
        deadline=deadline,
        outcome=ProposalOutcome(row.outcome) if row.outcome else None,
        decided_at=_utc(row.decided_at),
        adr_id=AdrId(row.adr_id) if row.adr_id else None,
    )


__all__ = [
    "MemberStatus",
    "add_member",
    "cast_ballot",
    "close_proposal",
    "create_proposal",
    "exile_member",
    "get_proposal",
    "list_admitted",
    "list_ballots",
    "list_open_proposals",
]
