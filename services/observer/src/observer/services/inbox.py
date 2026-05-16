"""InboxReadModel — Augustus's inbox.

Per spec/05-ddd-contexts §C5: the inbox is a *view*, not a queue. It joins
on every read:
  - open ballots from senate where Augustus is eligible
  - pod_state rows with agent_state = 'stuck'
  - council rows tagged needs_augustus = true

Augustus "clearing" an entry maps to the underlying action; there is no
InboxEntryAcknowledged event.
"""

from __future__ import annotations

from typing import Any

import asyncpg
from conclave_core.models import AUGUSTUS


class InboxReadModel:
    def __init__(self, *, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def read(self) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            ballots = await conn.fetch(
                """SELECT proposal_id, kind, summary, strategy, deadline
                     FROM senate.proposals
                     WHERE outcome = 'open' AND $1 = ANY(eligible_voters)""",
                AUGUSTUS,
            )
            stuck = await conn.fetch(
                "SELECT pod_id, display_role FROM observer.pod_state WHERE agent_state = 'stuck'"
            )
            councils = await conn.fetch(
                """SELECT council_id, topic, participants
                     FROM council.councils
                     WHERE status = 'open' AND needs_augustus = TRUE"""
            )

        items: list[dict[str, Any]] = []
        for r in ballots:
            items.append(
                {
                    "kind": "ballot",
                    "proposal_id": r["proposal_id"],
                    "proposal_kind": r["kind"],
                    "summary": r["summary"],
                    "strategy": r["strategy"],
                    "deadline": r["deadline"].isoformat(),
                }
            )
        for r in stuck:
            items.append(
                {
                    "kind": "stuck",
                    "pod_id": r["pod_id"],
                    "display_role": r["display_role"],
                }
            )
        for r in councils:
            items.append(
                {
                    "kind": "council",
                    "council_id": r["council_id"],
                    "topic": r["topic"],
                    "participants": list(r["participants"]),
                }
            )
        return items
