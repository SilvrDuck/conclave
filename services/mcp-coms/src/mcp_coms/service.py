"""Council + DM service. Append-only messages. DM = 2-party private council.

Spec ref: spec/05-ddd-contexts.md §C3.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

import asyncpg
from conclave_core import Bus
from conclave_core.events import CouncilClosed, CouncilOpened, MessagePosted
from conclave_core.models import AUGUSTUS

log = logging.getLogger("mcp-coms.service")

COUNCIL_CONTEXT = "council"


class ComsService:
    def __init__(self, *, pool: asyncpg.Pool, bus: Bus) -> None:
        self._pool = pool
        self._bus = bus

    async def convene_council(
        self,
        *,
        topic: str,
        participants: list[str],
        private: bool = False,
        needs_augustus: bool = False,
    ) -> str:
        if not topic.strip():
            raise ValueError("council topic must be non-empty")
        if len(participants) < 1:
            raise ValueError("council must have at least one participant")
        council_id = f"council-{secrets.token_hex(6)}"
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO council.councils(council_id, topic, participants,
                       private, needs_augustus)
                   VALUES($1, $2, $3, $4, $5)""",
                council_id,
                topic,
                participants,
                private,
                needs_augustus,
            )
        await self._bus.publish_event(
            CouncilOpened(
                council_id=council_id,
                topic=topic,
                participants=participants,
                private=private,
                needs_augustus=needs_augustus,
            ),
            COUNCIL_CONTEXT,
        )
        log.info("CouncilOpened %s topic=%r participants=%d", council_id, topic, len(participants))
        return council_id

    async def post_message(self, *, council_id: str, from_pod: str, body: str) -> int:
        if not body.strip():
            raise ValueError("message body must be non-empty")
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """SELECT participants, status, private
                         FROM council.councils
                         WHERE council_id = $1 FOR UPDATE""",
                    council_id,
                )
                if row is None:
                    raise ValueError(f"unknown council_id: {council_id}")
                if row["status"] != "open":
                    raise ValueError(f"council {council_id} is closed")

                participants = list(row["participants"])
                if from_pod == AUGUSTUS:
                    # Spec §C3: Augustus posts only in private 2-party councils
                    # he's a participant of (DMs). Public councils are read-only
                    # for him.
                    if not (
                        row["private"]
                        and len(participants) == 2
                        and AUGUSTUS in participants
                    ):
                        raise ValueError(
                            f"Augustus may only post in DMs; {council_id} is not one"
                        )
                elif from_pod not in participants:
                    raise ValueError(
                        f"{from_pod} is not a participant in {council_id}"
                    )
                seq_row = await conn.fetchrow(
                    """SELECT COALESCE(MAX(seq), 0) + 1 AS next FROM council.messages
                         WHERE council_id = $1""",
                    council_id,
                )
                seq = int(seq_row["next"]) if seq_row else 1
                await conn.execute(
                    """INSERT INTO council.messages(council_id, seq, from_pod, body)
                       VALUES($1, $2, $3, $4)""",
                    council_id,
                    seq,
                    from_pod,
                    body,
                )
        await self._bus.publish_event(
            MessagePosted(council_id=council_id, seq=seq, from_pod=from_pod, body=body),
            COUNCIL_CONTEXT,
        )
        return seq

    async def close_council(
        self, *, council_id: str, summary: str, decision_id: str | None = None
    ) -> None:
        if not summary.strip():
            raise ValueError("close summary must be non-empty")
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """UPDATE council.councils
                      SET status = 'closed', closed_at = now(), summary = $2,
                          decision_id = $3
                    WHERE council_id = $1 AND status = 'open'
                    RETURNING council_id""",
                council_id,
                summary,
                decision_id,
            )
            if row is None:
                raise ValueError(f"council {council_id} not found or already closed")
        await self._bus.publish_event(
            CouncilClosed(council_id=council_id, summary=summary, decision_id=decision_id),
            COUNCIL_CONTEXT,
        )
        log.info("CouncilClosed %s", council_id)

    async def dm(self, *, from_pod: str, to_pod: str, body: str) -> dict[str, Any]:
        """Open-or-reuse a 2-party private council and post one message.

        DMs are the degenerate case of councils. The find-or-create lookup
        runs under an advisory lock keyed on the sorted pair, so two
        concurrent DMs between the same parties don't fork the thread.
        """
        if from_pod == to_pod:
            raise ValueError("cannot DM yourself")
        a, b = sorted([from_pod, to_pod])
        pair_key = f"{a}|{b}"
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Advisory lock on the sorted-pair hash serialises concurrent
                # dm() calls for the same parties so we don't create duplicate
                # threads. Lock is auto-released at txn end.
                await conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended($1, 0))",
                    pair_key,
                )
                row = await conn.fetchrow(
                    """SELECT council_id FROM council.councils
                         WHERE private = TRUE AND status = 'open'
                           AND participants @> ARRAY[$1, $2]::text[]
                           AND array_length(participants, 1) = 2
                         LIMIT 1""",
                    a,
                    b,
                )
                if row is None:
                    council_id = await self._insert_council(
                        conn=conn,
                        topic=f"DM: {a} ↔ {b}",
                        participants=[a, b],
                        private=True,
                        # Spec §C5: a fresh DM where Augustus is a party should
                        # surface on the operator inbox (regardless of direction).
                        needs_augustus=AUGUSTUS in {a, b},
                    )
                else:
                    council_id = row["council_id"]
        seq = await self.post_message(
            council_id=council_id, from_pod=from_pod, body=body
        )
        return {"council_id": council_id, "seq": seq}

    async def _insert_council(
        self,
        *,
        conn: asyncpg.Connection,
        topic: str,
        participants: list[str],
        private: bool,
        needs_augustus: bool,
    ) -> str:
        """Insert a council row + publish CouncilOpened. Used inside an
        existing txn so the surrounding logic can hold its lock."""
        council_id = f"council-{secrets.token_hex(6)}"
        await conn.execute(
            """INSERT INTO council.councils(council_id, topic, participants,
                   private, needs_augustus)
               VALUES($1, $2, $3, $4, $5)""",
            council_id,
            topic,
            participants,
            private,
            needs_augustus,
        )
        await self._bus.publish_event(
            CouncilOpened(
                council_id=council_id,
                topic=topic,
                participants=participants,
                private=private,
                needs_augustus=needs_augustus,
            ),
            COUNCIL_CONTEXT,
        )
        log.info("CouncilOpened %s topic=%r participants=%d", council_id, topic, len(participants))
        return council_id
