"""End-to-end smoke test: the platform's happy path through the bus.

Asserts:
  1. Observer is healthy.
  2. POST /commands {kind:IssueProclamation} → proclamation row appears.
  3. mcp-decisions auto-creates a placeholder ADR for the proclamation
     within a short SSE-driven window.
  4. mcp-senate's MCP tool propose_admission opens a proposal that
     auto-closes (N=1 trivial pass via consensus_omnium with the
     proposer auto-casting YES). A sealed ADR appears.
  5. mcp-coms accepts a SendDirectMessage from the Forum and creates a
     2-party private council with a needs-Augustus flag.

Run against the live stack (`docker compose --profile conclave up -d`):
    uv run pytest tests/test_e2e_smoke.py -v
"""

from __future__ import annotations

import asyncio
import secrets
import time
from typing import Any

import httpx
import pytest
from fastmcp.client import Client

OBSERVER = "http://localhost:8000"
SENATE_MCP = "http://localhost:8101/mcp"
COMS_MCP = "http://localhost:8102/mcp"


async def _wait_for(
    pred: Any,
    *,
    timeout: float = 15.0,
    interval: float = 0.5,
) -> Any:
    deadline = time.monotonic() + timeout
    last: Any = None
    while time.monotonic() < deadline:
        last = await pred()
        if last:
            return last
        await asyncio.sleep(interval)
    raise AssertionError(f"timed out waiting; last={last!r}")


@pytest.mark.asyncio
async def test_healthz() -> None:
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{OBSERVER}/healthz", timeout=5)
        r.raise_for_status()
        assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_proclamation_flow_creates_placeholder_decision() -> None:
    """POST IssueProclamation → row in operator.proclamations →
    ProclamationIssued bus event → mcp-decisions creates a placeholder."""
    marker = secrets.token_hex(4)
    text = f"e2e smoke {marker}: listen to music, see lyrics scroll, jam"

    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{OBSERVER}/commands",
            json={"kind": "IssueProclamation", "text": text},
            timeout=5,
        )
        assert r.status_code == 200, r.text

        async def latest() -> dict | None:
            r = await c.get(f"{OBSERVER}/state/proclamations", timeout=5)
            for row in r.json():
                if row["text"] == text:
                    return row
            return None

        proc = await _wait_for(latest)
        assert proc["status"] == "open"
        seq = proc["seq"]

        async def placeholder() -> dict | None:
            r = await c.get(f"{OBSERVER}/state/decisions", timeout=5)
            for d in r.json():
                if d["origin"]["kind"] == "proclamation" and d["origin"]["id"] == str(seq):
                    return d
            return None

        d = await _wait_for(placeholder)
        assert d["status"] == "placeholder"
        assert d["title"].startswith("Architecture for:")


@pytest.mark.asyncio
async def test_malformed_command_is_rejected_at_edge() -> None:
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{OBSERVER}/commands",
            json={"kind": "BogusCommand"},
            timeout=5,
        )
        assert r.status_code == 422
        # Discriminated-union error mentions the 4 valid tags.
        detail = r.json()["detail"]
        msg = str(detail)
        for kind in ("IssueProclamation", "SendDirectMessage", "EditCharter", "CastBallot"):
            assert kind in msg


@pytest.mark.asyncio
async def test_senate_admission_n1_trivial_pass() -> None:
    """Open an admission proposal with consensus_omnium and N=1 eligible.
    The proposer's auto-cast YES should close it as approved without any
    special-case bootstrap path."""
    candidate = f"smoke-pod-{secrets.token_hex(3)}"
    async with Client(SENATE_MCP, timeout=10.0) as c:
        r = await c.call_tool(
            "propose_admission",
            {
                "proposer": candidate,
                "candidate_pod_id": candidate,
                "candidate_charter": "smoke test charter",
                "eligible_voters": [candidate],
                "strategy": "consensus_omnium",
            },
        )
        proposal_id = r.data["proposal_id"]

        async def closed() -> dict | None:
            r = await c.call_tool("outcome", {"proposal_id": proposal_id})
            data = r.data
            if data and data.get("outcome") and data["outcome"] != "open":
                return data
            return None

        out = await _wait_for(closed)
        assert out["outcome"] == "approved"


@pytest.mark.asyncio
async def test_senate_majority_decides_early() -> None:
    """Majority strategy with N=3, 2 YES → APPROVED immediately."""
    voters = [f"smoke-v{i}-{secrets.token_hex(2)}" for i in range(3)]
    async with Client(SENATE_MCP, timeout=10.0) as c:
        r = await c.call_tool(
            "propose_completion",
            {
                "proposer": voters[0],
                "proclamation_seq": 999,
                "summary": "smoke majority test",
                "eligible_voters": voters,
                "strategy": "majority",
            },
        )
        proposal_id = r.data["proposal_id"]

        # voters[0] auto-cast YES at open. Add a second YES → 2/3 ≥ half+1.
        await c.call_tool(
            "cast_ballot",
            {"proposal_id": proposal_id, "voter": voters[1], "choice": "yes"},
        )

        async def closed() -> dict | None:
            r = await c.call_tool("outcome", {"proposal_id": proposal_id})
            data = r.data
            if data and data.get("outcome") and data["outcome"] != "open":
                return data
            return None

        out = await _wait_for(closed)
        assert out["outcome"] == "approved"


@pytest.mark.asyncio
async def test_coms_dm_creates_needs_augustus_council() -> None:
    """Sending a DM as the Forum (via observer /commands) creates a
    2-party private council with needs_augustus=True."""
    target = f"smoke-dm-{secrets.token_hex(3)}"
    body = f"smoke dm {secrets.token_hex(3)}"
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{OBSERVER}/commands",
            json={"kind": "SendDirectMessage", "pod_id": target, "body": body},
            timeout=5,
        )
        assert r.status_code == 200

        async def dm_council() -> dict | None:
            r = await c.get(f"{OBSERVER}/state/councils", timeout=5)
            for c_ in r.json():
                if (
                    c_["private"]
                    and "__augustus__" in c_["participants"]
                    and target in c_["participants"]
                ):
                    return c_
            return None

        council = await _wait_for(dm_council)
        assert council["needs_augustus"] is True
        # The first message should be in the council.
        r = await c.get(
            f"{OBSERVER}/state/councils/{council['council_id']}/messages",
            timeout=5,
        )
        msgs = r.json()
        assert any(m["body"] == body for m in msgs)
