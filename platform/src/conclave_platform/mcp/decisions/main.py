"""conclave-mcp-decisions — runs the decisions MCP over streamable HTTP."""

from __future__ import annotations

import os

import structlog

from ...adapters.docs import GitHubIssuesDocs, InMemoryDocs, SenateProxyDocs, SqliteDocs
from .server import DecisionsDeps, build_mcp

log = structlog.get_logger(__name__)


def main() -> None:
    kind = os.environ.get("DOCS_KIND", "inmemory")
    port = int(os.environ.get("PORT", "8004"))
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104
    docs: GitHubIssuesDocs | InMemoryDocs | SqliteDocs | SenateProxyDocs
    if kind == "github_issues":
        owner, _, repo = os.environ["REPO_FULL_NAME"].partition("/")
        docs = GitHubIssuesDocs(owner=owner, repo=repo, token=os.environ["GITHUB_TOKEN"])
    elif kind == "sqlite":
        dsn = os.environ.get("DOCS_DSN", "sqlite+aiosqlite:////data/docs.db")
        docs = SqliteDocs(dsn=dsn)
    elif kind == "senate_proxy":
        docs = SenateProxyDocs(senate_url=os.environ.get("SENATE_URL", "http://senate-ledger:8001"))
    else:
        docs = InMemoryDocs()
    deps = DecisionsDeps(docs=docs)
    mcp = build_mcp(deps)
    log.info("mcp-decisions.start", port=port, kind=kind)
    mcp.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    main()
