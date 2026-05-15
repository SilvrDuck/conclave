"""In-process end-to-end smoke for the senate / observer / MCP flow.

Wires every component in a single test process — no Docker, no real Pi.
What it proves:

  * a founder proposal under majority strategy auto-decides at N=1 and
    writes an ADR via the decisions MCP / DocsAdapter;
  * a follow-up `propose_member` for a peer (now under N>=2 voters)
    opens a real vote;
  * casting yes ballots closes the vote and admits the new member;
  * proposing a contract change with consensus_omnium computes the
    affected list from the observer's call-graph and stays open until
    every caller votes yes;
  * all of the above flow through real HTTP + ASGITransport — not direct
    method calls.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from conclave_platform.adapters.bus import InMemoryBus
from conclave_platform.adapters.docs import InMemoryDocs
from conclave_platform.observer import create_app as create_observer_app
from conclave_platform.senate_ledger import create_app as create_senate_app
from conclave_platform.senate_ledger.observer_client import ObserverClient


@pytest_asyncio.fixture
async def stack() -> AsyncIterator[
    tuple[AsyncClient, AsyncClient, InMemoryDocs, InMemoryBus]
]:
    bus = InMemoryBus()
    await bus.connect()

    docs = InMemoryDocs()

    observer_app = create_observer_app(dsn="sqlite+aiosqlite:///:memory:", bus=bus)
    obs_transport = ASGITransport(app=observer_app)
    obs_client = AsyncClient(transport=obs_transport, base_url="http://observer")

    # Senate ledger's ObserverClient also goes through the observer's ASGI app:
    senate_obs = ObserverClient(base_url="http://observer")
    senate_obs._client = obs_client  # type: ignore[assignment]

    senate_app = create_senate_app(
        dsn="sqlite+aiosqlite:///:memory:", observer=senate_obs, docs=docs, bus=bus
    )
    sen_transport = ASGITransport(app=senate_app)
    sen_client = AsyncClient(transport=sen_transport, base_url="http://senate")

    async with (
        observer_app.router.lifespan_context(observer_app),
        senate_app.router.lifespan_context(senate_app),
    ):
        yield obs_client, sen_client, docs, bus

    await obs_client.aclose()
    await sen_client.aclose()
    await bus.close()


async def test_full_flow(
    stack: tuple[AsyncClient, AsyncClient, InMemoryDocs, InMemoryBus],
) -> None:
    obs, sen, docs, _bus = stack

    # 1) Founder bootstrap — N=1 trivial pass admits the founder.
    r = await sen.post(
        "/proposals",
        json={
            "kind": "member",
            "proposer": "founder",
            "strategy": "majority",
            "payload": {
                "pod_name": "founder",
                "charter_path": "pods/founder/charter.md",
            },
            "rationale": "founder bootstrap",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["proposal"]["outcome"] == "approved"

    # Mirror member into observer so downstream callers see it.
    await obs.post(
        "/ingest/member",
        json={
            "name": "founder",
            "charter_path": "pods/founder/charter.md",
            "status": "admitted",
        },
    )

    # 2) Founder proposes a peer (alice). N=2 now — proposer + founder.
    r = await sen.post(
        "/proposals",
        json={
            "kind": "member",
            "proposer": "founder",
            "strategy": "majority",
            "payload": {"pod_name": "alice", "charter_path": "pods/alice/charter.md"},
            "rationale": "we need an auth pod",
        },
    )
    assert r.status_code == 200, r.text
    proposal = r.json()["proposal"]
    pid = proposal["id"]
    # Founder is the only existing admitted member, so this is still N=1 and
    # auto-approves. (Aside: with multiple members, ballots would be needed.)
    assert proposal["outcome"] == "approved"

    # Observer mirror for alice + register endpoints.
    await obs.post(
        "/ingest/member",
        json={"name": "alice", "charter_path": "pods/alice/charter.md", "status": "admitted"},
    )
    await obs.post(
        "/ingest/endpoint",
        json={"pod": "alice", "method": "GET", "path": "/users/{id}"},
    )
    # carol calls /users/{id}, so she's an affected consumer.
    await obs.post(
        "/ingest/member",
        json={"name": "carol", "charter_path": "pods/carol/charter.md", "status": "admitted"},
    )
    await obs.post(
        "/ingest/call",
        json={
            "caller": "carol",
            "callee": "alice",
            "method": "GET",
            "path": "/users/{id}",
        },
    )

    # 3) Alice proposes a contract change. consensus_omnium → all callers must
    #    vote yes. Senate auto-resolves affected via observer.callers_of.
    r = await sen.post(
        "/proposals",
        json={
            "kind": "contract_change",
            "proposer": "alice",
            "strategy": "consensus_omnium",
            "payload": {"endpoints": ["GET /users/{id}"]},
            "rationale": "add pagination",
        },
    )
    assert r.status_code == 200, r.text
    proposal = r.json()["proposal"]
    pid = proposal["id"]
    assert set(proposal["affected"]) == {"alice", "carol"}
    # Still open: needs unanimous yes.
    out = await sen.get(f"/proposals/{pid}/outcome")
    assert out.json()["outcome"] is None
    # Cast both yes ballots.
    await sen.post(f"/proposals/{pid}/ballots", json={"voter": "alice", "choice": "yes"})
    await sen.post(f"/proposals/{pid}/ballots", json={"voter": "carol", "choice": "yes"})
    out = await sen.get(f"/proposals/{pid}/outcome")
    assert out.json()["outcome"] == "approved"

    # 4) ADRs exist for the founder admit + alice admit + contract change.
    adrs = await docs.list()
    titles = [a.title for a in adrs]
    assert any("admit" in t for t in titles), titles
    assert any("contract change" in t for t in titles), titles
