"""InMemoryDocs: CRUD + search + per-pod filter."""

from __future__ import annotations

from conclave_platform.adapters.docs import DocsAdapter, InMemoryDocs
from conclave_platform.core import PodName
from conclave_platform.core.ids import AdrId


async def test_write_read_round_trip() -> None:
    docs = InMemoryDocs()
    adr_id = await docs.write_adr(
        title="Adopt FastAPI",
        body="we go fastapi for ergonomics",
        affected_pods=[PodName("alice"), PodName("bob")],
    )
    adr = await docs.read(adr_id)
    assert adr is not None
    assert adr.title == "Adopt FastAPI"
    assert adr.affected_pods == [PodName("alice"), PodName("bob")]


async def test_search_matches_title_or_body() -> None:
    docs = InMemoryDocs()
    await docs.write_adr(title="Pick datastore", body="use postgres", affected_pods=[])
    await docs.write_adr(title="Rate limit", body="use leaky bucket", affected_pods=[])
    hits = await docs.search("postgres")
    assert len(hits) == 1
    assert hits[0].title == "Pick datastore"


async def test_list_filters_by_pod_and_sorts_recent_first() -> None:
    docs = InMemoryDocs()
    await docs.write_adr(title="First", body="", affected_pods=[PodName("alice")])
    await docs.write_adr(title="Second", body="", affected_pods=[PodName("bob")])
    await docs.write_adr(title="Third", body="", affected_pods=[PodName("alice")])
    items = await docs.list(pod=PodName("alice"))
    assert [a.title for a in items] == ["Third", "First"]


async def test_read_missing_returns_none() -> None:
    docs = InMemoryDocs()
    assert await docs.read(AdrId("adr-9999")) is None


def test_inmemory_satisfies_protocol() -> None:
    assert isinstance(InMemoryDocs(), DocsAdapter)
