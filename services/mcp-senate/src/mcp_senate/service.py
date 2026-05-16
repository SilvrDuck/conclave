"""SenateService — actual writes to the `senate` schema and event emission.

Shared by both the MCP tools (called by pod agents) and the bus subscriber
(commands routed via the observer/Forum). The MCP server process owns
this schema's writes; no other process writes here.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg
from conclave_core import Bus
from conclave_core.events import BallotCast, ProposalClosed, ProposalOpened
from conclave_core.models import (
    ProposalKind,
    StrategyName,
    VoteChoice,
)

from mcp_senate.strategies import (
    StrategyContext,
    draw_sortition,
    evaluate,
)

log = logging.getLogger("mcp-senate.service")

SENATE_CONTEXT = "senate"
DEFAULT_DEADLINE = timedelta(minutes=5)


def _affected_for(kind: str, payload: dict[str, Any]) -> list[str]:
    """Compute `ProposalClosed.affected` from the proposal's kind + payload.

    Downstream policies key off `affected` — Pod Lifecycle for admission /
    exile / image_swap; Decisions for contract_change; Operator (proclamation
    completion) for completion. None of them want the electorate.
    """
    match kind:
        case ProposalKind.ADMISSION.value | ProposalKind.EXILE.value | ProposalKind.IMAGE_SWAP.value:
            pid = payload.get("pod_id")
            return [pid] if pid else []
        case ProposalKind.CONTRACT_CHANGE.value:
            # The endpoints' owning pods are what downstream needs.
            endpoints = payload.get("endpoints") or []
            pods = {
                e.get("pod_id") for e in endpoints if isinstance(e, dict) and e.get("pod_id")
            }
            return sorted(pods)
        case ProposalKind.COMPLETION.value:
            seq = payload.get("proclamation_seq")
            return [f"proclamation:{seq}"] if seq is not None else []
        case _:
            return []


@dataclass(frozen=True)
class ProposalArgs:
    kind: ProposalKind
    proposer: str
    strategy: StrategyName
    summary: str
    payload: dict[str, Any]
    eligible: list[str]
    sortition_size: int | None = None
    deadline: timedelta = DEFAULT_DEADLINE


class SenateService:
    def __init__(self, *, pool: asyncpg.Pool, bus: Bus) -> None:
        self._pool = pool
        self._bus = bus

    # ─── propose ────────────────────────────────────────────────────────

    async def open_proposal(self, args: ProposalArgs) -> str:
        """Create and broadcast a new proposal. Returns the proposal_id.

        Sortition strategies narrow `eligible` at open time so subsequent
        evaluations don't have to re-draw.
        """
        proposal_id = f"prop-{secrets.token_hex(6)}"
        if not args.summary.strip():
            raise ValueError("proposal summary must be non-empty")
        if args.proposer not in args.eligible and args.kind != ProposalKind.ADMISSION:
            # admission proposers may not be admitted yet
            log.info("proposer %s not in eligible voters (allowed for kind=%s)",
                     args.proposer, args.kind)

        eligible = list(args.eligible)
        if args.strategy is StrategyName.SORTITION:
            size = args.sortition_size or max(3, (len(eligible) + 1) // 2)
            seed = secrets.randbits(63)
            eligible = draw_sortition(eligible, size, seed)
            payload = {**args.payload, "_sortition_seed": seed, "_sortition_size": size}
        else:
            payload = args.payload

        deadline_at = datetime.now(UTC) + args.deadline

        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO senate.proposals(proposal_id, kind, proposer, strategy,
                       summary, payload, eligible_voters, deadline)
                   VALUES($1, $2, $3, $4, $5, $6::jsonb, $7, $8)""",
                proposal_id,
                args.kind.value,
                args.proposer,
                args.strategy.value,
                args.summary,
                payload,
                eligible,
                deadline_at,
            )

        await self._bus.publish_event(
            ProposalOpened(
                proposal_id=proposal_id,
                kind=args.kind,
                proposer=args.proposer,
                strategy=args.strategy,
                summary=args.summary,
                payload=payload,
                eligible_voters=eligible,
                deadline=deadline_at,
            ),
            SENATE_CONTEXT,
        )
        log.info(
            "ProposalOpened %s kind=%s strategy=%s eligible=%d",
            proposal_id, args.kind, args.strategy, len(eligible),
        )

        # Proposer typically endorses their own proposal — auto-cast a YES
        # if they're among the eligible voters. Honors N=1 trivial pass.
        if args.proposer in eligible:
            await self.cast_ballot(
                proposal_id=proposal_id,
                voter=args.proposer,
                choice=VoteChoice.YES,
                comment="auto: proposer endorsement",
            )

        return proposal_id

    # ─── cast ballot ────────────────────────────────────────────────────

    async def cast_ballot(
        self,
        *,
        proposal_id: str,
        voter: str,
        choice: VoteChoice,
        comment: str | None = None,
    ) -> None:
        # All reads + inserts in one txn so FOR UPDATE actually holds the lock.
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """SELECT outcome, eligible_voters
                         FROM senate.proposals WHERE proposal_id = $1
                         FOR UPDATE""",
                    proposal_id,
                )
                if row is None:
                    raise ValueError(f"unknown proposal_id: {proposal_id}")
                if row["outcome"] != "open":
                    raise ValueError(
                        f"proposal {proposal_id} is already {row['outcome']}"
                    )
                if voter not in row["eligible_voters"]:
                    raise ValueError(f"voter {voter} not eligible for {proposal_id}")
                await conn.execute(
                    """INSERT INTO senate.ballots(proposal_id, voter, choice, comment)
                       VALUES($1, $2, $3, $4)
                       ON CONFLICT (proposal_id, voter) DO NOTHING""",
                    proposal_id,
                    voter,
                    choice.value,
                    comment,
                )
        await self._bus.publish_event(
            BallotCast(
                proposal_id=proposal_id, voter=voter, choice=choice, comment=comment
            ),
            SENATE_CONTEXT,
        )
        log.info("BallotCast %s voter=%s choice=%s", proposal_id, voter, choice)

        # Re-evaluate strategy after every ballot — early close if decided.
        await self._maybe_close(proposal_id, deadline_elapsed=False)

    # ─── close ───────────────────────────────────────────────────────────

    async def close_overdue(self) -> int:
        """Close every proposal past its deadline. Returns the count closed."""
        now = datetime.now(UTC)
        async with self._pool.acquire() as conn:
            overdue = await conn.fetch(
                """SELECT proposal_id FROM senate.proposals
                     WHERE outcome = 'open' AND deadline <= $1""",
                now,
            )
        for r in overdue:
            try:
                await self._maybe_close(r["proposal_id"], deadline_elapsed=True)
            except Exception:
                log.exception("close_overdue failed for %s", r["proposal_id"])
        return len(overdue)

    async def _maybe_close(self, proposal_id: str, *, deadline_elapsed: bool) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """SELECT kind, strategy, summary, eligible_voters, payload, outcome
                         FROM senate.proposals WHERE proposal_id = $1 FOR UPDATE""",
                    proposal_id,
                )
                if row is None or row["outcome"] != "open":
                    return

                ballots = await conn.fetch(
                    "SELECT voter, choice FROM senate.ballots WHERE proposal_id = $1",
                    proposal_id,
                )
                ballot_map = {b["voter"]: VoteChoice(b["choice"]) for b in ballots}
                strategy = StrategyName(row["strategy"])
                payload = row["payload"] or {}
                ctx = StrategyContext(
                    ballots=ballot_map,
                    eligible=list(row["eligible_voters"]),
                    deadline_elapsed=deadline_elapsed,
                    sortition_seed=payload.get("_sortition_seed"),
                    sortition_size=payload.get("_sortition_size"),
                )
                outcome = evaluate(strategy, ctx)
                if outcome is None:
                    return

                await conn.execute(
                    """UPDATE senate.proposals
                          SET outcome = $2, closed_at = now()
                        WHERE proposal_id = $1""",
                    proposal_id,
                    outcome.value,
                )

                # affected = whoever this proposal *changes*, not who voted on it.
                # Spec §C2: downstream policies (Pod Lifecycle on admission/exile,
                # Decisions on contract changes, Operator on completion) key off
                # `affected`. Eligible voters are tracked separately on the
                # proposal itself.
                affected = _affected_for(row["kind"], payload)

        await self._bus.publish_event(
            ProposalClosed(
                proposal_id=proposal_id,
                outcome=outcome,
                summary=row["summary"],
                affected=affected,
            ),
            SENATE_CONTEXT,
        )
        log.info("ProposalClosed %s outcome=%s", proposal_id, outcome)

    # ─── reads ──────────────────────────────────────────────────────────

    async def list_open_proposals(self) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT proposal_id, kind, proposer, strategy, summary,
                          eligible_voters, deadline
                     FROM senate.proposals WHERE outcome = 'open'
                     ORDER BY deadline ASC"""
            )
        return [
            {
                "proposal_id": r["proposal_id"],
                "kind": r["kind"],
                "proposer": r["proposer"],
                "strategy": r["strategy"],
                "summary": r["summary"],
                "eligible_voters": list(r["eligible_voters"]),
                "deadline": r["deadline"].isoformat(),
            }
            for r in rows
        ]

    async def outcome(self, proposal_id: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            r = await conn.fetchrow(
                """SELECT outcome, summary, closed_at
                     FROM senate.proposals WHERE proposal_id = $1""",
                proposal_id,
            )
        if r is None:
            return None
        return {
            "outcome": r["outcome"],
            "summary": r["summary"],
            "closed_at": r["closed_at"].isoformat() if r["closed_at"] else None,
        }
