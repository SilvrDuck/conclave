"""Decisions service. Sealed records + placeholder lifecycle.

Spec ref: spec/05-ddd-contexts.md §C4.

Body invariants:
- placeholder bodies allowed to be null
- sealed bodies must be non-empty and not a template marker
"""

from __future__ import annotations

import logging
import re
import secrets
from typing import Any

import asyncpg
from conclave_core import Bus
from conclave_core.events import DecisionPlaceholderCreated, DecisionSealed

log = logging.getLogger("mcp-decisions.service")

DECISIONS_CONTEXT = "decisions"

# Bodies that look like a template placeholder are rejected at seal time
# (spec/03-prototype-audit.md L113 — v1 had empty tablets nobody sealed).
TEMPLATE_BODIES = {
    "_council pending_",
    "_pending_",
    "tbd",
    "todo",
    "n/a",
}


def _looks_like_template(body: str) -> bool:
    stripped = body.strip().lower()
    if not stripped:
        return True
    if stripped in TEMPLATE_BODIES:
        return True
    if re.fullmatch(r"_+\s*\w+(\s+\w+){0,3}\s*_+", stripped):
        return True
    return False


def _truncate(text: str, limit: int = 60) -> str:
    text = text.strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


class DecisionsService:
    def __init__(self, *, pool: asyncpg.Pool, bus: Bus) -> None:
        self._pool = pool
        self._bus = bus

    # ─── placeholder ────────────────────────────────────────────────────

    async def create_placeholder(
        self,
        *,
        title: str,
        origin_kind: str,
        origin_id: str,
        affected: list[str] | None = None,
    ) -> str:
        if not title.strip():
            raise ValueError("placeholder title must be non-empty")
        decision_id = f"adr-{secrets.token_hex(6)}"
        affected = affected or []
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO decisions.decisions(decision_id, title, body, affected,
                       origin_kind, origin_id, status)
                   VALUES($1, $2, NULL, $3, $4, $5, 'placeholder')
                   ON CONFLICT (decision_id) DO NOTHING
                   RETURNING decision_id""",
                decision_id,
                title,
                affected,
                origin_kind,
                origin_id,
            )
        # If we collided (vanishingly unlikely) just retry with a fresh id.
        if row is None:
            return await self.create_placeholder(
                title=title, origin_kind=origin_kind, origin_id=origin_id, affected=affected
            )
        await self._bus.publish_event(
            DecisionPlaceholderCreated(
                decision_id=decision_id,
                title=title,
                proclamation_seq=None,
            ),
            DECISIONS_CONTEXT,
        )
        log.info("placeholder %s for %s/%s", decision_id, origin_kind, origin_id)
        return decision_id

    # ─── seal ───────────────────────────────────────────────────────────

    async def seal(
        self,
        *,
        decision_id: str,
        body: str,
        affected: list[str] | None = None,
    ) -> None:
        if _looks_like_template(body):
            raise ValueError("sealed decision body must be substantive, not a template")
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """SELECT title, status, affected, origin_kind, origin_id
                         FROM decisions.decisions WHERE decision_id = $1 FOR UPDATE""",
                    decision_id,
                )
                if row is None:
                    raise ValueError(f"unknown decision_id: {decision_id}")
                if row["status"] == "sealed":
                    raise ValueError(f"decision {decision_id} is already sealed")
                final_affected = list(affected) if affected is not None else list(row["affected"])
                await conn.execute(
                    """UPDATE decisions.decisions
                          SET body = $2, affected = $3,
                              status = 'sealed', sealed_at = now()
                        WHERE decision_id = $1""",
                    decision_id,
                    body,
                    final_affected,
                )
                title = row["title"]
                origin = {"kind": row["origin_kind"], "id": row["origin_id"]}
        await self._bus.publish_event(
            DecisionSealed(
                decision_id=decision_id,
                title=title,
                body=body,
                affected=final_affected,
                origin=origin,
            ),
            DECISIONS_CONTEXT,
        )
        log.info("DecisionSealed %s", decision_id)

    async def seal_new(
        self,
        *,
        title: str,
        body: str,
        origin_kind: str,
        origin_id: str,
        affected: list[str] | None = None,
    ) -> str:
        """Create + seal a decision in one step (no placeholder phase)."""
        decision_id = await self.create_placeholder(
            title=title, origin_kind=origin_kind, origin_id=origin_id, affected=affected
        )
        await self.seal(decision_id=decision_id, body=body, affected=affected)
        return decision_id

    # ─── reads ──────────────────────────────────────────────────────────

    async def read(self, decision_id: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            r = await conn.fetchrow(
                """SELECT decision_id, title, body, affected, origin_kind, origin_id,
                          status, created_at, sealed_at
                     FROM decisions.decisions WHERE decision_id = $1""",
                decision_id,
            )
        if r is None:
            return None
        return _to_dict(r)

    async def list(
        self,
        *,
        status: str | None = None,
        origin_kind: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        clauses, params = [], []
        if status:
            params.append(status)
            clauses.append(f"status = ${len(params)}")
        if origin_kind:
            params.append(origin_kind)
            clauses.append(f"origin_kind = ${len(params)}")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        sql = f"""SELECT decision_id, title, body, affected, origin_kind, origin_id,
                         status, created_at, sealed_at
                    FROM decisions.decisions {where}
                    ORDER BY created_at DESC
                    LIMIT ${len(params)}"""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        return [_to_dict(r) for r in rows]

    async def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        pattern = f"%{query}%"
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT decision_id, title, body, affected, origin_kind, origin_id,
                          status, created_at, sealed_at
                     FROM decisions.decisions
                    WHERE title ILIKE $1 OR body ILIKE $1
                    ORDER BY created_at DESC
                    LIMIT $2""",
                pattern,
                limit,
            )
        return [_to_dict(r) for r in rows]

    # ─── reactors ───────────────────────────────────────────────────────

    async def on_proclamation_issued(self, data: dict[str, Any]) -> None:
        """Create the placeholder per spec §2 / §C4 invariants."""
        seq = data["proclamation_seq"]
        text = data["text"]
        title = f"Architecture for: {_truncate(text)}"
        async with self._pool.acquire() as conn:
            existing = await conn.fetchrow(
                """SELECT decision_id FROM decisions.decisions
                     WHERE origin_kind = 'proclamation' AND origin_id = $1""",
                str(seq),
            )
        if existing is not None:
            return
        await self.create_placeholder(
            title=title,
            origin_kind="proclamation",
            origin_id=str(seq),
        )

    async def on_proposal_closed(self, data: dict[str, Any]) -> None:
        """Seal an ADR for approved proposals."""
        if data["outcome"] != "approved":
            return
        body = data.get("summary") or "proposal approved"
        title = f"Proposal {data['proposal_id']}: {_truncate(body)}"
        try:
            await self.seal_new(
                title=title,
                body=body,
                origin_kind="proposal",
                origin_id=data["proposal_id"],
                affected=data.get("affected") or [],
            )
        except ValueError:
            log.exception("seal proposal failed (already sealed?)")

    async def on_council_closed(self, data: dict[str, Any]) -> None:
        """Seal an ADR (or attach to existing) when a council closes."""
        decision_id = data.get("decision_id")
        summary = data["summary"]
        if decision_id:
            try:
                await self.seal(decision_id=decision_id, body=summary)
            except ValueError:
                log.exception("seal failed for %s", decision_id)
            return
        # No pre-allocated decision: create-and-seal a fresh one.
        title = f"Council {data['council_id']}: {_truncate(summary)}"
        try:
            await self.seal_new(
                title=title,
                body=summary,
                origin_kind="council",
                origin_id=data["council_id"],
            )
        except ValueError:
            log.exception("seal council failed")


def _to_dict(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "decision_id": row["decision_id"],
        "title": row["title"],
        "body": row["body"],
        "affected": list(row["affected"]),
        "origin": {"kind": row["origin_kind"], "id": row["origin_id"]},
        "status": row["status"],
        "created_at": row["created_at"].isoformat(),
        "sealed_at": row["sealed_at"].isoformat() if row["sealed_at"] else None,
    }
