"""Voting strategies — pure functions over (ballots, eligible, options).

A strategy returns either the resolved `ProposalOutcome` or `None` (still
open). The senate calls the strategy after every ballot and once at the
deadline. Adding a strategy means adding one entry to `STRATEGIES` and the
function — no senate-core changes.

Spec ref: spec/02-event-storming.md Phase 3, spec/06-atam.md S4 + M1.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from conclave_core.models import ProposalOutcome, StrategyName, VoteChoice

SUPERMAJORITY_RATIO = 2 / 3


@dataclass(frozen=True)
class StrategyContext:
    """Inputs every strategy needs.

    `ballots`        — dict {voter: VoteChoice}.
    `eligible`       — list of voters eligible at proposal-open time.
    `deadline_elapsed` — True iff the deadline reactor is closing this.
    `sortition_seed` — optional seed for reproducible sortition draws.
    `sortition_size` — for `sortition` strategy, the subset size.
    """

    ballots: dict[str, VoteChoice]
    eligible: list[str]
    deadline_elapsed: bool = False
    sortition_seed: int | None = None
    sortition_size: int | None = None


def evaluate(name: StrategyName, ctx: StrategyContext) -> ProposalOutcome | None:
    return STRATEGIES[name](ctx)


def draw_sortition(eligible: list[str], size: int, seed: int) -> list[str]:
    """Deterministic sortition draw, recorded at proposal open time."""
    if size >= len(eligible):
        return list(eligible)
    rng = random.Random(seed)
    return sorted(rng.sample(eligible, size))


# ─── strategies ────────────────────────────────────────────────────────


def _majority(ctx: StrategyContext) -> ProposalOutcome | None:
    eligible = ctx.eligible
    if not eligible:
        return ProposalOutcome.EXPIRED  # nobody to vote → nothing to approve
    ballots = ctx.ballots
    yes = sum(1 for v in ballots.values() if v == VoteChoice.YES)
    no = sum(1 for v in ballots.values() if v == VoteChoice.NO)
    cast = yes + no  # abstain doesn't count toward majority

    if ctx.deadline_elapsed:
        if cast == 0:
            return ProposalOutcome.EXPIRED
        return ProposalOutcome.APPROVED if yes > no else ProposalOutcome.REJECTED

    # Early close once a side passes half of eligible — irreversible.
    half = len(eligible) // 2
    if yes > half:
        return ProposalOutcome.APPROVED
    if no > half:
        return ProposalOutcome.REJECTED
    return None


def _supermajority(ctx: StrategyContext) -> ProposalOutcome | None:
    eligible = ctx.eligible
    if not eligible:
        return ProposalOutcome.EXPIRED
    ballots = ctx.ballots
    yes = sum(1 for v in ballots.values() if v == VoteChoice.YES)
    no = sum(1 for v in ballots.values() if v == VoteChoice.NO)
    threshold = int(len(eligible) * SUPERMAJORITY_RATIO) + 1

    if yes >= threshold:
        return ProposalOutcome.APPROVED
    # If even all remaining ballots were YES we couldn't hit threshold → reject.
    remaining = len(eligible) - len(ballots)
    if yes + remaining < threshold:
        return ProposalOutcome.REJECTED

    if ctx.deadline_elapsed:
        # By definition we haven't hit the YES threshold here.
        return ProposalOutcome.REJECTED if no else ProposalOutcome.EXPIRED
    return None


def _consensus_omnium(ctx: StrategyContext) -> ProposalOutcome | None:
    eligible = ctx.eligible
    if not eligible:
        return ProposalOutcome.EXPIRED
    ballots = ctx.ballots
    if any(v == VoteChoice.NO for v in ballots.values()):
        return ProposalOutcome.REJECTED
    # All eligible must vote YES.
    yes_set = {v for v, choice in ballots.items() if choice == VoteChoice.YES}
    if set(eligible).issubset(yes_set):
        return ProposalOutcome.APPROVED
    if ctx.deadline_elapsed:
        return ProposalOutcome.EXPIRED
    return None


def _sortition(ctx: StrategyContext) -> ProposalOutcome | None:
    # By the time we get here, `eligible` was already narrowed to the drawn
    # subset at proposal-open time. So sortition reduces to majority.
    return _majority(ctx)


STRATEGIES = {
    StrategyName.MAJORITY: _majority,
    StrategyName.SUPERMAJORITY: _supermajority,
    StrategyName.CONSENSUS_OMNIUM: _consensus_omnium,
    StrategyName.SORTITION: _sortition,
}
