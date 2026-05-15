"""SqliteDocs: round-trip with a tmp-path sqlite file."""

from __future__ import annotations

from pathlib import Path

from conclave_platform.adapters.docs import DocsAdapter, SqliteDocs
from conclave_platform.core import PodName


async def test_write_then_list_with_pod_filter(tmp_path: Path) -> None:
    dsn = f"sqlite+aiosqlite:///{tmp_path / 'docs.db'}"
    docs = SqliteDocs(dsn=dsn)
    a = await docs.write_adr(
        title="First", body="x", affected_pods=[PodName("alice")]
    )
    b = await docs.write_adr(
        title="Second", body="y", affected_pods=[PodName("bob")]
    )
    items = await docs.list()
    titles = [i.title for i in items]
    assert {"First", "Second"} <= set(titles)
    alice = await docs.list(pod=PodName("alice"))
    assert [i.id for i in alice] == [a]
    assert b != a
    await docs.close()


async def test_search_across_title_and_body(tmp_path: Path) -> None:
    docs = SqliteDocs(dsn=f"sqlite+aiosqlite:///{tmp_path / 'docs.db'}")
    await docs.write_adr(title="Adopt FastAPI", body="reasoning", affected_pods=[])
    await docs.write_adr(title="Rate limit", body="leaky bucket", affected_pods=[])
    hits = await docs.search("FastAPI")
    assert [h.title for h in hits] == ["Adopt FastAPI"]
    await docs.close()


def test_sqlite_satisfies_protocol(tmp_path: Path) -> None:
    docs = SqliteDocs(dsn=f"sqlite+aiosqlite:///{tmp_path / 'docs.db'}")
    assert isinstance(docs, DocsAdapter)
