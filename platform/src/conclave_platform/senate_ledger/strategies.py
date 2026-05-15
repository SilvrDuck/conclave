"""Voting strategies — pure functions over (ballots, voters, context) → result.

Adding a strategy = one function + an entry in `_STRATEGIES`. Each strategy
encapsulates its own quorum, threshold, and timeout policy.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from ..core import Ballot, BallotChoice, PodName, ProposalOutcome, VotingStrategy


@dataclass(frozen=True, slots=True)
class StrategyContext:
    proposal_id: str
    voters: list[PodName]  # eligible voters for this proposal
    deadline: datetime
    now: datetime
    # For sortition: deterministic sample drawn at proposal creation.
    sortition_pool: list[PodName] | None = None


@dataclass(frozen=True, slots=True)
class StrategyResult:
    decided: bool
    outcome: ProposalOutcome | None
    reason: str

    @classmethod
    def open(cls, reason: str = "") -> StrategyResult:
        return cls(decided=False, outcome=None, reason=reason)

    @classmethod
    def approve(cls, reason: str) -> StrategyResult:
        return cls(decided=True, outcome=ProposalOutcome.approved, reason=reason)

    @classmethod
    def reject(cls, reason: str) -> StrategyResult:
        return cls(decided=True, outcome=ProposalOutcome.rejected, reason=reason)

    @classmethod
    def timeout(cls, reason: str = "deadline elapsed") -> StrategyResult:
        return cls(decided=True, outcome=ProposalOutcome.timeout, reason=reason)


Strategy = Callable[[list[Ballot], StrategyContext], StrategyResult]


def _tally(ballots: list[Ballot]) -> tuple[int, int, int]:
    yes = sum(b.choice == BallotChoice.yes for b in ballots)
    no = sum(b.choice == BallotChoice.no for b in ballots)
    abstain = sum(b.choice == BallotChoice.abstain for b in ballots)
    return yes, no, abstain


def majority(ballots: list[Ballot], ctx: StrategyContext) -> StrategyResult:  # noqa: PLR0911
    """> 50% yes among those who voted, with at least 50% turnout. Abstentions
    count toward turnout but not toward yes/no."""
    eligible = len(ctx.voters)
    yes, no, abstain = _tally(ballots)
    turnout = yes + no + abstain
    if eligible == 0:
        return StrategyResult.reject("no eligible voters")
    if eligible == 1:
        if yes == 1:
            return StrategyResult.approve("N=1 trivial pass")
        if no == 1:
            return StrategyResult.reject("N=1 self-reject")
    decided_threshold = (yes - no) > 0
    quorum_met = turnout * 2 >= eligible
    if quorum_met and decided_threshold and yes > no:
        return StrategyResult.approve(f"{yes}>{no}, turnout={turnout}/{eligible}")
    if quorum_met and no >= yes and (yes + (eligible - turnout)) < no + 1:
        return StrategyResult.reject(f"yes={yes} cannot exceed no={no}")
    if ctx.now >= ctx.deadline:
        return StrategyResult.timeout()
    return StrategyResult.open(f"waiting: yes={yes} no={no} eligible={eligible}")


def supermajority(ballots: list[Ballot], ctx: StrategyContext) -> StrategyResult:
    """≥ 2/3 yes of *all eligible voters*. Strict — abstentions don't help."""
    eligible = len(ctx.voters)
    yes, no, _abstain = _tally(ballots)
    if eligible == 0:
        return StrategyResult.reject("no eligible voters")
    threshold = (2 * eligible + 2) // 3  # ceil(2/3 * eligible)
    remaining = eligible - len(ballots)
    if yes >= threshold:
        return StrategyResult.approve(f"{yes}/{eligible} >= 2/3")
    # Even if all remaining voted yes, still can't reach threshold.
    blocked = no + (eligible - yes - no - _abstain) > eligible - threshold
    if blocked and yes + remaining < threshold:
        return StrategyResult.reject(
            f"unreachable: yes={yes}, remaining={remaining}, threshold={threshold}"
        )
    if ctx.now >= ctx.deadline:
        return StrategyResult.timeout()
    return StrategyResult.open(
        f"waiting: yes={yes}/{eligible}, threshold={threshold}"
    )


def consensus_omnium(ballots: list[Ballot], ctx: StrategyContext) -> StrategyResult:
    """All eligible voters must vote yes. Any `no` → reject immediately."""
    yes, no, _abstain = _tally(ballots)
    eligible = len(ctx.voters)
    if no > 0:
        return StrategyResult.reject(f"{no} dissent")
    if yes == eligible and eligible > 0:
        return StrategyResult.approve("unanimous")
    if ctx.now >= ctx.deadline:
        return StrategyResult.timeout("deadline elapsed without consensus")
    return StrategyResult.open(f"waiting: yes={yes}/{eligible}")


def sortition(ballots: list[Ballot], ctx: StrategyContext) -> StrategyResult:
    """Majority of a randomly-chosen panel (pool drawn at proposal creation)."""
    pool = ctx.sortition_pool or ctx.voters
    panel_ballots = [b for b in ballots if b.voter in pool]
    sub_ctx = StrategyContext(
        proposal_id=ctx.proposal_id,
        voters=pool,
        deadline=ctx.deadline,
        now=ctx.now,
    )
    return majority(panel_ballots, sub_ctx)


def draw_sortition_panel(
    *,
    proposal_id: str,
    voters: list[PodName],
    size: int = 3,
) -> list[PodName]:
    """Deterministic per-proposal panel — same proposal always picks the same N."""
    seed = int(hashlib.sha256(proposal_id.encode()).hexdigest(), 16)
    rng = random.Random(seed)  # noqa: S311 — deterministic seeding, not crypto
    return rng.sample(sorted(voters), k=min(size, len(voters)))


_STRATEGIES: dict[VotingStrategy, Strategy] = {
    VotingStrategy.majority: majority,
    VotingStrategy.supermajority: supermajority,
    VotingStrategy.consensus_omnium: consensus_omnium,
    VotingStrategy.sortition: sortition,
}


def evaluate(
    strategy: VotingStrategy,
    ballots: list[Ballot],
    ctx: StrategyContext,
) -> StrategyResult:
    return _STRATEGIES[strategy](ballots, ctx)


__all__ = [
    "Strategy",
    "StrategyContext",
    "StrategyResult",
    "consensus_omnium",
    "draw_sortition_panel",
    "evaluate",
    "majority",
    "sortition",
    "supermajority",
]
