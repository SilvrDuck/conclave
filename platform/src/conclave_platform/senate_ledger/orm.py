"""SQLAlchemy models for the senate ledger (proposals, ballots, members)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ..core import utc_now


class Base(DeclarativeBase):
    pass


class MemberRow(Base):
    __tablename__ = "members"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="admitted")
    admitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exiled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProposalRow(Base):
    __tablename__ = "proposals"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    proposer: Mapped[str] = mapped_column(String, nullable=False)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    affected: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    sortition_pool: Mapped[list[str] | None] = mapped_column(JSON)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    outcome: Mapped[str | None] = mapped_column(String)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    adr_id: Mapped[str | None] = mapped_column(String)
    ballots: Mapped[list[BallotRow]] = relationship(
        "BallotRow", back_populates="proposal", cascade="all, delete-orphan"
    )


class BallotRow(Base):
    __tablename__ = "ballots"
    proposal_id: Mapped[str] = mapped_column(
        ForeignKey("proposals.id", ondelete="CASCADE"), primary_key=True
    )
    voter: Mapped[str] = mapped_column(String, primary_key=True)
    choice: Mapped[str] = mapped_column(String, nullable=False)
    comment: Mapped[str | None] = mapped_column(String)
    cast_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    proposal: Mapped[ProposalRow] = relationship("ProposalRow", back_populates="ballots")
