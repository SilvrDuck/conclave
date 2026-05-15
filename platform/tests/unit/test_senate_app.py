"""End-to-end-ish tests for the senate ledger over its HTTP surface.

Uses InMemoryDocs + a fake ObserverClient + InMemoryBus.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from conclave_platform.adapters.bus import InMemoryBus
from conclave_platform.adapters.docs import InMemoryDocs
from conclave_platform.core import PodName
from conclave_platform.senate_ledger import create_app
from conclave_platform.senate_ledger.observer_client import ObserverClient


class _FakeObserverClient(ObserverClient):
    def __init__(self) -> None:
        # Skip httpx setup; we override the methods used by the senate.
        self._admitted: list[PodName] = []
        self._callers: dict[str, list[PodName]] = {}

    async def close(self) -> None:  # type: ignore[override]
        return None

    async def list_admitted_members(self) -> list[PodName]:  # type: ignore[override]
        return list(self._admitted)

    async def callers_of(self, *, method: str, path: str) -> list[PodName]:  # type: ignore[override]
        return self._callers.get(f"{method.upper()} {path}", [])


SenateFixture = tuple[AsyncClient, _FakeObserverClient, InMemoryDocs, InMemoryBus]


@pytest_asyncio.fixture
async def client() -> AsyncIterator[SenateFixture]:
    observer = _FakeObserverClient()
    docs = InMemoryDocs()
    bus = InMemoryBus()
    await bus.connect()
    app = create_app(
        dsn="sqlite+aiosqlite:///:memory:",
        observer=cast(ObserverClient, observer),
        docs=docs,
        bus=bus,
    )
    transport = ASGITransport(app=app)
    async with (
        AsyncClient(transport=transport, base_url="http://t") as http,
        app.router.lifespan_context(app),
    ):
        yield http, observer, docs, bus
    await bus.close()


async def test_health(
    client: SenateFixture,
) -> None:
    http, _, _, _ = client
    r = await http.get("/healthz")
    assert r.status_code == 200


async def test_founder_n1_member_proposal_auto_approves(
    client: SenateFixture,
) -> None:
    http, observer, docs, _ = client
    observer._admitted = []  # senate has no members yet
    r = await http.post(
        "/proposals",
        json={
            "kind": "member",
            "proposer": "founder",
            "strategy": "majority",
            "payload": {"pod_name": "founder", "charter_path": "pods/founder/charter.md"},
            "rationale": "founder bootstrap",
        },
    )
    assert r.status_code == 200, r.text
    proposal = r.json()["proposal"]
    assert proposal["outcome"] == "approved"
    members = await http.get("/members")
    assert "founder" in members.json()["members"]
    adrs = await docs.list()
    assert any("admit" in a.title for a in adrs)


async def test_contract_change_uses_callers_from_observer(
    client: SenateFixture,
) -> None:
    http, observer, _docs, _ = client
    observer._admitted = [PodName("bob"), PodName("alice"), PodName("carol")]
    observer._callers["GET /users/{id}"] = [PodName("alice"), PodName("carol")]
    r = await http.post(
        "/proposals",
        json={
            "kind": "contract_change",
            "proposer": "bob",
            "strategy": "consensus_omnium",
            "payload": {"endpoints": ["GET /users/{id}"], "rationale": "add paging"},
            "rationale": "add paging",
        },
    )
    assert r.status_code == 200, r.text
    proposal = r.json()["proposal"]
    assert set(proposal["affected"]) == {"alice", "bob", "carol"}
    # Still open: needs unanimous yes.
    pid = proposal["id"]
    for voter in ("bob", "alice", "carol"):
        rr = await http.post(
            f"/proposals/{pid}/ballots",
            json={"voter": voter, "choice": "yes"},
        )
        assert rr.status_code == 200
    final = await http.get(f"/proposals/{pid}/outcome")
    assert final.json()["outcome"] == "approved"


async def test_one_dissent_rejects_consensus_omnium(
    client: SenateFixture,
) -> None:
    http, observer, _docs, _ = client
    observer._admitted = [PodName("alice"), PodName("bob")]
    r = await http.post(
        "/proposals",
        json={
            "kind": "contract_change",
            "proposer": "alice",
            "strategy": "consensus_omnium",
            "payload": {"endpoints": []},
            "affected_override": ["alice", "bob"],
        },
    )
    pid = r.json()["proposal"]["id"]
    await http.post(
        f"/proposals/{pid}/ballots", json={"voter": "alice", "choice": "yes"}
    )
    await http.post(
        f"/proposals/{pid}/ballots", json={"voter": "bob", "choice": "no"}
    )
    final = await http.get(f"/proposals/{pid}/outcome")
    assert final.json()["outcome"] == "rejected"


async def test_open_proposal_listing(
    client: SenateFixture,
) -> None:
    http, observer, _docs, _ = client
    observer._admitted = [PodName("alice"), PodName("bob"), PodName("carol")]
    await http.post(
        "/proposals",
        json={
            "kind": "member",
            "proposer": "alice",
            "strategy": "majority",
            "payload": {"pod_name": "dave", "charter_path": "pods/dave/charter.md"},
        },
    )
    r = await http.get("/proposals")
    assert r.status_code == 200
    assert len(r.json()["proposals"]) == 1
