"""GET /state/* — Forum read paths.

Every endpoint returns plain JSON projected from the observer schema. No
business logic here; just selects and shape-conversions.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/state", tags=["state"])

# Filesystem reads (charter / workspace tree / spec) live behind PROJECT_DIR
# which the compose mount bind-mounts RO from the host project root.
_PROJECT_DIR = Path(os.environ.get("PROJECT_DIR", "/workspace"))
# Pod ids are minted as `pod-<hex>`, but the schema accepts any TEXT.
# We restrict to a conservative slug to defeat path traversal.
_POD_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_SPEC_NAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+\.md$")
# Cap workspace file listing so a runaway pod can't OOM the Forum.
_MAX_WORKSPACE_ENTRIES = 500


@router.get("/pods")
async def list_pods(request: Request) -> list[dict[str, Any]]:
    pool = request.app.state.observer.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT pod_id, display_role, image_strategy, runtime_status,
                      agent_state, main_image, admitted, public_url, last_seen
                 FROM observer.pod_state
                 ORDER BY last_seen DESC"""
        )
    return [
        {
            "pod_id": r["pod_id"],
            "display_role": r["display_role"],
            "image_strategy": r["image_strategy"],
            "runtime_status": r["runtime_status"],
            "agent_state": r["agent_state"],
            "main_image": r["main_image"],
            "admitted": r["admitted"],
            "public_url": r["public_url"],
            "last_seen": r["last_seen"].isoformat(),
        }
        for r in rows
    ]


@router.get("/proclamations")
async def list_proclamations(request: Request) -> list[dict[str, Any]]:
    pool = request.app.state.observer.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT seq, text, issued_at, status, summary,
                      completed_at, placeholder_decision_id
                 FROM operator.proclamations ORDER BY seq DESC"""
        )
    return [
        {
            "seq": r["seq"],
            "text": r["text"],
            "issued_at": r["issued_at"].isoformat(),
            "status": r["status"],
            "summary": r["summary"],
            "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
            "placeholder_decision_id": r["placeholder_decision_id"],
        }
        for r in rows
    ]


@router.get("/proposals")
async def list_proposals(request: Request) -> list[dict[str, Any]]:
    pool = request.app.state.observer.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT proposal_id, kind, proposer, strategy, summary, payload,
                      eligible_voters, deadline, outcome, opened_at, closed_at
                 FROM senate.proposals ORDER BY opened_at DESC LIMIT 100"""
        )
        ballots = await conn.fetch(
            "SELECT proposal_id, voter, choice, comment, cast_at FROM senate.ballots"
        )
    by_prop: dict[str, list[dict[str, Any]]] = {}
    for b in ballots:
        by_prop.setdefault(b["proposal_id"], []).append(
            {
                "voter": b["voter"],
                "choice": b["choice"],
                "comment": b["comment"],
                "cast_at": b["cast_at"].isoformat(),
            }
        )
    return [
        {
            "proposal_id": r["proposal_id"],
            "kind": r["kind"],
            "proposer": r["proposer"],
            "strategy": r["strategy"],
            "summary": r["summary"],
            "payload": r["payload"],
            "eligible_voters": list(r["eligible_voters"]),
            "deadline": r["deadline"].isoformat(),
            "outcome": r["outcome"],
            "opened_at": r["opened_at"].isoformat(),
            "closed_at": r["closed_at"].isoformat() if r["closed_at"] else None,
            "ballots": by_prop.get(r["proposal_id"], []),
        }
        for r in rows
    ]


