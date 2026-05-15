"""Async SQLAlchemy engine + session factory.

Default DSN is `sqlite+aiosqlite:///./observer.db` for quickstart. Production
uses `postgresql+asyncpg://...`. Schema is created at startup via
`Base.metadata.create_all` — alpha has no migrations yet.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def make_engine(dsn: str) -> AsyncEngine:
    return create_async_engine(dsn, future=True, pool_pre_ping=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session, session.begin():
        yield session
