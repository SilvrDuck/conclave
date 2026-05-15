"""GitHubActionsCI: ensure_workflow writes templated YAML; last_run parses runs."""

from __future__ import annotations

import httpx
import pytest
import respx

from conclave_platform.adapters.base import Commit
from conclave_platform.adapters.ci import CIAdapter, GitHubActionsCI, WorkflowConclusion


class _FakeRepo:
    def __init__(self) -> None:
        self.writes: list[tuple[str, str, str, str]] = []

    async def write_file(
        self, path: str, content: str, *, message: str, branch: str
    ) -> Commit:
        self.writes.append((path, content, message, branch))
        return Commit(sha="0" * 40)


@pytest.fixture
def ci_and_repo() -> tuple[GitHubActionsCI, _FakeRepo]:
    repo = _FakeRepo()
    ci = GitHubActionsCI(
        owner="o", repo="r", token="t", repo_writer=repo
    )
    return ci, repo


async def test_ensure_workflow_writes_template(
    ci_and_repo: tuple[GitHubActionsCI, _FakeRepo],
) -> None:
    ci, repo = ci_and_repo
    await ci.ensure_workflow("alice")
    assert len(repo.writes) == 1
    path, content, message, branch = repo.writes[0]
    assert path == ".github/workflows/alice.yml"
    assert "name: alice-ci" in content
    assert "pods/alice/workspace" in content
    assert branch == "main"
    assert message.startswith("ci:")
    await ci.close()


@respx.mock
async def test_last_run_maps_conclusion(
    ci_and_repo: tuple[GitHubActionsCI, _FakeRepo],
) -> None:
    ci, _ = ci_and_repo
    respx.get(
        "https://api.github.com/repos/o/r/actions/workflows/alice.yml/runs"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "workflow_runs": [
                    {
                        "name": "alice-ci",
                        "conclusion": "success",
                        "html_url": "https://gh/r/runs/1",
                        "run_started_at": "2026-05-15T10:00:00Z",
                    }
                ]
            },
        )
    )
    run = await ci.last_run("alice")
    assert run is not None
    assert run.conclusion == WorkflowConclusion.success
    await ci.close()


@respx.mock
async def test_last_run_returns_none_on_404(
    ci_and_repo: tuple[GitHubActionsCI, _FakeRepo],
) -> None:
    ci, _ = ci_and_repo
    respx.get(
        "https://api.github.com/repos/o/r/actions/workflows/alice.yml/runs"
    ).mock(return_value=httpx.Response(404))
    assert await ci.last_run("alice") is None
    await ci.close()


def test_satisfies_protocol(ci_and_repo: tuple[GitHubActionsCI, _FakeRepo]) -> None:
    ci, _ = ci_and_repo
    assert isinstance(ci, CIAdapter)