@router.get("/councils")
async def list_councils(request: Request) -> list[dict[str, Any]]:
    pool = request.app.state.observer.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT council_id, topic, participants, private, status,
                      opened_at, closed_at, summary, decision_id, needs_augustus
                 FROM council.councils ORDER BY opened_at DESC LIMIT 100"""
        )
    return [
        {
            "council_id": r["council_id"],
            "topic": r["topic"],
            "participants": list(r["participants"]),
            "private": r["private"],
            "needs_augustus": r["needs_augustus"],
            "status": r["status"],
            "opened_at": r["opened_at"].isoformat(),
            "closed_at": r["closed_at"].isoformat() if r["closed_at"] else None,
            "summary": r["summary"],
            "decision_id": r["decision_id"],
        }
        for r in rows
    ]


@router.get("/councils/{council_id}/messages")
async def list_council_messages(request: Request, council_id: str) -> list[dict[str, Any]]:
    pool = request.app.state.observer.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT seq, from_pod, body, sent_at
                 FROM council.messages WHERE council_id = $1
                 ORDER BY seq ASC""",
            council_id,
        )
    return [
        {
            "seq": r["seq"],
            "from_pod": r["from_pod"],
            "body": r["body"],
            "sent_at": r["sent_at"].isoformat(),
        }
        for r in rows
    ]


@router.get("/decisions")
async def list_decisions(request: Request) -> list[dict[str, Any]]:
    pool = request.app.state.observer.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT decision_id, title, body, affected, origin_kind,
                      origin_id, status, created_at, sealed_at
                 FROM decisions.decisions ORDER BY created_at DESC LIMIT 100"""
        )
    return [
        {
            "decision_id": r["decision_id"],
            "title": r["title"],
            "body": r["body"],
            "affected": list(r["affected"]),
            "origin": {"kind": r["origin_kind"], "id": r["origin_id"]},
            "status": r["status"],
            "created_at": r["created_at"].isoformat(),
            "sealed_at": r["sealed_at"].isoformat() if r["sealed_at"] else None,
        }
        for r in rows
    ]


@router.get("/calls")
async def list_calls(request: Request, since_seconds: int = 60) -> list[dict[str, Any]]:
    pool = request.app.state.observer.pool
    cutoff = datetime.now(UTC) - timedelta(seconds=since_seconds)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT src_pod, dst_pod, method, path, status, latency_ms, observed_at
                 FROM observer.calls WHERE observed_at >= $1
                 ORDER BY observed_at DESC LIMIT 500""",
            cutoff,
        )
    return [
        {
            "src_pod": r["src_pod"],
            "dst_pod": r["dst_pod"],
            "method": r["method"],
            "path": r["path"],
            "status": r["status"],
            "latency_ms": r["latency_ms"],
            "observed_at": r["observed_at"].isoformat(),
        }
        for r in rows
    ]


@router.get("/endpoints")
async def list_endpoints(request: Request, pod_id: str | None = None) -> list[dict[str, Any]]:
    pool = request.app.state.observer.pool
    async with pool.acquire() as conn:
        if pod_id:
            rows = await conn.fetch(
                "SELECT pod_id, method, path, annotation, first_seen, last_seen "
                "FROM observer.endpoints WHERE pod_id = $1 ORDER BY path",
                pod_id,
            )
        else:
            rows = await conn.fetch(
                "SELECT pod_id, method, path, annotation, first_seen, last_seen "
                "FROM observer.endpoints ORDER BY pod_id, path"
            )
    return [
        {
            "pod_id": r["pod_id"],
            "method": r["method"],
            "path": r["path"],
            "annotation": r["annotation"],
            "first_seen": r["first_seen"].isoformat(),
            "last_seen": r["last_seen"].isoformat(),
        }
        for r in rows
    ]


@router.get("/activity")
async def list_activity(request: Request, limit: int = 200) -> list[dict[str, Any]]:
    pool = request.app.state.observer.pool
    limit = max(1, min(limit, 1000))
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT event_id, event_type, payload, occurred_at FROM observer.activity "
            "ORDER BY occurred_at DESC LIMIT $1",
            limit,
        )
    return [
        {
            "event_id": r["event_id"],
            "event_type": r["event_type"],
            "payload": r["payload"],
            "occurred_at": r["occurred_at"].isoformat(),
        }
        for r in rows
    ]


@router.get("/digests")
async def list_digests(request: Request, limit: int = 24) -> list[dict[str, Any]]:
    pool = request.app.state.observer.pool
    limit = max(1, min(limit, 168))
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT hour_bucket, summary, item_count FROM observer.digests "
            "ORDER BY hour_bucket DESC LIMIT $1",
            limit,
        )
    return [
        {
            "hour_bucket": r["hour_bucket"].isoformat(),
            "summary": r["summary"],
            "item_count": r["item_count"],
        }
        for r in rows
    ]


