"""OperatorService — owns proclamations + Forum command fanout.

Lives in the observer process. Translates Forum POSTs into bus commands
routed to the owning context's process, except `IssueProclamation` which
the operator handles itself (writes to `operator.proclamations` and
emits `ProclamationIssued`).
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg
from conclave_core import Bus, ProclamationIssued, command_subject

log = logging.getLogger("observer.operator")

OPERATOR_CONTEXT = "operator"


class OperatorService:
    """In-process service running inside Observer."""

    def __init__(self, *, pool: asyncpg.Pool, bus: Bus) -> None:
        self._pool = pool
        self._bus = bus

    async def start(self) -> None:
        # Listen for our own IssueProclamation commands posted by the
        # CommandRouter; we don't expose a direct method on operator
        # because the command/event flow should be uniform.
        subject = command_subject("IssueProclamation", OPERATOR_CONTEXT)
        await self._bus.subscribe(
            subject,
            self._on_issue_proclamation,
            durable="observer-operator-issue-proclamation",
        )

    # ── Forum command translation (called by CommandRouter) ─────────────

    async def fan_out_forum_command(self, kind: str, payload: dict[str, Any]) -> None:
        """Translate one of the 4 Forum writes into a bus command."""

        match kind:
            case "IssueProclamation":
                await self._bus.publish_command(
                    "IssueProclamation", payload, OPERATOR_CONTEXT
                )
            case "SendDirectMessage":
                await self._bus.publish_command(
                    "SendDirectMessage", payload, "council"
                )
            case "EditCharter":
                await self._bus.publish_command("EditCharter", payload, "pods")
            case "CastBallot":
                await self._bus.publish_command("CastBallot", payload, "senate")
            case _:
                raise ValueError(f"unknown Forum command kind: {kind}")

    # ── Bus handlers ────────────────────────────────────────────────────

    async def _on_issue_proclamation(self, data: dict[str, Any]) -> None:
        text = data.get("text", "").strip()
        if not text:
            log.warning("IssueProclamation with empty text; dropping")
            return
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO operator.proclamations(text) VALUES($1) "
                "RETURNING seq, text, issued_at",
                text,
            )
        assert row is not None
        event = ProclamationIssued(
            proclamation_seq=row["seq"],
            text=row["text"],
            issued_at=row["issued_at"],
        )
        await self._bus.publish_event(event, OPERATOR_CONTEXT)
        log.info("ProclamationIssued seq=%s", row["seq"])
