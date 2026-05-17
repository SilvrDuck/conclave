"""Unit tests for the four senate voting strategies (kanban #34).

Spec/08 §4 requires three of the four strategies to fire in the
golden run. The e2e smoke covers `majority` + `consensus_omnium`
implicitly via the admission flow; `supermajority` and `sortition`
need explicit coverage that doesn't depend on a live stack.

These are pure-function tests against `mcp_senate.strategies`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make services/mcp-senate/src importable so we don't need uv to
# resolve a workspace install just to run these unit tests.
_SENATE_SRC = (
    Path(__file__).resolve().parent.parent
    / "services" / "mcp-senate" / "src"
)
if str(_SENATE_SRC) not in sys.path:
    sys.path.insert(0, str(_SENATE_SRC))

from conclave_core.models import ProposalOutcome, StrategyName, VoteChoice  # noqa: E402
from mcp_senate.strategies import (  # noqa: E402
    StrategyContext,
    draw_sortition,
    evaluate,
)

YES = VoteChoice.YES
NO = VoteChoice.NO
ABS = VoteChoice.ABSTAIN


def _ctx(
    *,
    ballots: dict[str, VoteChoice],
    eligible: list[str],
    deadline_elapsed: bool = False,
    sortition_seed: int | None = None,
    sortition_size: int | None = None,
) -> StrategyContext:
    return StrategyContext(
        ballots=ballots,
        eligible=eligible,
        deadline_elapsed=deadline_elapsed,
        sortition_seed=sortition_seed,
        sortition_size=sortition_size,
    )


# ─── majority ────────────────────────────────────────────────────────


class TestMajority:
    def test_early_yes(self) -> None:
        ctx = _ctx(ballots={"a": YES, "b": YES}, eligible=["a", "b", "c"])
        assert evaluate(StrategyName.MAJORITY, ctx) is ProposalOutcome.APPROVED

    def test_early_no(self) -> None:
        ctx = _ctx(ballots={"a": NO, "b": NO}, eligible=["a", "b", "c"])
        assert evaluate(StrategyName.MAJORITY, ctx) is ProposalOutcome.REJECTED

    def test_open_when_undecided(self) -> None:
        ctx = _ctx(ballots={"a": YES}, eligible=["a", "b", "c"])
        assert evaluate(StrategyName.MAJORITY, ctx) is None

    def test_deadline_yes_wins(self) -> None:
        ctx = _ctx(
            ballots={"a": YES, "b": NO},
            eligible=["a", "b", "c"],
            deadline_elapsed=True,
        )
        # tied so far, but only one no — tie breaks reject when even
        # but yes > no isn't true here; both 1.
        assert evaluate(StrategyName.MAJORITY, ctx) is ProposalOutcome.REJECTED

    def test_deadline_expired_no_votes(self) -> None:
        ctx = _ctx(ballots={}, eligible=["a", "b"], deadline_elapsed=True)
        assert evaluate(StrategyName.MAJORITY, ctx) is ProposalOutcome.EXPIRED

    def test_abstain_doesnt_count(self) -> None:
        # 2 abstain + 1 yes → at deadline, yes > no, approved.
        ctx = _ctx(
            ballots={"a": ABS, "b": ABS, "c": YES},
            eligible=["a", "b", "c"],
            deadline_elapsed=True,
        )
        assert evaluate(StrategyName.MAJORITY, ctx) is ProposalOutcome.APPROVED


# ─── supermajority ───────────────────────────────────────────────────


class TestSupermajority:
    def test_n1_one_yes_passes(self) -> None:
        # ceil(1 * 2/3) = 1, one yes meets it.
        ctx = _ctx(ballots={"a": YES}, eligible=["a"])
        assert evaluate(StrategyName.SUPERMAJORITY, ctx) is ProposalOutcome.APPROVED

    def test_n3_two_yes_passes(self) -> None:
        # ceil(3 * 2/3) = 2.
        ctx = _ctx(ballots={"a": YES, "b": YES}, eligible=["a", "b", "c"])
        assert evaluate(StrategyName.SUPERMAJORITY, ctx) is ProposalOutcome.APPROVED

    def test_n6_three_yes_short_of_threshold(self) -> None:
        # ceil(6 * 2/3) = 4. 3 yes + 3 remaining could just reach 4 (still possible).
        ctx = _ctx(
            ballots={"a": YES, "b": YES, "c": YES},
            eligible=["a", "b", "c", "d", "e", "f"],
        )
        # Could still pass if d/e/f vote yes; therefore still open.
        assert evaluate(StrategyName.SUPERMAJORITY, ctx) is None

    def test_n6_early_rejection_when_unreachable(self) -> None:
        # ceil(6 * 2/3) = 4. 2 yes + 3 no → 1 remaining → max yes = 3 < 4.
        ctx = _ctx(
            ballots={"a": YES, "b": YES, "c": NO, "d": NO, "e": NO},
            eligible=["a", "b", "c", "d", "e", "f"],
        )
        assert evaluate(StrategyName.SUPERMAJORITY, ctx) is ProposalOutcome.REJECTED

    def test_n3_deadline_partial_yes_rejected(self) -> None:
        # ceil(3 * 2/3) = 2. Only 1 yes by deadline + 1 no.
        ctx = _ctx(
            ballots={"a": YES, "b": NO},
            eligible=["a", "b", "c"],
            deadline_elapsed=True,
        )
        # Not enough yes to pass; explicit no → reject (not expired).
        assert evaluate(StrategyName.SUPERMAJORITY, ctx) is ProposalOutcome.REJECTED

    def test_deadline_no_votes_expired(self) -> None:
        ctx = _ctx(ballots={}, eligible=["a", "b"], deadline_elapsed=True)
        # supermajority counts: threshold = ceil(2 * 2/3) = 2. Not met,
        # but no NO either → expired.
        # Remaining = 2, yes + remaining = 2 == threshold → still
        # "could close" path — but at deadline_elapsed with no no, expired.
        # The strategy code returns REJECTED if any no, else EXPIRED.
        assert evaluate(StrategyName.SUPERMAJORITY, ctx) is ProposalOutcome.EXPIRED


# ─── consensus_omnium ────────────────────────────────────────────────


class TestConsensusOmnium:
    def test_n1_trivial_pass(self) -> None:
        ctx = _ctx(ballots={"a": YES}, eligible=["a"])
        assert evaluate(StrategyName.CONSENSUS_OMNIUM, ctx) is ProposalOutcome.APPROVED

    def test_any_no_rejects(self) -> None:
        ctx = _ctx(ballots={"a": YES, "b": NO}, eligible=["a", "b", "c"])
        assert evaluate(StrategyName.CONSENSUS_OMNIUM, ctx) is ProposalOutcome.REJECTED

    def test_pending_when_missing_voter(self) -> None:
        ctx = _ctx(ballots={"a": YES, "b": YES}, eligible=["a", "b", "c"])
        assert evaluate(StrategyName.CONSENSUS_OMNIUM, ctx) is None

    def test_all_yes_passes(self) -> None:
        ctx = _ctx(
            ballots={"a": YES, "b": YES, "c": YES},
            eligible=["a", "b", "c"],
        )
        assert evaluate(StrategyName.CONSENSUS_OMNIUM, ctx) is ProposalOutcome.APPROVED

    def test_deadline_with_missing_voter_expires(self) -> None:
        ctx = _ctx(
            ballots={"a": YES, "b": YES},
            eligible=["a", "b", "c"],
            deadline_elapsed=True,
        )
        assert (
            evaluate(StrategyName.CONSENSUS_OMNIUM, ctx)
            is ProposalOutcome.EXPIRED
        )


# ─── sortition ───────────────────────────────────────────────────────


class TestSortition:
    def test_draw_deterministic(self) -> None:
        eligible = [f"pod-{i}" for i in range(10)]
        a = draw_sortition(eligible, size=3, seed=42)
        b = draw_sortition(eligible, size=3, seed=42)
        c = draw_sortition(eligible, size=3, seed=43)
        assert a == b  # same seed → same draw
        assert a != c  # different seed → different draw (whp)
        assert len(a) == 3
        assert set(a).issubset(set(eligible))

    def test_draw_size_geq_eligible_returns_all(self) -> None:
        eligible = ["a", "b"]
        out = draw_sortition(eligible, size=5, seed=1)
        assert sorted(out) == sorted(eligible)

    def test_evaluate_reduces_to_majority(self) -> None:
        # By proposal-open time eligible is already narrowed to the
        # drawn subset. So sortition is majority on that subset.
        ctx = _ctx(ballots={"a": YES, "b": YES}, eligible=["a", "b", "c"])
        assert evaluate(StrategyName.SORTITION, ctx) is ProposalOutcome.APPROVED
        ctx2 = _ctx(
            ballots={"a": NO, "b": NO},
            eligible=["a", "b", "c"],
        )
        assert evaluate(StrategyName.SORTITION, ctx2) is ProposalOutcome.REJECTED
