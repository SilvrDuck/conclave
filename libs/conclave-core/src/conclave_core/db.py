"""asyncpg connection pool helper. One pool per process, per-schema search_path.

Each context owns one schema and *only* writes there. Cross-schema reads are
allowed but should go through the owning context's read API when possible.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg


def database_url() -> str:
    """Return the configured DATABASE_URL. Falls back to the
    localhost dev DSN only when CONCLAVE_DEV_DEFAULT_DB is set.
    Production-shaped services should crash on a missing URL rather
    than silently connecting to a wrong instance."""
    explicit = os.environ.get("DATABASE_URL")
    if explicit:
        return explicit
    if os.environ.get("CONCLAVE_DEV_DEFAULT_DB"):
        return "postgres://conclave:conclave@localhost:5432/conclave"
    raise RuntimeError(
        "DATABASE_URL not set. Export it explicitly, or set "
        "CONCLAVE_DEV_DEFAULT_DB=1 to use the local dev DSN."
    )


@asynccontextmanager
async def pool(
    *, schema: str | None = None, min_size: int = 1, max_size: int = 10
) -> AsyncIterator[asyncpg.Pool]:
    """Create a pool. If `schema` is provided, sets `search_path` on every
    connection so unqualified table refs resolve to that context's schema."""

    async def init(conn: asyncpg.Connection) -> None:
        await conn.set_type_codec(
            "jsonb",
            encoder=_encode_jsonb,
            decoder=_decode_jsonb,
            schema="pg_catalog",
        )
        if schema:
            await conn.execute(f'SET search_path TO "{schema}", public')

    p = await asyncpg.create_pool(
        dsn=database_url(),
        min_size=min_size,
        max_size=max_size,
        init=init,
    )
    if p is None:
        raise RuntimeError("asyncpg.create_pool returned None")
    try:
        yield p
    finally:
        await p.close()


def _encode_jsonb(value: object) -> str:
    return json.dumps(value)


def _decode_jsonb(value: str) -> object:
    return json.loads(value)
