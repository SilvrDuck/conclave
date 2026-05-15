"""GitHubIssuesDocs: HTTP contract verified with respx."""

from __future__ import annotations

import httpx
import pytest
import respx

from conclave_platform.adapters.docs import DocsAdapter, GitHubIssuesDocs
from conclave_platform.core import PodName
from conclave_platform.core.ids import AdrId


@pytest.fixture
def docs() -> GitHubIssuesDocs:
    return GitHubIssuesDocs(owner="SilvrDuck", repo="conclave-playground", token="ghp_test")


@respx.mock
async def test_write_adr_posts_issue_and_closes(docs: GitHubIssuesDocs) -> None:
    respx.post("https://api.github.com/repos/SilvrDuck/conclave-playground/labels").mock(
        return_value=httpx.Response(201, json={"name": "adr"}),
    )
    create = respx.post(
        "https://api.github.com/repos/SilvrDuck/conclave-playground/issues"
    ).mock(return_value=httpx.Response(201, json={"number": 42}))
    close = respx.patch(
        "https://api.github.com/repos/SilvrDuck/conclave-playground/issues/42"
    ).mock(return_value=httpx.Response(200, json={"number": 42, "state": "closed"}))

    adr_id = await docs.write_adr(
        title="Adopt FastAPI",
        body="reasons",
        affected_pods=[PodName("alice")],
        proposal_id="p-1",
    )
    assert adr_id == "adr-42"
    assert create.called
    assert close.called
    body = create.calls.last.request.read()
    assert b"proposal: p-1" in body
    assert b"pod:alice" in body
    await docs.close()


@respx.mock
async def test_read_returns_none_on_404(docs: GitHubIssuesDocs) -> None:
    respx.get(
        "https://api.github.com/repos/SilvrDuck/conclave-playground/issues/99"
    ).mock(return_value=httpx.Response(404))
    assert await docs.read(AdrId("adr-99")) is None
    await docs.close()


@respx.mock
async def test_read_parses_proposal_id_and_pods(docs: GitHubIssuesDocs) -> None:
    respx.get(
        "https://api.github.com/repos/SilvrDuck/conclave-playground/issues/7"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "number": 7,
                "title": "Change /users",
                "body": "rationale\n\n---\nproposal: p-2",
                "labels": [{"name": "adr"}, {"name": "pod:alice"}, {"name": "pod:bob"}],
                "created_at": "2026-05-15T10:00:00Z",
            },
        )
    )
    adr = await docs.read(AdrId("adr-7"))
    assert adr is not None
    assert adr.title == "Change /users"
    assert adr.affected_pods == [PodName("alice"), PodName("bob")]
    assert adr.proposal_id == "p-2"
    await docs.close()


@respx.mock
async def test_search_passes_query_string(docs: GitHubIssuesDocs) -> None:
    route = respx.get("https://api.github.com/search/issues").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    await docs.search("foo bar")
    assert route.called
    q = route.calls.last.request.url.params["q"]
    assert "label:adr" in q
    assert "foo bar" in q
    await docs.close()


def test_satisfies_protocol(docs: GitHubIssuesDocs) -> None:
    assert isinstance(docs, DocsAdapter)
