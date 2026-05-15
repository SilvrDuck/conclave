"""Event discriminated-union round-trip."""

from __future__ import annotations

import pytest

from conclave_platform.core import (
    AnnotationRequested,
    EventEnvelope,
    GoalUpdated,
    MessageReceived,
    PodName,
    VoteOpen,
    endpoint_key,
    pod_inbox_topic,
)
from conclave_platform.core.ids import (
    ChatroomId,
    MessageId,
    ProposalId,
)


def _round_trip(env: EventEnvelope) -> EventEnvelope:
    return EventEnvelope.model_validate_json(env.model_dump_json())


def test_message_received_round_trip() -> None:
    env = EventEnvelope(
        event=MessageReceived(
            target_pod=PodName("alice"),
            chatroom_id=ChatroomId("c-1"),
            message_id=MessageId("m-1"),
            from_pod=PodName("bob"),
            body="hi alice",
        )
    )
    again = _round_trip(env)
    assert isinstance(again.event, MessageReceived)
    assert again.event.body == "hi alice"


def test_vote_open_round_trip() -> None:
    env = EventEnvelope(
        event=VoteOpen(
            target_pod=PodName("alice"),
            proposal_id=ProposalId("p-1"),
            kind="member",
            proposer=PodName("bob"),
            rationale="we need an auth pod",
        )
    )
    again = _round_trip(env)
    assert isinstance(again.event, VoteOpen)


def test_annotation_requested_round_trip() -> None:
    env = EventEnvelope(
        event=AnnotationRequested(
            target_pod=PodName("alice"),
            endpoint=endpoint_key("get", "/users/{id}"),
            pod=PodName("alice"),
        )
    )
    again = _round_trip(env)
    assert isinstance(again.event, AnnotationRequested)
    assert again.event.endpoint == "GET /users/{id}"


def test_goal_updated_broadcast_has_no_target() -> None:
    env = EventEnvelope(event=GoalUpdated(goal="build TODO API"))
    again = _round_trip(env)
    assert again.event.target_pod is None


def test_pod_inbox_topic() -> None:
    assert pod_inbox_topic(PodName("alice")) == "pod/alice/inbox"


def test_endpoint_key_normalizes_verb() -> None:
    assert endpoint_key("get", "/users") == "GET /users"
    assert endpoint_key("POST", "/users") == "POST /users"


@pytest.mark.parametrize(
    "raw",
    [
        '{"event":{"type":"goal_updated","goal":"x"}}',
        '{"event":{"type":"member_admitted","pod":"alice"}}',
    ],
)
def test_loads_from_raw_json(raw: str) -> None:
    env = EventEnvelope.model_validate_json(raw)
    assert env.event.ts is not None
