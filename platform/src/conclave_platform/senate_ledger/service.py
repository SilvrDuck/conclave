"""Senate business logic — eligible-voter computation, strategy evaluation, side-effects."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters import BusAdapter, DocsAdapter
from ..core import (
    BallotChoice,
    EventEnvelope,
    PodName,
    Proposal,
    ProposalKind,
    ProposalOutcome,
    VoteClosed,
    VoteOpen,
    VotingStrategy,
    pod_inbox_topic,
    utc_now,
)
from ..core.events import SYSTEM_OBSERVER_TOPIC
from ..core.ids import EndpointKey, ProposalId
from . import repository as repo
from .observer_client import ObserverClient
from .strategies import StrategyContext, StrategyResult, draw_sortition_panel, evaluate

if TYPE_CHECKING:
    pass

log = structlog.get_logger(__name__)


@dataclass
class ProposeInput:
    kind: ProposalKind
    proposer: PodName
    strategy: VotingStrategy
    payload: dict[str, object]
    rationale: str
    affected_override: list[PodName] | None
    deadline_seconds: int


def _new_id() -> ProposalId:
    return ProposalId(f"p-{uuid.uuid4().hex[:10]}")


async def _compute_eligible_voters(
    session: AsyncSession,
    observer: ObserverClient,
    *,
    kind: ProposalKind,
    proposer: PodName,
    payload: dict[str, object],
    override: list[PodName] | None,
) -> tuple[list[PodName], list[PodName]]:
    """Return (voters, affected). For contract_change, voters = consumers of the
    endpoint(s); for everything else, voters = current admitted members."""
    members = await repo.list_admitted(session)
    if not members:  # senate bootstrapping with empty ledger — trust observer
        members = await observer.list_admitted_members()
    if override is not None:
        return override, override
    if kind == ProposalKind.contract_change:
        endpoints_raw = payload.get("endpoints", [])
        if not isinstance(endpoints_raw, list):
            raise ValueError("contract_change requires payload.endpoints: list[str]")
        callers: set[PodName] = set()
        for ek in endpoints_raw:
            method, _, path = str(ek).partition(" ")
            callers.update(await observer.callers_of(method=method, path=path))
        affected = sorted({proposer, *callers})
        return affected, affected
    if kind == ProposalKind.member:
        # All admitted members vote; proposer included.
        voters = sorted({proposer, *members})
        return voters, [proposer]
    if kind == ProposalKind.exile:
        target_raw = payload.get("pod_name")
        target = PodName(str(target_raw)) if target_raw else None
        voters = [m for m in members if m != target]
        return voters, [target] if target else []
    if kind == ProposalKind.revival:
        return sorted(members), members
    if kind == ProposalKind.completion:
        return sorted(members), members
    raise ValueError(f"unknown kind {kind}")


async def propose(
    session: AsyncSession,
    *,
    observer: ObserverClient,
    bus: BusAdapter | None,
    inp: ProposeInput,
) -> Proposal:
    voters, affected = await _compute_eligible_voters(
        session,
        observer,
        kind=inp.kind,
        proposer=inp.proposer,
        payload=inp.payload,
        override=inp.affected_override,
    )
    proposal_id = _new_id()
    pool = None
    if inp.strategy == VotingStrategy.sortition:
        pool = draw_sortition_panel(proposal_id=proposal_id, voters=voters)
    deadline = utc_now() + timedelta(seconds=inp.deadline_seconds)
    proposal = await repo.create_proposal(
        session,
        proposal_id=proposal_id,
        kind=inp.kind,
        proposer=inp.proposer,
        strategy=inp.strategy,
        payload=inp.payload,
        affected=affected,
        deadline=deadline,
        sortition_pool=pool,
    )
    if bus is not None:
        await _emit_vote_open(bus, proposal, voters, rationale=inp.rationale)
    # N=1 trivial-pass auto-decide (founder bootstrap)
    if len(voters) == 1 and voters[0] == inp.proposer:
        await repo.cast_ballot(
            session,
            proposal_id=proposal_id,
            voter=voters[0],
            choice=BallotChoice.yes,
            comment="N=1 self-yes (auto)",
        )
    return proposal


async def cast_and_maybe_close(
    session: AsyncSession,
    *,
    observer: ObserverClient,
    docs: DocsAdapter,
    bus: BusAdapter | None,
    proposal_id: ProposalId,
    voter: PodName,
    choice: BallotChoice,
    comment: str | None,
) -> tuple[Proposal, StrategyResult]:
    proposal = await repo.get_proposal(session, proposal_id)
    if proposal is None:
        raise KeyError(proposal_id)
    if proposal.outcome is not None:
        return proposal, StrategyResult(
            decided=True, outcome=proposal.outcome, reason="already closed"
        )
    await repo.cast_ballot(
        session, proposal_id=proposal_id, voter=voter, choice=choice, comment=comment
    )
    return await _reevaluate(
        session, observer=observer, docs=docs, bus=bus, proposal_id=proposal_id
    )


async def _reevaluate(
    session: AsyncSession,
    *,
    observer: ObserverClient,
    docs: DocsAdapter,
    bus: BusAdapter | None,
    proposal_id: ProposalId,
) -> tuple[Proposal, StrategyResult]:
    proposal = await repo.get_proposal(session, proposal_id)
    if proposal is None:
        raise KeyError(proposal_id)
    ballots = await repo.list_ballots(session, proposal_id)
    voters, _affected = await _compute_eligible_voters(
        session,
        observer,
        kind=proposal.kind,
        proposer=proposal.proposer,
        payload=proposal.payload,  # type: ignore[arg-type]
        override=proposal.affected if proposal.kind == ProposalKind.contract_change else None,
    )
    sortition_voters = (
        [PodName(p) for p in proposal.affected]
        if proposal.strategy == VotingStrategy.sortition
        else None
    )
    ctx = StrategyContext(
        proposal_id=proposal_id,
        voters=voters,
        deadline=proposal.deadline,
        now=utc_now(),
        sortition_pool=sortition_voters,
    )
    result = evaluate(proposal.strategy, ballots, ctx)
    if not result.decided:
        return proposal, result
    adr_id: str | None = None
    if result.outcome == ProposalOutcome.approved:
        adr_id = await _approve_side_effects(
            session,
            docs=docs,
            observer=observer,
            proposal=proposal,
            reason=result.reason,
        )
    elif result.outcome == ProposalOutcome.rejected:
        adr_id = await docs.write_adr(
            title=f"[rejected] {proposal.kind.value}: {proposal.id}",
            body=f"Rejected. Reason: {result.reason}",
            affected_pods=proposal.affected,
            proposal_id=proposal.id,
        )
    closed = await repo.close_proposal(
        session,
        proposal_id=proposal_id,
        outcome=result.outcome or ProposalOutcome.timeout,
        adr_id=adr_id,
    )
    if bus is not None:
        await _emit_vote_closed(bus, closed)
    return closed, result


async def _approve_side_effects(
    session: AsyncSession,
    *,
    docs: DocsAdapter,
    observer: ObserverClient,
    proposal: Proposal,
    reason: str,
) -> str:
    title_prefix = {
        ProposalKind.member: "ADR: admit",
        ProposalKind.exile: "ADR: exile",
        ProposalKind.revival: "ADR: revive",
        ProposalKind.contract_change: "ADR: contract change",
        ProposalKind.completion: "ADR: completion",
    }
    body = _render_adr_body(proposal, reason)
    adr_id = await docs.write_adr(
        title=f"{title_prefix[proposal.kind]} ({proposal.id})",
        body=body,
        affected_pods=proposal.affected,
        proposal_id=proposal.id,
    )
    if proposal.kind == ProposalKind.member:
        target = proposal.payload.get("pod_name")
        if target:
            target_pod = PodName(str(target))
            await repo.add_member(session, target_pod)
            charter = str(
                proposal.payload.get("charter_path") or f"pods/{target_pod}/charter.md"
            )
            try:
                await observer.upsert_member(
                    name=target_pod, charter_path=charter, status="admitted"
                )
            except Exception as exc:
                log.warning("senate.observer_mirror_failed", pod=target_pod, exc=str(exc))
    elif proposal.kind == ProposalKind.exile:
        target = proposal.payload.get("pod_name")
        if target:
            target_pod = PodName(str(target))
            await repo.exile_member(session, target_pod)
            try:
                await observer.upsert_member(
                    name=target_pod,
                    charter_path=f"pods/{target_pod}/charter.md",
                    status="exiled",
                )
            except Exception as exc:
                log.warning("senate.observer_mirror_failed", pod=target_pod, exc=str(exc))
    return adr_id


def _render_adr_body(proposal: Proposal, reason: str) -> str:
    return (
        f"# {proposal.kind.value} — {proposal.id}\n\n"
        f"**Proposer**: {proposal.proposer}\n"
        f"**Strategy**: {proposal.strategy.value}\n"
        f"**Affected**: {', '.join(proposal.affected) or '(none)'}\n\n"
        f"## Outcome\n\n{reason}\n\n"
        f"## Payload\n\n```json\n{proposal.payload}\n```\n"
    )


async def _emit_vote_open(
    bus: BusAdapter,
    proposal: Proposal,
    voters: list[PodName],
    *,
    rationale: str,
) -> None:
    envelope = EventEnvelope(
        event=VoteOpen(
            proposal_id=proposal.id,
            kind=proposal.kind.value,
            proposer=proposal.proposer,
            rationale=rationale,
        )
    )
    payload = envelope.model_dump_json().encode()
    for voter in voters:
        # Each voter event is targeted; harness routes from inbox topic.
        targeted = EventEnvelope(
            event=VoteOpen(
                target_pod=voter,
                proposal_id=proposal.id,
                kind=proposal.kind.value,
                proposer=proposal.proposer,
                rationale=rationale,
            )
        )
        await bus.publish(pod_inbox_topic(voter), targeted.model_dump_json().encode())
    await bus.publish(f"{SYSTEM_OBSERVER_TOPIC}/vote_open", payload)


async def _emit_vote_closed(bus: BusAdapter, proposal: Proposal) -> None:
    outcome = proposal.outcome.value if proposal.outcome else "open"
    envelope = EventEnvelope(
        event=VoteClosed(proposal_id=proposal.id, outcome=outcome)
    )
    payload = envelope.model_dump_json().encode()
    for voter in proposal.affected:
        targeted = EventEnvelope(
            event=VoteClosed(
                target_pod=voter, proposal_id=proposal.id, outcome=outcome
            )
        )
        await bus.publish(pod_inbox_topic(voter), targeted.model_dump_json().encode())
    await bus.publish(f"{SYSTEM_OBSERVER_TOPIC}/vote_closed", payload)


__all__ = [
    "ProposeInput",
    "cast_and_maybe_close",
    "propose",
]


def _endpoint_label(_: EndpointKey) -> str:
    return str(_)
