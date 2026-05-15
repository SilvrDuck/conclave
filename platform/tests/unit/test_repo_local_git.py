"""LocalGitRepo against a real temp git repo (git CLI, no network)."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest

from conclave_platform.adapters.repo import LocalGitRepo, RepoAdapter


@pytest.fixture
def repo(tmp_path: Path) -> LocalGitRepo:
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    (tmp_path / "README.md").write_text("seed\n")
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "."],
        check=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        },
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"],
        check=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        },
    )
    return LocalGitRepo(workdir=tmp_path)


async def test_ensure_branch_creates_new(repo: LocalGitRepo) -> None:
    await repo.ensure_branch("feat/x")
    _, stdout, _ = await repo._git("rev-parse", "--abbrev-ref", "HEAD")
    assert stdout.strip() == "feat/x"


async def test_write_file_commits_with_message(repo: LocalGitRepo, tmp_path: Path) -> None:
    await repo.ensure_branch("feat/y")
    commit = await repo.write_file(
        "pods/alice/charter.md",
        "I am alice\n",
        message="alice charter",
        branch="feat/y",
    )
    assert len(commit.sha) == 40
    content = (tmp_path / "pods/alice/charter.md").read_text()
    assert content == "I am alice\n"


async def test_read_file_returns_none_for_missing(repo: LocalGitRepo) -> None:
    assert await repo.read_file("nonexistent.md") is None


async def test_list_files_filters_prefix(repo: LocalGitRepo) -> None:
    await repo.ensure_branch("feat/z")
    await repo.write_file("pods/alice/a.md", "a", message="a", branch="feat/z")
    await repo.write_file("pods/bob/b.md", "b", message="b", branch="feat/z")
    files = await repo.list_files("pods/alice/")
    assert files == ["pods/alice/a.md"]


def test_local_satisfies_protocol(repo: LocalGitRepo) -> None:
    assert isinstance(repo, RepoAdapter)


async def test_concurrent_writes_serialize(repo: LocalGitRepo) -> None:
    await repo.ensure_branch("feat/concurrent")
    # Two concurrent writes to different files on same branch — lock should serialize.
    results = await asyncio.gather(
        repo.write_file("a.md", "1", message="a", branch="feat/concurrent"),
        repo.write_file("b.md", "2", message="b", branch="feat/concurrent"),
    )
    assert all(len(c.sha) == 40 for c in results)
