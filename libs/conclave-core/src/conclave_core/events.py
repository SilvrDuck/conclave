"""Domain events crossing context boundaries (published on the bus).

Every event is a frozen pydantic model. The `event_type` field is used by
consumers to route; pydantic's discriminated unions are not used here so
that adding an event in one service doesn't force a redeploy of every
consumer.

Events are append-only. Never rename a field; deprecate and add a new one.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from conclave_core.models import (
    AgentState,
    PodRuntimeStatus,
    ProposalKind,
    ProposalOutcome,
    StrategyName,
    VoteChoice,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _eid() -> str:
    return uuid4().hex


class DomainEvent(BaseModel):
    """Base for every cross-context event. Pydantic-frozen, JSON-serialisable."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(default_factory=_eid)
    event_type: str
    occurred_at: datetime = Field(default_factory=_now)


# ─── Operator context ──────────────────────────────────────────────────────


class ProclamationIssued(DomainEvent):
    event_type: Literal["ProclamationIssued"] = "ProclamationIssued"
    proclamation_seq: int
    text: str
    issued_at: datetime


class ProclamationCompleted(DomainEvent):
    event_type: Literal["ProclamationCompleted"] = "ProclamationCompleted"
    proclamation_seq: int
    summary: str
    decision_id: str


class DirectMessageFromUser(DomainEvent):
    event_type: Literal["DirectMessageFromUser"] = "DirectMessageFromUser"
    pod_id: str
    body: str


class CharterEdited(DomainEvent):
    event_type: Literal["CharterEdited"] = "CharterEdited"
    pod_id: str
    body: str
    by: str  # "__augustus__" or a pod_id


class StateReset(DomainEvent):
    """All read-models and pod containers have been wiped. Architect
    triggered a fresh start from the Forum (or via the HTTP API).
    Emitted by operator after mcp-pods has confirmed pod teardown."""

    event_type: Literal["StateReset"] = "StateReset"


# ─── Senate context ────────────────────────────────────────────────────────


class ProposalOpened(DomainEvent):
    event_type: Literal["ProposalOpened"] = "ProposalOpened"
    proposal_id: str
    kind: ProposalKind
    proposer: str
    strategy: StrategyName
    summary: str
    payload: dict
    eligible_voters: list[str]
    deadline: datetime


class BallotCast(DomainEvent):
    event_type: Literal["BallotCast"] = "BallotCast"
    proposal_id: str
    voter: str
    choice: VoteChoice
    comment: str | None = None


class ProposalClosed(DomainEvent):
    event_type: Literal["ProposalClosed"] = "ProposalClosed"
    proposal_id: str
    outcome: ProposalOutcome
    summary: str
    affected: list[str] = []


# ─── Council context ───────────────────────────────────────────────────────


class CouncilOpened(DomainEvent):
    event_type: Literal["CouncilOpened"] = "CouncilOpened"
    council_id: str
    topic: str
    participants: list[str]
    private: bool = False
    needs_augustus: bool = False


class MessagePosted(DomainEvent):
    event_type: Literal["MessagePosted"] = "MessagePosted"
    council_id: str
    seq: int
    from_pod: str  # may be AUGUSTUS for DMs
    body: str


class CouncilClosed(DomainEvent):
    event_type: Literal["CouncilClosed"] = "CouncilClosed"
    council_id: str
    summary: str
    decision_id: str | None = None


# ─── Decisions context ─────────────────────────────────────────────────────


class DecisionPlaceholderCreated(DomainEvent):
    event_type: Literal["DecisionPlaceholderCreated"] = "DecisionPlaceholderCreated"
    decision_id: str
    title: str
    proclamation_seq: int | None = None


class DecisionSealed(DomainEvent):
    event_type: Literal["DecisionSealed"] = "DecisionSealed"
    decision_id: str
    title: str
    body: str
    affected: list[str]
    origin: dict  # {"kind": "proposal"|"council"|"proclamation", "id": "..."}


# ─── Pod Lifecycle context ─────────────────────────────────────────────────


