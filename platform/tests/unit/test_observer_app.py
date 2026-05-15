"""FastAPI ingest + state endpoints against in-memory SQLite + InMemoryBus."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from conclave_platform.adapters.bus import InMemoryBus
from conclave_platform.observer import create_app


@pytest_asyncio.fixture
async def client_and_bus() -> AsyncIterator[tuple[AsyncClient, InMemoryBus]]:
    bus = InMemoryBus()
    await bus.connect()
    app = create_app(dsn="sqlite+aiosqlite:///:memory:", bus=bus)
    transport = ASGITransport(app=app)
    async with (
        AsyncClient(transport=transport, base_url="http://t") as client,
        app.router.lifespan_context(app),
    ):
        yield client, bus
    await bus.close()


async def test_health(client_and_bus: tuple[AsyncClient, InMemoryBus]) -> None:
    client, _ = client_and_bus
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_new_endpoint_emits_annotation_request(
    client_and_bus: tuple[AsyncClient, InMemoryBus],
) -> None:
    client, bus = client_and_bus
    received: list[bytes] = []

    async def on_msg(payload: bytes) -> None:
        received.append(payload)

    await bus.subscribe("system/observer/annotation_requested", on_msg)
    r = await client.post(
        "/ingest/endpoint",
        json={"pod": "alice", "method": "GET", "path": "/users/{id}"},
    )
    assert r.status_code == 200
    assert r.json()["is_new"] is True
    await asyncio.sleep(0)  # let task drain
    await asyncio.sleep(0)
    assert len(received) == 1
    assert b"annotation_requested" in received[0]
    # Second post with same endpoint: not new, no extra event.
    r = await client.post(
        "/ingest/endpoint",
        json={"pod": "alice", "method": "GET", "path": "/users/{id}", "annotation": "lookup"},
    )
    assert r.json()["is_new"] is False
    await asyncio.sleep(0)
    assert len(received) == 1


async def test_ingest_member_then_list(
    client_and_bus: tuple[AsyncClient, InMemoryBus],
) -> None:
    client, _ = client_and_bus
    r = await client.post(
        "/ingest/member",
        json={
            "name": "alice",
            "charter_path": "pods/alice/charter.md",
            "status": "admitted",
        },
    )
    assert r.status_code == 200
    r = await client.get("/state/members")
    assert r.status_code == 200
    members = r.json()["members"]
    assert [m["name"] for m in members] == ["alice"]


async def test_state_agenda_404_for_unknown_pod(
    client_and_bus: tuple[AsyncClient, InMemoryBus],
) -> None:
    client, _ = client_and_bus
    r = await client.get("/state/agenda/ghost")
    assert r.status_code == 404


async def test_state_agenda_returns_snapshot(
    client_and_bus: tuple[AsyncClient, InMemoryBus],
) -> None:
    client, _ = client_and_bus
    await client.post(
        "/ingest/member",
        json={"name": "alice", "charter_path": "pods/alice/charter.md", "status": "admitted"},
    )
    await client.post(
        "/ingest/agenda",
        json={
            "pod": "alice",
            "items": [
                {
                    "id": "alice-1",
                    "section": "doing",
                    "text": "ship pagination",
                    "updated_at": "2026-05-15T10:00:00Z",
                }
            ],
        },
    )
    r = await client.get("/state/agenda/alice")
    assert r.status_code == 200
    snap = r.json()["snapshot"]
    assert [i["id"] for i in snap["doing"]] == ["alice-1"]


async def test_state_callers_of_endpoint(
    client_and_bus: tuple[AsyncClient, InMemoryBus],
) -> None:
    client, _ = client_and_bus
    await client.post(
        "/ingest/call",
        json={"caller": "alice", "callee": "bob", "method": "GET", "path": "/users/{id}"},
    )
    await client.post(
        "/ingest/call",
        json={"caller": "carol", "callee": "bob", "method": "GET", "path": "/users/{id}"},
    )
    r = await client.get(
        "/state/callers", params={"method": "GET", "path": "/users/{id}"}
    )
    assert r.status_code == 200
    assert set(r.json()["callers"]) == {"alice", "carol"}
