"""Value types shared across contexts.

These are domain primitives (IDs, enums) - not aggregates. Aggregates live
inside their owning service's schema, never in this lib.
"""

from __future__ import annotations

from enum import StrEnum
from typing import NewType

PodId = NewType("PodId", str)
ProposalId = NewType("ProposalId", str)
CouncilId = NewType("CouncilId", str)
DecisionId = NewType("DecisionId", str)
ProclamationSeq = NewType("ProclamationSeq", int)


class ImageStrategy(StrEnum):
    CODE = "code"
    ADOPTED = "adopted"


class ProposalKind(StrEnum):
    ADMISSION = "admission"
    EXILE = "exile"
    IMAGE_SWAP = "image_swap"
    CONTRACT_CHANGE = "contract_change"
    COMPLETION = "completion"


class StrategyName(StrEnum):
    MAJORITY = "majority"
    SUPERMAJORITY = "supermajority"
    CONSENSUS_OMNIUM = "consensus_omnium"
    SORTITION = "sortition"


class VoteChoice(StrEnum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


class ProposalOutcome(StrEnum):
    OPEN = "open"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PodRuntimeStatus(StrEnum):
    NOT_YET_SPAWNED = "not_yet_spawned"
    RUNNING = "running"
    STOPPED = "stopped"


class AgentState(StrEnum):
    IDLE = "idle"
    THINKING = "thinking"
    BLOCKED = "blocked"
    STUCK = "stuck"


AUGUSTUS = "__augustus__"
"""Sender identity for messages and ballots originating from the operator."""