class PodContainerStarted(DomainEvent):
    event_type: Literal["PodContainerStarted"] = "PodContainerStarted"
    pod_id: str
    image: str
    mode: str  # "code" or "adopted"


class PodAdmitted(DomainEvent):
    event_type: Literal["PodAdmitted"] = "PodAdmitted"
    pod_id: str
    display_role: str


class PodRenamed(DomainEvent):
    event_type: Literal["PodRenamed"] = "PodRenamed"
    pod_id: str
    new_display_role: str
    old_display_role: str | None


class PodExited(DomainEvent):
    event_type: Literal["PodExited"] = "PodExited"
    pod_id: str
    reason: str  # "exiled" | "crashed" | "stopped"


class PodImageSwapped(DomainEvent):
    event_type: Literal["PodImageSwapped"] = "PodImageSwapped"
    pod_id: str
    old_image: str
    new_image: str
    new_mode: str


class PodsNuked(DomainEvent):
    """mcp-pods finished stopping and removing every pod container and
    every rendered pods/<id>/ dir in response to a NukePods command.
    Signals operator that it's safe to truncate the DB."""

    event_type: Literal["PodsNuked"] = "PodsNuked"
    nuked_count: int


# ─── Observation context ───────────────────────────────────────────────────


class EndpointObserved(DomainEvent):
    event_type: Literal["EndpointObserved"] = "EndpointObserved"
    pod_id: str
    method: str
    path: str


class EndpointAnnotated(DomainEvent):
    event_type: Literal["EndpointAnnotated"] = "EndpointAnnotated"
    pod_id: str
    method: str
    path: str
    body: str


class EndpointContractChanged(DomainEvent):
    """Spec/02 Phase 6 — IdentifyCallers policy fires when a pod's API
    surface expands while it already has callers. The platform tells
    the callers so they can convene a council *before* the contract
    is balloted. This is the IdentifyCallers result, materialised."""

    event_type: Literal["EndpointContractChanged"] = "EndpointContractChanged"
    pod_id: str
    method: str
    path: str
    callers: list[str]


class PodMarkedStuck(DomainEvent):
    event_type: Literal["PodMarkedStuck"] = "PodMarkedStuck"
    pod_id: str
    reason: str


class PodHealthChanged(DomainEvent):
    event_type: Literal["PodHealthChanged"] = "PodHealthChanged"
    pod_id: str
    runtime_status: PodRuntimeStatus
    agent_state: AgentState | None = None


# ─── Agent Execution context (observed) ────────────────────────────────────


class AgentBooted(DomainEvent):
    """Emitted once when a pod's agent runtime is alive and connected to
    the bus. Distinct from PodContainerStarted (the container exists)
    and AgentSessionStarted (Claude session id is captured). Spec/02
    Phase 2."""

    event_type: Literal["AgentBooted"] = "AgentBooted"
    pod_id: str
    agent_kind: str = "claude-code"


class PodCharterLoaded(DomainEvent):
    """Emitted by the pod when it has read its charter file at boot.
    The hash identifies the charter content so the Forum can show
    'charter v3' style versioning. Spec/02 Phase 2."""

    event_type: Literal["PodCharterLoaded"] = "PodCharterLoaded"
    pod_id: str
    charter_path: str
    version_hash: str


class AgentSessionStarted(DomainEvent):
    event_type: Literal["AgentSessionStarted"] = "AgentSessionStarted"
    pod_id: str
    session_id: str


class AgentTurnStarted(DomainEvent):
    event_type: Literal["AgentTurnStarted"] = "AgentTurnStarted"
    pod_id: str
    turn_id: str


class AgentTurnEnded(DomainEvent):
    event_type: Literal["AgentTurnEnded"] = "AgentTurnEnded"
    pod_id: str
    turn_id: str
    tokens_in: int
    tokens_out: int


class AgentTextDelta(DomainEvent):
    """Per-frame delta of the agent's text output, streamed at ~1Hz
    during a turn so the Forum can render live transcript in J4's
    Pod folio. Kanban #90."""

    event_type: Literal["AgentTextDelta"] = "AgentTextDelta"
    pod_id: str
    turn_id: str
    seq: int
    body: str
