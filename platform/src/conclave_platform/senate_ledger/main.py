"""Uvicorn entry — `uv run conclave-senate`."""

from __future__ import annotations

import os

import structlog
import uvicorn

from ..adapters.docs import GitHubIssuesDocs, InMemoryDocs
from .app import create_app
from .observer_client import ObserverClient

log = structlog.get_logger(__name__)


def main() -> None:
    dsn = os.environ.get("SENATE_DSN", "sqlite+aiosqlite:///./senate.db")
    observer_url = os.environ.get("OBSERVER_URL", "http://observer:8000")
    docs_kind = os.environ.get("DOCS_KIND", "inmemory")
    host = os.environ.get("SENATE_HOST", "0.0.0.0")  # noqa: S104
    port = int(os.environ.get("SENATE_PORT", "8001"))

    observer = ObserverClient(base_url=observer_url)
    docs: object
    if docs_kind == "github_issues":
        token = os.environ["GITHUB_TOKEN"]
        owner, _, repo_ = os.environ["REPO_FULL_NAME"].partition("/")
        docs = GitHubIssuesDocs(owner=owner, repo=repo_, token=token)
    else:
        docs = InMemoryDocs()
    log.info("senate.start", dsn=dsn, observer=observer_url, docs=docs_kind, port=port)
    app = create_app(dsn=dsn, observer=observer, docs=docs)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
