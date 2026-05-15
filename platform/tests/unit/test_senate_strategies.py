"""Voting strategy unit tests — synthetic ballot streams."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from conclave_platform.core import (
    Ballot,
    BallotChoice,
    PodName,
    ProposalOutcome,
    VotingStrategy,
)
from conclave_platform.core.ids import ProposalId
from conclave_platform.senate_ledger.strategies import (
    StrategyContext,
    consensus_omnium,
    draw_sortition_panel,
    evaluate,
    majority,
    sortition,
    supermajority,
)


def _ballot(voter: str, choice: BallotChoice) -> Ballot:
    return Ballot(
        proposal_id=ProposalId("p-1"),
        voter=PodName(voter),
        choice=choice,
        cast_at=datetime(2026, 5, 15, tzinfo=UTC),
    )


def _ctx(voters: list[str], **kw: object) -> StrategyContext:
    return StrategyContext(
        proposal_id="p-1",
        voters=[PodName(v) for v in voters],
        deadline=datetime(2030, 1, 1, tzinfo=UTC),
        now=datetime(2026, 5, 15, tzinfo=UTC),
        **kw,  # type: ignore[arg-type]
    )


# --- majority ---


def test_majority_n1_pass() -> None:
    r = majority([_ballot("alice", BallotChoice.yes)], _ctx(["alice"]))
    assert r.decided and r.outcome == ProposalOutcome.approved


def test_majority_n3_two_yes_passes() -> None:
    r = majority(
        [
            _ballot("alice", BallotChoice.yes),
            _ballot("bob", BallotChoice.yes),
            _ballot("carol", BallotChoice.no),
        ],
        _ctx(["alice", "bob", "carol"]),
    )
    assert r.decided and r.outcome == ProposalOutcome.approved


def test_majority_no_quorum_stays_open() -> None:
    r = majority(
        [_ballot("alice", BallotChoice.yes)],
        _ctx(["alice", "bob", "carol", "dave"]),
    )
    assert not r.decided


def test_majority_timeout() -> None:
    past = StrategyContext(
        proposal_id="p-1",
        voters=[PodName("alice"), PodName("bob")],
        deadline=datetime(2026, 5, 14, tzinfo=UTC),
        now=datetime(2026, 5, 15, tzinfo=UTC),
    )
    r = majority([], past)
    assert r.decided and r.outcome == ProposalOutcome.timeout


# --- supermajority ---


def test_supermajority_two_thirds_of_three() -> None:
    # 2/3 of 3 → ceil = 2
    r = supermajority(
        [
            _ballot("alice", BallotChoice.yes),
            _ballot("bob", BallotChoice.yes),
            _ballot("carol", BallotChoice.no),
        ],
        _ctx(["alice", "bob", "carol"]),
    )
    assert r.decided and r.outcome == ProposalOutcome.approved


def test_supermajority_one_short() -> None:
    # 2/3 of 4 → ceil(8/3) = 3 yes needed.
    r = supermajority(
        [
            _ballot("alice", BallotChoice.yes),
            _ballot("bob", BallotChoice.yes),
            _ballot("carol", BallotChoice.no),
            _ballot("dave", BallotChoice.no),
        ],
        _ctx(["alice", "bob", "carol", "dave"]),
    )
    assert r.decided and r.outcome == ProposalOutcome.rejected


def test_supermajority_partial_stays_open() -> None:
    r = supermajority(
        [_ballot("alice", BallotChoice.yes)],
        _ctx(["alice", "bob", "carol", "dave"]),
    )
    assert not r.decided


# --- consensus_omnium ---


def test_consensus_omnium_single_no_rejects() -> None:
    r = consensus_omnium(
        [
            _ballot("alice", BallotChoice.yes),
            _ballot("bob", BallotChoice.no),
        ],
        _ctx(["alice", "bob", "carol"]),
    )
    assert r.decided and r.outcome == ProposalOutcome.rejected


def test_consensus_omnium_unanimous_approves() -> None:
    r = consensus_omnium(
        [
            _ballot("alice", BallotChoice.yes),
            _ballot("bob", BallotChoice.yes),
        ],
        _ctx(["alice", "bob"]),
    )
    assert r.decided and r.outcome == ProposalOutcome.approved


def test_consensus_omnium_pending_stays_open() -> None:
    r = consensus_omnium(
        [_ballot("alice", BallotChoice.yes)],
        _ctx(["alice", "bob"]),
    )
    assert not r.decided


# --- sortition ---


def test_sortition_uses_panel_only() -> None:
    pool = [PodName("alice"), PodName("bob"), PodName("carol")]
    ctx = _ctx(["alice", "bob", "carol", "dave"], sortition_pool=pool)
    r = sortition(
        [
            _ballot("alice", BallotChoice.yes),
            _ballot("bob", BallotChoice.yes),
            _ballot("dave", BallotChoice.no),  # not on panel
        ],
        ctx,
    )
    assert r.decided and r.outcome == ProposalOutcome.approved


# --- draw_sortition_panel ---


def test_draw_sortition_panel_is_deterministic() -> None:
    voters = [PodName(n) for n in ("alice", "bob", "carol", "dave", "erin")]
    a = draw_sortition_panel(proposal_id="p-42", voters=voters, size=3)
    b = draw_sortition_panel(proposal_id="p-42", voters=voters, size=3)
    assert a == b
    assert len(a) == 3


def test_draw_sortition_panel_different_for_other_proposal() -> None:
    voters = [PodName(n) for n in ("alice", "bob", "carol", "dave", "erin")]
    a = draw_sortition_panel(proposal_id="p-1", voters=voters, size=3)
    b = draw_sortition_panel(proposal_id="p-2", voters=voters, size=3)
    assert a != b


# --- evaluate dispatcher ---


@pytest.mark.parametrize(
    "strat",
    [
        "majority",
        "supermajority",
        "consensus_omnium",
        "sortition",
    ],
)
def test_evaluate_dispatch_does_not_raise(strat: str) -> None:
    r = evaluate(VotingStrategy(strat), [], _ctx(["alice", "bob"]))
    assert r is not None
