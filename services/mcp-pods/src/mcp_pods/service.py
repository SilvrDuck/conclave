"""Pod-lifecycle service. Owns the pods schema; writes traefik rules.

Spec ref: spec/05-ddd-contexts.md §C6.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import shutil
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
    PodsNuked,
)
from conclave_core.models import ImageStrategy

from mcp_pods.spawner import PODS_DIR, SpawnError, mint_pod_id, spawn_pod
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
        # Serialise NukePods invocations within the process. NATS can
        # redeliver if the handler exceeds ack_wait (default 30s) and
        # docker rm -f on a populated swarm can easily push past that.
        # Also guards against the architect spamming Reset from the UI.
        self._nuke_lock = asyncio.Lock()

    async def reconcile_orphans(self) -> int:
        """Run once on mcp-pods startup. If SpawnFirstPod inserted a
        placeholder (display_role='tbd', admitted=FALSE) but the pod's
        bootstrap.py crashed before register_self, the row sticks
        around and `count(non-exiled) > 0` permanently blocks the
        SpawnFirstPod policy. Reconcile by:

        1. Selecting orphan candidates: NOT exiled, NOT admitted,
           display_role IN ('tbd', pod_id) — that is, never renamed
           from the placeholder.
        2. For each: `docker container inspect conclave-<pod_id>`.
           - exit 0 + State.Running == True → live pod, leave it.
           - exit 0 + Running == False → exited; reap.
           - exit != 0 → no container at all; reap.
        3. Reap = remove the rendered pods/<id>/ dir + DELETE the
           pods.pods row.

        Returns the number of rows reaped. Safe to call multiple
        times; idempotent on already-clean state.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT pod_id FROM pods.pods
                    WHERE NOT exiled AND NOT admitted
                      AND (display_role = 'tbd' OR display_role = pod_id)"""
            )
        candidates = [r["pod_id"] for r in rows]
        if not candidates:
            return 0
        reaped: list[str] = []
        for pod_id in candidates:
            if await self._container_alive(pod_id):
                continue
            await self._reap_orphan(pod_id)
            reaped.append(pod_id)
        if reaped:
            log.warning(
                "orphan reconciler reaped %d placeholder pod row(s): %s",
                len(reaped), reaped,
            )
        return len(reaped)

    async def _container_alive(self, pod_id: str) -> bool:
        """True iff `conclave-<pod_id>` container exists and is Running."""
        proc = await asyncio.create_subprocess_exec(
            "docker", "container", "inspect",
            "--format", "{{.State.Running}}",
            f"conclave-{pod_id}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            return False
        if proc.returncode != 0:
            return False
        return stdout.decode().strip() == "true"

    async def _reap_orphan(self, pod_id: str) -> None:
        """Remove rendered dir + delete the pods.pods row."""
        pod_dir = PODS_DIR / pod_id
        if pod_dir.exists():
            shutil.rmtree(pod_dir, ignore_errors=True)
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM pods.pods WHERE pod_id = $1 AND NOT admitted",
                pod_id,
            )

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
        # CTE pattern: capture the *pre-update* role in `before`, then update
        # and return it. Without the CTE, a sub-SELECT in RETURNING sees the
        # post-update row (RETURNING runs after the UPDATE has applied).
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """WITH before AS (
                       SELECT display_role AS old_role, admitted FROM pods.pods
                        WHERE pod_id = $1 FOR UPDATE
                   ), upd AS (
                       UPDATE pods.pods SET display_role = $2
                        WHERE pod_id = $1
                        RETURNING pod_id
                   )
                   SELECT before.old_role, before.admitted FROM before, upd""",
                pod_id,
                new_display_role,
            )
            if row is None:
                raise ValueError(f"unknown pod_id: {pod_id}")
        await self._bus.publish_event(
            PodRenamed(
                pod_id=pod_id,
                new_display_role=new_display_role,
                old_display_role=row["old_role"],
            ),
            PODS_CONTEXT,
        )
        log.info(
            "PodRenamed %s: %r -> %r", pod_id, row["old_role"], new_display_role
        )
        # Rewrite the Traefik rule so <new_role>.conclave.local routes
        # to the same backend. Only admitted pods have rules to begin
        # with — non-admitted candidates don't have a hostname yet.
        if row["admitted"]:
            try:
                write_rule(
                    dynamic_dir=traefik_dynamic_dir(),
                    pod_id=pod_id,
                    display_role=new_display_role,
                    service_port=DEFAULT_SERVICE_PORT,
                )
            except OSError:
                log.exception("failed to rewrite Traefik rule for renamed %s", pod_id)

    # ─── reactors (consume events from senate, observer) ────────────────

    async def on_proposal_closed(self, data: dict[str, Any]) -> None:
        """Apply approved senate proposals that touch a pod.

        Currently handles admission (UPDATE admitted=TRUE + Traefik rule)
        and image_swap (UPDATE image_strategy/main_image + PodImageSwapped).
        Real container swap is deferred — the schema + event record the
        intent; the actual `docker compose up` of the new image is a
        follow-up.
        """
        if data["outcome"] != "approved":
            return
        affected = data.get("affected") or []
        # senate now emits affected for admission/exile/image_swap as a
        # single pod_id (post-PR#6 fix). Match by what the row stores.

        # Image swap is its own path because the senate payload carries
        # the new image/mode, and we need PodImageSwapped (not PodAdmitted).
        # The ProposalClosed event doesn't carry the payload, so we read it
        # back from the senate schema inside _handle_image_swap_close.
        if "Image swap" in str(data.get("summary", "")):
            await self._handle_image_swap_close(data["proposal_id"])
            return
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

    async def _handle_image_swap_close(self, proposal_id: str) -> None:
        """Look up the closed proposal in the senate schema, apply the
        image-swap on the pods row, and emit PodImageSwapped."""
        async with self._pool.acquire() as conn:
            # Read the payload directly from senate.proposals (cross-schema
            # read is acceptable; we don't write).
            row = await conn.fetchrow(
                """SELECT payload FROM senate.proposals
                     WHERE proposal_id = $1 AND outcome = 'approved'""",
                proposal_id,
            )
            if row is None or not row["payload"]:
                log.warning("image_swap proposal %s payload missing", proposal_id)
                return
            payload = row["payload"]
            pod_id = payload.get("pod_id")
            new_image = payload.get("new_image")
            new_mode = payload.get("new_mode", "code")
            if not pod_id or not new_image:
                return
            old = await conn.fetchrow(
                "SELECT main_image, image_strategy FROM pods.pods WHERE pod_id = $1",
                pod_id,
            )
            old_image = (old["main_image"] if old else None) or "code"
            await conn.execute(
                """UPDATE pods.pods
                      SET main_image = $2, image_strategy = $3
                    WHERE pod_id = $1""",
                pod_id,
                new_image,
                new_mode,
            )
        await self._bus.publish_event(
            PodImageSwapped(
                pod_id=pod_id,
                old_image=old_image,
                new_image=new_image,
                new_mode=new_mode,
            ),
            PODS_CONTEXT,
        )
        log.info("PodImageSwapped %s: %s -> %s (%s)", pod_id, old_image, new_image, new_mode)

    async def on_pod_exited(self, data: dict[str, Any]) -> None:
        """Remove the pod's traefik rule when it leaves."""
        pod_id = data["pod_id"]
        try:
            remove_rule(dynamic_dir=traefik_dynamic_dir(), pod_id=pod_id)
        except OSError:
            log.exception("failed to remove Traefik rule for %s", pod_id)

    async def on_nuke_pods(self, _data: dict[str, Any]) -> None:
        """ResetState reactor — stop every running conclave-pod-*
        container, remove every rendered pods/pod-*/ dir, drop any
        per-pod Traefik rule, then emit PodsNuked so operator can
        truncate the DB.

        Idempotent on already-clean state (no pods left still emits
        PodsNuked(nuked_count=0)). Serialised by _nuke_lock so NATS
        redeliveries don't run two teardowns in parallel."""
        async with self._nuke_lock:
            log.info("NukePods: tearing down all pod containers + dirs")
            # 1. list every container that matches the pod naming scheme.
            proc = await asyncio.create_subprocess_exec(
                "docker", "ps", "-a", "--filter", "name=conclave-pod-",
                "--format", "{{.Names}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            except TimeoutError:
                proc.kill()
                await proc.wait()
                log.error("NukePods: docker ps timed out")
                return
            containers = [n for n in stdout.decode().splitlines() if n.strip()]
            # 2. docker rm -f each, in parallel — sequential rm of N pods
            #    risks exceeding NATS ack_wait. asyncio.gather caps the
            #    end-to-end wait at the slowest single rm.
            async def _rm(name: str) -> None:
                try:
                    p = await asyncio.create_subprocess_exec(
                        "docker", "rm", "-f", name,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    _, err = await asyncio.wait_for(p.communicate(), timeout=30)
                    if p.returncode != 0:
                        log.warning(
                            "docker rm -f %s rc=%s: %s",
                            name, p.returncode, err.decode(errors='replace')[:200],
                        )
                except TimeoutError:
                    log.error("docker rm -f %s timed out", name)
            if containers:
                await asyncio.gather(*(_rm(c) for c in containers))
            # 3. remove rendered pods/pod-*/ dirs. We run as root inside the
            #    container so this works regardless of host UID; the dirs
            #    were owned by the host user (via _chown_to_host) so future
            #    `rm -rf` from the host also works.
            if PODS_DIR.exists():
                for child in PODS_DIR.iterdir():
                    if child.name.startswith("pod-"):
                        shutil.rmtree(child, ignore_errors=True)
            # 4. clear per-pod Traefik rules.
            dyn = traefik_dynamic_dir()
            if dyn.exists():
                for rule in dyn.glob("pod-*.yml"):
                    try:
                        rule.unlink()
                    except OSError:
                        log.exception("failed to remove Traefik rule %s", rule)
            # 5. signal operator that it's safe to truncate the DB.
            await self._bus.publish_event(
                PodsNuked(nuked_count=len(containers)), PODS_CONTEXT,
            )
            log.info("NukePods done — %d container(s) removed", len(containers))

    async def on_restart_pod(self, data: dict[str, Any]) -> None:
        """ATAM Op4 — restart the named pod's container.

        Augustus issues this via the Forum to recover a misbehaving
        pod without exiling it. We invoke `docker restart` against
        the conclave-<pod_id> container; Docker preserves the
        container's identity + bind-mounts, so the agent resumes on
        the next inbox event."""
        import asyncio as _asyncio  # local: only on this path
        pod_id = data.get("pod_id")
        if not pod_id or not isinstance(pod_id, str):
            log.warning("RestartPod missing pod_id; data=%r", data)
            return
        container = f"conclave-{pod_id}"
        log.info("RestartPod: docker restart %s", container)
        proc = await _asyncio.create_subprocess_exec(
            "docker", "restart", container,
            stdout=_asyncio.subprocess.PIPE,
            stderr=_asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await _asyncio.wait_for(proc.communicate(), timeout=30)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            log.error("docker restart %s timed out", container)
            return
        if proc.returncode != 0:
            log.error(
                "docker restart %s failed rc=%s: %s",
                container, proc.returncode, stderr.decode(errors="replace")[:300],
            )

    async def on_pod_admitted(self, data: dict[str, Any]) -> None:
        """BroadcastMembership policy — spec/02 Phase 3.

        Fanout the new pod's membership into every existing peer's
        inbox so the swarm doesn't have to poll state.members. The
        published subject is core NATS (conclave.inbox.<peer_id>),
        matching the per-pod subscription in pods/_template/agent/
        bootstrap.py. Not JetStream — the inbox is best-effort fanout,
        not durable state; persistent peers will catch up via state
        reads when they boot."""
        new_pod = data["pod_id"]
        new_role = data["display_role"]
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT pod_id FROM pods.pods
                    WHERE admitted AND NOT exiled AND pod_id <> $1""",
                new_pod,
            )
        if not rows:
            return
        body = json.dumps(
            {
                "event_type": "MembershipChange",
                "action": "admitted",
                "pod_id": new_pod,
                "display_role": new_role,
                "occurred_at": data.get("occurred_at"),
            }
        ).encode()
        peer_ids = [r["pod_id"] for r in rows]
        for peer in peer_ids:
            try:
                await self._bus.nc.publish(f"conclave.inbox.{peer}", body)
            except Exception:
                log.exception("inbox fanout to %s failed", peer)
        log.info(
            "BroadcastMembership: new pod %s announced to %d peers",
            new_pod,
            len(peer_ids),
        )

    async def on_proclamation_issued(self, _data: dict[str, Any]) -> None:
        """SpawnFirstPod policy — spec/02 Phase 1 last row.

        Race-safe under NATS redelivery via a transaction-scoped
        Postgres advisory lock. asyncpg's default isolation is READ
        COMMITTED, so a plain COUNT+INSERT lets two concurrent
        deliveries each see zero pods and both insert new pod_ids
        (different PKs, so no unique-constraint backstop). The
        advisory lock serialises the check-and-claim instead.

        Test gate: when `CONCLAVE_DISABLE_SPAWN_FIRST_POD=true`,
        short-circuit without spawning. Smoke tests issue
        proclamations without wanting a real pod-spawn + Claude
        budget burn. Kanban #86.
        """
        if os.environ.get("CONCLAVE_DISABLE_SPAWN_FIRST_POD", "").lower() in {
            "1", "true", "yes"
        }:
            log.info("SpawnFirstPod gate set; skipping spawn")
            return
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Lock key derived from the policy name; the same key
                # for every delivery so concurrent calls queue.
                await conn.execute(
                    "SELECT pg_advisory_xact_lock("
                    "hashtextextended('mcp-pods:spawn-first', 0)"
                    ")"
                )
                n = await conn.fetchval(
                    "SELECT COUNT(*) FROM pods.pods WHERE NOT exiled"
                )
                if n > 0:
                    return
                pod_id = mint_pod_id()
                display_role = "tbd"
                await conn.execute(
                    """INSERT INTO pods.pods(pod_id, display_role, image_strategy)
                       VALUES($1, $2, 'code')""",
                    pod_id,
                    display_role,
                )
        log.info("SpawnFirstPod claiming %s", pod_id)
        try:
            await spawn_pod(pod_id, display_role)
        except SpawnError:
            log.exception("SpawnFirstPod failed for %s", pod_id)
            # Roll the placeholder back so a retry can re-claim.
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM pods.pods WHERE pod_id = $1 AND NOT admitted",
                    pod_id,
                )
            raise

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


