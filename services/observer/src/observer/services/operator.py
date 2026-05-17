"""OperatorService — owns proclamations + Forum command fanout.

Lives in the observer process. Translates Forum POSTs into bus commands
routed to the owning context's process, except `IssueProclamation` and
`ResetState` which the operator handles itself.
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg
from conclave_core import (
    Bus,
    PodsNuked,
    ProclamationIssued,
    StateReset,
    command_subject,
    event_subject,
)

log = logging.getLogger("observer.operator")

OPERATOR_CONTEXT = "operator"

# Tables that ResetState truncates. Listed here (not derived from
# information_schema) so the wipe is an explicit, reviewable contract —
# adding a new domain table without thinking about reset semantics
# should fail loudly when the team notices stale rows post-reset, not
# silently get caught by an introspecting truncate.
RESET_TABLES = (
    "council.councils",
    "council.messages",
    "decisions.decisions",
    "operator.proclamations",
    "senate.proposals",
    "senate.ballots",
    "pods.pods",
    "pods.spawns",
    "observer.pod_state",
    "observer.endpoints",
    "observer.calls",
    "observer.activity",
    "observer.digests",
    "observer.agent_turns",
)


class OperatorService:
    """In-process service running inside Observer."""

    def __init__(self, *, pool: asyncpg.Pool, bus: Bus) -> None:
        self._pool = pool
        self._bus = bus

    async def start(self) -> None:
        # Listen for our own IssueProclamation commands posted by the
        # CommandRouter; we don't expose a direct method on operator
        # because the command/event flow should be uniform.
        await self._bus.subscribe(
            command_subject("IssueProclamation", OPERATOR_CONTEXT),
            self._on_issue_proclamation,
            durable="observer-operator-issue-proclamation",
        )
        await self._bus.subscribe(
            command_subject("ResetState", OPERATOR_CONTEXT),
            self._on_reset_state,
            durable="observer-operator-reset-state",
        )
        # PodsNuked tells us mcp-pods has stopped & removed every pod
        # container; only then is the DB truncate safe (no stragglers
        # writing into freshly-empty tables).
        await self._bus.subscribe(
            event_subject(PodsNuked, "pods"),
            self._on_pods_nuked,
            durable="observer-operator-pods-nuked",
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
            case "RestartPod":
                await self._bus.publish_command("RestartPod", payload, "pods")
            case "ResetState":
                await self._bus.publish_command(
                    "ResetState", payload, OPERATOR_CONTEXT
                )
            case _:
                raise ValueError(f"unknown Forum command kind: {kind}")

    # ── Bus handlers ────────────────────────────────────────────────────

    async def _on_reset_state(self, _data: dict[str, Any]) -> None:
        """Tell mcp-pods to remove every pod container + rendered dir.
        The DB truncate happens in _on_pods_nuked once mcp-pods reports
        completion. Splitting the work avoids racing pod registrations
        against an empty pods.pods table."""
        log.info("ResetState: requesting NukePods from mcp-pods")
        await self._bus.publish_command("NukePods", {}, "pods")

    async def _on_pods_nuked(self, data: dict[str, Any]) -> None:
        """mcp-pods finished tearing down every pod. Truncate every
        domain table in one transaction (CASCADE for safety), then
        emit StateReset so the Forum and any future observers can
        refresh their views."""
        nuked = data.get("nuked_count", "?")
        log.info("PodsNuked nuked_count=%s — truncating domain tables", nuked)
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                table_list = ", ".join(RESET_TABLES)
                # RESTART IDENTITY so the proclamation seq counter goes
                # back to 1 — the next pass really is "epoch I" again.
                await conn.execute(
                    f"TRUNCATE {table_list} RESTART IDENTITY CASCADE"
                )
        await self._bus.publish_event(StateReset(), OPERATOR_CONTEXT)
        log.info("StateReset emitted")

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
