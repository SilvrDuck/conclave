"""Pod-lifecycle service. Owns the pods schema; writes traefik rules.

Spec ref: spec/05-ddd-contexts.md §C6.
"""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg
from conclave_core import Bus
from conclave_core.events import (
    PodAdmitted,
    PodContainerStarted,
    PodImageSwapped,
    PodRenamed,
)
from conclave_core.models import ImageStrategy

from mcp_pods.traefik import remove_rule, write_rule

log = logging.getLogger("mcp-pods.service")

PODS_CONTEXT = "pods"
DEFAULT_SERVICE_PORT = 8000


def traefik_dynamic_dir() -> Path:
    return Path(os.environ.get("TRAEFIK_DYNAMIC_DIR", "/traefik-dynamic"))


class PodsService:
    def __init__(self, *, pool: asyncpg.Pool, bus: Bus) -> None:
        self._pool = pool
        self._bus = bus

    async def register_self(
        self,
        *,
        pod_id: str | None,
        display_role: str,
        image_strategy: str,
        main_image: str | None = None,
        charter_path: str | None = None,
    ) -> dict[str, Any]:
        strategy = ImageStrategy(image_strategy)
        pod_id = pod_id or f"pod-{secrets.token_hex(6)}"
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO pods.pods(pod_id, display_role, image_strategy,
                       main_image, charter_path)
                   VALUES($1, $2, $3, $4, $5)
                   ON CONFLICT (pod_id) DO UPDATE
                       SET display_role = EXCLUDED.display_role,
                           image_strategy = EXCLUDED.image_strategy,
                           main_image = COALESCE(EXCLUDED.main_image, pods.pods.main_image)""",
                pod_id,
                display_role,
                strategy.value,
                main_image,
                charter_path,
            )
        await self._bus.publish_event(
            PodContainerStarted(
                pod_id=pod_id,
                image=main_image or "code",
                mode=strategy.value,
            ),
            PODS_CONTEXT,
        )
        log.info("PodContainerStarted %s role=%s mode=%s", pod_id, display_role, strategy)
        return {"pod_id": pod_id, "display_role": display_role}

    async def rename_self(self, *, pod_id: str, new_display_role: str) -> None:
        if not new_display_role.strip():
            raise ValueError("new_display_role must be non-empty")
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """UPDATE pods.pods SET display_role = $2
                     WHERE pod_id = $1
                     RETURNING (SELECT display_role FROM pods.pods WHERE pod_id = $1) AS old""",
                pod_id,
                new_display_role,
            )
            if row is None:
                raise ValueError(f"unknown pod_id: {pod_id}")
        await self._bus.publish_event(
            PodRenamed(
                pod_id=pod_id,
                new_display_role=new_display_role,
                old_display_role=row["old"],
            ),
            PODS_CONTEXT,
        )
        log.info("PodRenamed %s -> %s", pod_id, new_display_role)

    # ─── reactors (consume events from senate, observer) ────────────────

    async def on_proposal_closed(self, data: dict[str, Any]) -> None:
        """Apply approved senate proposals that touch a pod."""
        if data["outcome"] != "approved":
            return
        affected = data.get("affected") or []
        # senate now emits affected for admission/exile/image_swap as a
        # single pod_id (post-PR#6 fix). Match by what the row stores.
        for pod_id in affected:
            row = await self._fetch_pod(pod_id)
            if row is None:
                # admission of a not-yet-registered pod. Insert a placeholder
                # row; the pod will overwrite via register_self when it boots.
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """INSERT INTO pods.pods(pod_id, display_role, image_strategy)
                           VALUES($1, $1, 'code')
                           ON CONFLICT (pod_id) DO NOTHING""",
                        pod_id,
                    )
                row = await self._fetch_pod(pod_id)
            if row is None:
                continue
            # Idempotent admit: only mark + emit + write rule on the *first*
            # ProposalClosed fan-out. UPDATE…RETURNING gives us the prior
            # admitted state so redeliveries quietly drop.
            async with self._pool.acquire() as conn:
                already = await conn.fetchval(
                    """UPDATE pods.pods
                          SET admitted = TRUE,
                              admitted_at = COALESCE(admitted_at, now())
                        WHERE pod_id = $1 AND NOT admitted
                        RETURNING pod_id""",
                    pod_id,
                )
            if already is None:
                continue
            await self._bus.publish_event(
                PodAdmitted(pod_id=pod_id, display_role=row["display_role"]),
                PODS_CONTEXT,
            )
            try:
                write_rule(
                    dynamic_dir=traefik_dynamic_dir(),
                    pod_id=pod_id,
                    display_role=row["display_role"],
                    service_port=DEFAULT_SERVICE_PORT,
                )
            except OSError:
                log.exception("failed to write Traefik rule for %s", pod_id)

    async def on_pod_exited(self, data: dict[str, Any]) -> None:
        """Remove the pod's traefik rule when it leaves."""
        pod_id = data["pod_id"]
        try:
            remove_rule(dynamic_dir=traefik_dynamic_dir(), pod_id=pod_id)
        except OSError:
            log.exception("failed to remove Traefik rule for %s", pod_id)

    # ─── reads ──────────────────────────────────────────────────────────

    async def list_pods(self) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT pod_id, display_role, image_strategy, main_image,
                          admitted, admitted_at, exiled, spawned_at
                     FROM pods.pods ORDER BY spawned_at ASC"""
            )
        return [_row_to_dict(r) for r in rows]

    async def _fetch_pod(self, pod_id: str) -> asyncpg.Record | None:
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT pod_id, display_role, image_strategy FROM pods.pods WHERE pod_id = $1",
                pod_id,
            )


def _row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "pod_id": row["pod_id"],
        "display_role": row["display_role"],
        "image_strategy": row["image_strategy"],
        "main_image": row["main_image"],
        "admitted": row["admitted"],
        "admitted_at": (
            row["admitted_at"].isoformat() if isinstance(row["admitted_at"], datetime) else None
        ),
        "exiled": row["exiled"],
        "spawned_at": row["spawned_at"].isoformat(),
    }


# Unused-import shim: PodImageSwapped is referenced for future image-swap work.
_ = PodImageSwapped
