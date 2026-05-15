"""SqliteDocs — DocsAdapter backed by a single SQLite file.

The senate-ledger and mcp-decisions processes both write/read through the
same `docs.db` (bind-mounted at /data/docs.db in docker compose). At alpha
this is the simplest way to make ADRs visible across services without
requiring GitHub Issues credentials.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String, event, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ...core import Adr, AdrId, PodName, ProposalId, utc_now


class _Base(DeclarativeBase):
    pass


class _AdrRow(_Base):
    __tablename__ = "adrs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    affected_pods: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    proposal_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _apply_sqlite_pragmas(dbapi_conn, _conn_record):  # type: ignore[no-untyped-def]
    """busy_timeout lets concurrent writers (senate-ledger + mcp-decisions)
    block politely instead of fast-failing. We skip WAL to avoid the
    exclusive-lock race the two processes hit on first start."""
    cur = dbapi_conn.cursor()
    try:
        cur.execute("PRAGMA busy_timeout=30000")
        cur.execute("PRAGMA synchronous=NORMAL")
    finally:
        cur.close()


class SqliteDocs:
    def __init__(self, *, dsn: str) -> None:
        self._engine: AsyncEngine = create_async_engine(dsn, future=True)
        event.listen(self._engine.sync_engine, "connect", _apply_sqlite_pragmas)
        self._sessions = async_sessionmaker(self._engine, expire_on_commit=False)
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_schema(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            for attempt in range(5):
                try:
                    async with self._engine.begin() as conn:
                        await conn.run_sync(_Base.metadata.create_all)
                    break
                except Exception:
                    if attempt == 4:
                        raise
                    await asyncio.sleep(0.5 * (attempt + 1))
            self._initialized = True

    async def close(self) -> None:
        await self._engine.dispose()

    async def write_adr(
        self,
        *,
        title: str,
        body: str,
        affected_pods: list[PodName],
        proposal_id: str | None = None,
    ) -> AdrId:
        await self._ensure_schema()
        async with self._sessions() as s, s.begin():
            # ID = "adr-NNNN" with N = current count + 1. Cheap, monotonic
            # under SQLite's single-writer.
            n = (
                await s.execute(select(_AdrRow))
            ).scalars().all()
            new_id = AdrId(f"adr-{len(n) + 1:04d}")
            s.add(
                _AdrRow(
                    id=new_id,
                    title=title,
                    body=body,
                    affected_pods=list(affected_pods),
                    proposal_id=proposal_id,
                    created_at=utc_now(),
                )
            )
        return new_id

    async def read(self, adr_id: AdrId) -> Adr | None:
        await self._ensure_schema()
        async with self._sessions() as s:
            row = await s.get(_AdrRow, adr_id)
            return None if row is None else _to_adr(row)

    async def search(self, query: str, *, limit: int = 10) -> list[Adr]:
        await self._ensure_schema()
        needle = query.lower()
        async with self._sessions() as s:
            rows = (await s.execute(select(_AdrRow))).scalars().all()
        hits = [
            r
            for r in rows
            if needle in r.title.lower() or needle in r.body.lower()
        ]
        return [_to_adr(r) for r in hits[:limit]]

    async def list(
        self,
        *,
        pod: PodName | None = None,
        limit: int = 100,
    ) -> list[Adr]:
        await self._ensure_schema()
        async with self._sessions() as s:
            rows = (await s.execute(select(_AdrRow))).scalars().all()
        items = list(rows)
        if pod is not None:
            items = [r for r in items if pod in r.affected_pods]
        items.sort(key=lambda r: r.created_at, reverse=True)
        return [_to_adr(r) for r in items[:limit]]


def _to_adr(row: _AdrRow) -> Adr:
    return Adr(
        id=AdrId(row.id),
        title=row.title,
        body=row.body,
        affected_pods=[PodName(p) for p in row.affected_pods],
        proposal_id=ProposalId(row.proposal_id) if row.proposal_id else None,
        created_at=_utc(row.created_at),
    )


__all__ = ["SqliteDocs"]
