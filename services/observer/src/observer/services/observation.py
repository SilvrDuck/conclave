"""ObservationService — projects events into observer schema read-models.

This is the *only* thing that writes to the observer schema (apart from
OTel ingest). Subscribes to every domain event and updates the matching
read-model. Errors in projection are logged but don't crash the service.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import asyncpg
from conclave_core import Bus

from observer.state import EventBroadcaster

log = logging.getLogger("observer.observation")

# Events we record on the activity feed (the "named events" of J3).
NAMED_EVENTS: set[str] = {
    "ProclamationIssued",
    "ProclamationCompleted",
    "PodContainerStarted",
    "PodAdmitted",
    "PodRenamed",
    "PodExited",
    "PodImageSwapped",
    "PodMarkedStuck",
    "ProposalOpened",
    "ProposalClosed",
    "CouncilOpened",
    "CouncilClosed",
    "DecisionSealed",
    "BallotCast",
}


class ObservationService:
    def __init__(self, *, pool: asyncpg.Pool, broadcaster: EventBroadcaster) -> None:
        self._pool = pool
        self._broadcaster = broadcaster

    async def start(self, bus: Bus) -> None:
        await bus.subscribe(
            "conclave.events.>",
            self._on_event,
            durable="observer-projection",
        )
        log.info("observation projection subscribed")

    async def _on_event(self, data: dict[str, Any]) -> None:
        event_type = data.get("event_type")
        if not event_type:
            log.warning("event without event_type: %s", data)
            return
        try:
            await self._record_activity(data)
            await self._project(event_type, data)
        except Exception:
            log.exception("projection failed for %s", event_type)
            raise
        # broadcast to SSE
        try:
            await self._broadcaster.publish(json.dumps(data))
        except Exception:
            log.exception("broadcaster.publish failed")

    async def _record_activity(self, data: dict[str, Any]) -> None:
        event_type = data["event_type"]
        if event_type not in NAMED_EVENTS:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO observer.activity(event_id, event_type, payload, occurred_at)
                   VALUES($1, $2, $3::jsonb, $4)
                   ON CONFLICT (event_id) DO NOTHING""",
                data["event_id"],
                event_type,
                json.dumps(data),
                _parse_dt(data["occurred_at"]),
            )

    async def _project(self, event_type: str, data: dict[str, Any]) -> None:
        # Dispatch on event_type; idempotent upserts so replay is safe.
        match event_type:
            case "PodContainerStarted":
                await self._upsert_pod(
                    pod_id=data["pod_id"],
                    display_role=data["pod_id"],  # default; rename event will update
                    image_strategy=data["mode"],
                    runtime_status="running",
                    main_image=data.get("image") if data.get("mode") == "adopted" else None,
                )
            case "PodAdmitted":
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """UPDATE observer.pod_state SET admitted = TRUE,
                              display_role = $2, last_seen = now()
                              WHERE pod_id = $1""",
                        data["pod_id"],
                        data["display_role"],
                    )
            case "PodRenamed":
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """UPDATE observer.pod_state SET display_role = $2, last_seen = now()
                              WHERE pod_id = $1""",
                        data["pod_id"],
                        data["new_display_role"],
                    )
            case "PodExited":
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """UPDATE observer.pod_state SET runtime_status = 'stopped',
                              last_seen = now() WHERE pod_id = $1""",
                        data["pod_id"],
                    )
            case "PodImageSwapped":
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """UPDATE observer.pod_state SET image_strategy = $2,
                              main_image = $3, last_seen = now() WHERE pod_id = $1""",
                        data["pod_id"],
                        data["new_mode"],
                        data["new_image"],
                    )
            case "PodHealthChanged":
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """UPDATE observer.pod_state
                              SET runtime_status = $2, agent_state = COALESCE($3, agent_state),
                                  last_seen = now()
                              WHERE pod_id = $1""",
                        data["pod_id"],
                        data["runtime_status"],
                        data.get("agent_state"),
                    )
            case "PodMarkedStuck":
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE observer.pod_state SET agent_state = 'stuck', last_seen = now() "
                        "WHERE pod_id = $1",
                        data["pod_id"],
                    )

    async def _upsert_pod(
        self,
        *,
        pod_id: str,
        display_role: str,
        image_strategy: str,
        runtime_status: str,
        main_image: str | None = None,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO observer.pod_state(pod_id, display_role, image_strategy,
                       runtime_status, main_image)
                   VALUES($1, $2, $3, $4, $5)
                   ON CONFLICT (pod_id) DO UPDATE
                       SET runtime_status = EXCLUDED.runtime_status,
                           main_image = COALESCE(EXCLUDED.main_image, observer.pod_state.main_image),
                           last_seen = now()""",
                pod_id,
                display_role,
                image_strategy,
                runtime_status,
                main_image,
            )


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)