def _validate_pod_id(pod_id: str) -> None:
    if not _POD_ID_RE.match(pod_id):
        raise HTTPException(status_code=400, detail="invalid pod_id format")


@router.get("/pods/{pod_id}/charter")
async def get_pod_charter(pod_id: str) -> dict[str, Any]:
    """Read the pod's charter.md from disk so the Forum charter editor
    can pre-load it (J7) and the PodDrawer can render the rules above
    the tabs. The charter is mounted RO into the pod and written
    on-host; observer mirrors the host view."""
    _validate_pod_id(pod_id)
    charter = _PROJECT_DIR / "pods" / pod_id / "charter.md"
    if not charter.is_file():
        raise HTTPException(status_code=404, detail="charter not found")
    body = charter.read_text(encoding="utf-8")
    stat = charter.stat()
    return {
        "pod_id": pod_id,
        "path": str(charter.relative_to(_PROJECT_DIR)),
        "body": body,
        "size": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
    }


@router.get("/pods/{pod_id}/files")
async def list_pod_files(pod_id: str) -> dict[str, Any]:
    """List files in the pod's workspace/ directory. Returns a flat
    list with relative paths so the Forum can render a file tree.
    Caps results to keep responses bounded."""
    _validate_pod_id(pod_id)
    workspace = _PROJECT_DIR / "pods" / pod_id / "workspace"
    if not workspace.is_dir():
        raise HTTPException(status_code=404, detail="workspace not found")
    entries: list[dict[str, Any]] = []
    for p in sorted(workspace.rglob("*")):
        if len(entries) >= _MAX_WORKSPACE_ENTRIES:
            break
        # Ignore __pycache__, .pyc, hidden files — they're noise.
        if any(part.startswith(".") or part == "__pycache__" for part in p.relative_to(workspace).parts):
            continue
        if p.is_dir():
            kind = "dir"
            size = None
        else:
            kind = "file"
            size = p.stat().st_size
        entries.append(
            {
                "path": str(p.relative_to(workspace)),
                "kind": kind,
                "size": size,
            }
        )
    return {
        "pod_id": pod_id,
        "root": str(workspace.relative_to(_PROJECT_DIR)),
        "truncated": len(entries) >= _MAX_WORKSPACE_ENTRIES,
        "entries": entries,
    }


@router.get("/pods/{pod_id}/turns")
async def list_pod_turns(
    request: Request, pod_id: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Recent agent turns for a pod (most recent first). Used by the
    Forum's Thinking tab to render J4's per-turn transcript."""
    _validate_pod_id(pod_id)
    limit = max(1, min(limit, 100))
    pool = request.app.state.observer.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT turn_id, started_at, ended_at, tokens_in, tokens_out
                 FROM observer.agent_turns
                WHERE pod_id = $1
                ORDER BY started_at DESC
                LIMIT $2""",
            pod_id,
            limit,
        )
    return [
        {
            "turn_id": r["turn_id"],
            "started_at": r["started_at"].isoformat() if r["started_at"] else None,
            "ended_at": r["ended_at"].isoformat() if r["ended_at"] else None,
            "tokens_in": r["tokens_in"],
            "tokens_out": r["tokens_out"],
            "status": "ended" if r["ended_at"] else "in_flight",
        }
        for r in rows
    ]


@router.get("/spec/{filename}")
async def get_spec_file(filename: str) -> dict[str, Any]:
    """Read a spec/<filename>.md so the Forum 'Spec' link can render
    it inline. Filenames are restricted to bare `<name>.md` (no
    path components) to defeat traversal."""
    if not _SPEC_NAME_RE.match(filename):
        raise HTTPException(status_code=400, detail="invalid spec filename")
    spec_path = _PROJECT_DIR / "spec" / filename
    if not spec_path.is_file():
        raise HTTPException(status_code=404, detail="spec file not found")
    body = spec_path.read_text(encoding="utf-8")
    return {
        "filename": filename,
        "path": str(spec_path.relative_to(_PROJECT_DIR)),
        "body": body,
        "size": spec_path.stat().st_size,
    }
