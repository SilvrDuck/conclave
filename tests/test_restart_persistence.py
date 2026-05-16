"""§10 acceptance: stack restart preserves state.

R2 from spec/08-v2-acceptance.md / spec/06-atam.md:
> Stack restart (`docker compose down && up`) preserves proclamations,
> admitted pods, charters, decisions, council transcripts.

This test is intentionally heavyweight — it cycles real containers.
Skip it in fast CI; run as part of the acceptance pre-flight:

    uv run pytest tests/test_restart_persistence.py -v -s
"""

from __future__ import annotations

import asyncio
import os
import secrets
import subprocess
import time

import httpx
import pytest

OBSERVER = os.environ.get("CONCLAVE_OBSERVER_URL", "http://localhost:8000")
COMPOSE = ["docker", "compose", "-f", "infra/compose.yaml"]


def _down() -> None:
    subprocess.run(COMPOSE + ["--profile", "conclave", "down"], check=True, timeout=60)


def _up() -> None:
    subprocess.run(
        COMPOSE + ["--profile", "conclave", "up", "-d"], check=True, timeout=120
    )


async def _wait_for_observer(timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{OBSERVER}/healthz", timeout=2)
                if r.status_code == 200:
                    return
        except (httpx.HTTPError, httpx.ConnectError):
            pass
        await asyncio.sleep(1)
    raise AssertionError("observer never became healthy")


@pytest.mark.asyncio
async def test_restart_preserves_state() -> None:
    # Seed: issue a proclamation with a unique marker so we know it's ours.
    marker = secrets.token_hex(4)
    text = f"r2 persistence test {marker}"
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{OBSERVER}/commands",
            json={"kind": "IssueProclamation", "text": text},
            timeout=5,
        )
        assert r.status_code == 200
        # wait for it to land
        for _ in range(20):
            r = await c.get(f"{OBSERVER}/state/proclamations", timeout=5)
            if any(p["text"] == text for p in r.json()):
                break
            await asyncio.sleep(0.5)
        else:
            raise AssertionError("seed proclamation never landed")

        # Snapshot before restart
        before_pods = (await c.get(f"{OBSERVER}/state/pods", timeout=5)).json()
        before_decs = (await c.get(f"{OBSERVER}/state/decisions", timeout=5)).json()
        before_cons = (await c.get(f"{OBSERVER}/state/councils", timeout=5)).json()

    # Restart the platform.
    _down()
    _up()
    await _wait_for_observer()

    # Verify everything we had is still there.
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{OBSERVER}/state/proclamations", timeout=5)
        assert any(p["text"] == text for p in r.json()), "proclamation lost"

        after_pods = (await c.get(f"{OBSERVER}/state/pods", timeout=5)).json()
        after_decs = (await c.get(f"{OBSERVER}/state/decisions", timeout=5)).json()
        after_cons = (await c.get(f"{OBSERVER}/state/councils", timeout=5)).json()

    # pods may flip runtime_status as they were stopped → restored; what
    # matters is the rows are still present.
    assert {p["pod_id"] for p in after_pods} >= {p["pod_id"] for p in before_pods}, (
        "lost pods on restart"
    )
    assert {d["decision_id"] for d in after_decs} >= {d["decision_id"] for d in before_decs}, (
        "lost decisions on restart"
    )
    assert {c["council_id"] for c in after_cons} >= {c["council_id"] for c in before_cons}, (
        "lost councils on restart"
    )
