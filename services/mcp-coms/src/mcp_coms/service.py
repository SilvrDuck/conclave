"""Council + DM service. Append-only messages. DM = 2-party private council.

Spec ref: spec/05-ddd-contexts.md §C3.
"""

from __future__ import annotations

import json
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

    async def convene_contract_change(
        self,
        *,
        pod_id: str,
        participants: list[str],
        endpoint_line: str,
    ) -> str:
        """Find-or-reuse a 'shape of new contract' council for the
        given participant set. Spec/02 Phase 6.

        Idempotent under NATS redelivery and across multiple
        EndpointContractChanged events from the same ingest batch:
        rather than opening N councils with identical participants,
        we reuse the open one and append the new endpoint to its
        topic. Lock keyed on the sorted-participants + pod_id hash
        so concurrent reactor invocations queue rather than fork."""
        sorted_parts = sorted(participants)
        topic_prefix = f"Shape of new contract on {pod_id}"
        lock_key = f"contract-change:{pod_id}:{'|'.join(sorted_parts)}"
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended($1, 0))",
                    lock_key,
                )
                row = await conn.fetchrow(
                    """SELECT council_id, topic FROM council.councils
                         WHERE status = 'open'
                           AND topic LIKE $1
                           AND participants @> $2::text[]
                           AND $2::text[] @> participants
                         LIMIT 1""",
                    f"{topic_prefix}%",
                    sorted_parts,
                )
                if row is not None:
                    # Extend the existing topic if this endpoint isn't
                    # already named. Keeps the council human-readable
                    # without spawning a duplicate.
                    existing_topic = row["topic"]
                    if endpoint_line not in existing_topic:
                        new_topic = f"{existing_topic}; {endpoint_line}"
                        await conn.execute(
                            """UPDATE council.councils SET topic = $2
                                WHERE council_id = $1""",
                            row["council_id"],
                            new_topic,
                        )
                    log.info(
                        "convene_contract_change reusing %s on %s",
                        row["council_id"], pod_id,
                    )
                    return row["council_id"]
        # No existing council — open a fresh one. convene_council
        # publishes CouncilOpened; we keep two SQL transactions here
        # (lookup + insert) to avoid holding the advisory lock through
        # the bus publish, since publish can outlast a single txn.
        return await self.convene_council(
            topic=f"{topic_prefix}: {endpoint_line}",
            participants=sorted_parts,
            private=False,
            needs_augustus=False,
        )

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
        # Spec/02 Phase 7: when Augustus speaks in a DM, the message
        # must land in the *recipient's inbox* (a core-NATS broadcast),
        # not just in the JetStream events stream the Forum consumes.
        # The pod's bootstrap subscribes to conclave.inbox.<pod_id>;
        # without this fan-out, J7 (course-correct) is broken end-to-end.
        if from_pod == AUGUSTUS:
            recipient = next(
                (p for p in participants if p != AUGUSTUS), None
            )
            if recipient is not None:
                inbox_body = json.dumps(
                    {
                        "event_type": "DirectMessageFromUser",
                        "pod_id": recipient,
                        "from": AUGUSTUS,
                        "council_id": council_id,
                        "seq": seq,
                        "body": body,
                    }
                ).encode()
                try:
                    await self._bus.nc.publish(
                        f"conclave.inbox.{recipient}", inbox_body
                    )
                except Exception:
                    log.exception("DM inbox fan-out to %s failed", recipient)
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
