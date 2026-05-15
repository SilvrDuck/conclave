"""Uvicorn entry — `uv run conclave-senate`."""

from __future__ import annotations

import asyncio
import os

import structlog
import uvicorn

from ..adapters.bus import NatsBus
from ..adapters.docs import GitHubIssuesDocs, InMemoryDocs, SqliteDocs
from .app import create_app
from .observer_client import ObserverClient

log = structlog.get_logger(__name__)


def main() -> None:
    dsn = os.environ.get("SENATE_DSN", "sqlite+aiosqlite:///./senate.db")
    observer_url = os.environ.get("OBSERVER_URL", "http://observer:8000")
    docs_kind = os.environ.get("DOCS_KIND", "inmemory")
    bus_url = os.environ.get("BUS_URL", "nats://bus:4222")
    host = os.environ.get("SENATE_HOST", "0.0.0.0")  # noqa: S104
    port = int(os.environ.get("SENATE_PORT", "8001"))

    observer = ObserverClient(base_url=observer_url)
    docs: object
    if docs_kind == "github_issues":
        token = os.environ["GITHUB_TOKEN"]
        owner, _, repo_ = os.environ["REPO_FULL_NAME"].partition("/")
        docs = GitHubIssuesDocs(owner=owner, repo=repo_, token=token)
    elif docs_kind == "sqlite":
        dsn = os.environ.get("DOCS_DSN", "sqlite+aiosqlite:////data/docs.db")
        docs = SqliteDocs(dsn=dsn)
    else:
        docs = InMemoryDocs()

    bus = NatsBus(servers=bus_url, name="senate-ledger")
    # Connect synchronously before uvicorn takes over — once Pi proposes, we
    # must already be on the wire to publish vote_open / vote_closed.
    asyncio.run(bus.connect())

    log.info(
        "senate.start",
        dsn=dsn,
        observer=observer_url,
        docs=docs_kind,
        bus=bus_url,
        port=port,
    )
    app = create_app(dsn=dsn, observer=observer, docs=docs, bus=bus)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
