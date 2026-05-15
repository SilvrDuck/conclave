"""Domain model construction."""

from __future__ import annotations

from datetime import UTC, datetime

from conclave_platform.core import (
    Endpoint,
    Member,
    MemberStatus,
    PodName,
    Proposal,
    ProposalKind,
    VotingStrategy,
    endpoint_key,
    utc_now,
)
from conclave_platform.core.ids import ProposalId


def test_member_minimal() -> None:
    m = Member(
        name=PodName("alice"),
        status=MemberStatus.admitted,
        charter_path="pods/alice/charter.md",
    )
    assert m.exiled_at is None


def test_endpoint_key_property() -> None:
    e = Endpoint(
        pod=PodName("alice"),
        method="get",
        path="/users/{id}",
        first_seen=utc_now(),
        last_seen=utc_now(),
    )
    assert e.key == endpoint_key("get", "/users/{id}")


def test_proposal_serializes() -> None:
    p = Proposal(
        id=ProposalId("p-1"),
        kind=ProposalKind.member,
        proposer=PodName("alice"),
        strategy=VotingStrategy.majority,
        payload={"charter_path": "pods/bob/charter.md"},
        affected=[PodName("alice")],
        opened_at=utc_now(),
        deadline=datetime(2099, 1, 1, tzinfo=UTC),
    )
    s = p.model_dump_json()
    assert "p-1" in s
