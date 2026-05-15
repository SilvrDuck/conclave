"""SQLAlchemy ORM models for the observer projection.

These mirror the wire models in `conclave_platform.core.models` but are
storage-shaped: JSON columns for unbounded lists, composite keys where it
keeps things simple.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ..core import utc_now


class Base(DeclarativeBase):
    pass


class MemberRow(Base):
    __tablename__ = "members"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    charter_path: Mapped[str] = mapped_column(String, nullable=False)
    admitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exiled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EndpointRow(Base):
    __tablename__ = "endpoints"
    __table_args__ = (UniqueConstraint("pod", "method", "path", name="uq_endpoint"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pod: Mapped[str] = mapped_column(String, nullable=False, index=True)
    method: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    annotation: Mapped[str | None] = mapped_column(String)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class CallEdgeRow(Base):
    __tablename__ = "call_edges"
    caller: Mapped[str] = mapped_column(String, primary_key=True)
    callee: Mapped[str] = mapped_column(String, primary_key=True)
    endpoint_key: Mapped[str] = mapped_column(String, primary_key=True)
    rate_per_min: Mapped[float] = mapped_column(default=0.0)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class ChatroomRow(Base):
    __tablename__ = "chatrooms"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    participants: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    opened_by: Mapped[str] = mapped_column(String, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str | None] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String, nullable=False, default="chatroom")
    messages: Mapped[list[MessageRow]] = relationship(
        "MessageRow", back_populates="chatroom", cascade="all, delete-orphan"
    )


class MessageRow(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    chatroom_id: Mapped[str | None] = mapped_column(
        ForeignKey("chatrooms.id", ondelete="CASCADE"), index=True
    )
    from_pod: Mapped[str] = mapped_column(String, nullable=False)
    to_pod: Mapped[str | None] = mapped_column(String)
    body: Mapped[str] = mapped_column(String, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    chatroom: Mapped[ChatroomRow | None] = relationship("ChatroomRow", back_populates="messages")


class ProposalRow(Base):
    __tablename__ = "proposals"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    proposer: Mapped[str] = mapped_column(String, nullable=False)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    affected: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    outcome: Mapped[str | None] = mapped_column(String)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgendaItemRow(Base):
    __tablename__ = "agenda_items"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    pod: Mapped[str] = mapped_column(String, nullable=False, index=True)
    section: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    eta: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
