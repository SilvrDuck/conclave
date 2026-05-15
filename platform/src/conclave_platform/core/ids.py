"""Strongly-typed identifiers used across the platform.

These are deliberately plain `str` newtypes — Pydantic serializes them transparently,
SQLAlchemy stores them as TEXT, and they keep mypy honest about not mixing,
e.g., a `PodName` with a `ProposalId`.
"""

from __future__ import annotations

from typing import NewType

PodName = NewType("PodName", str)
ProposalId = NewType("ProposalId", str)
ChatroomId = NewType("ChatroomId", str)
CouncilId = NewType("CouncilId", str)
MessageId = NewType("MessageId", str)
AdrId = NewType("AdrId", str)
AgendaItemId = NewType("AgendaItemId", str)
EndpointKey = NewType("EndpointKey", str)
SubscriptionId = NewType("SubscriptionId", str)


def endpoint_key(method: str, path: str) -> EndpointKey:
    """Canonical key for an HTTP endpoint: 'METHOD PATH' uppercased verb."""
    return EndpointKey(f"{method.upper()} {path}")
