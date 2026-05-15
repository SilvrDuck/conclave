"""LocalGitRepo — wraps `git` CLI for in-checkout commits.

Used by the harness to commit endpoints.md / agenda.md / charter.md from
inside the pod container, where /workspace is the bind-mounted monorepo.
Atomic commits, single branch per call, hard timeouts on every shell-out.
"""

from __future__ import annotations

import asyncio
import os
import shlex
from pathlib import Path

import structlog

from ..base import AdapterError, Commit

log = structlog.get_logger(__name__)

_DEFAULT_GIT_TIMEOUT = 30.0


class GitCommandError(AdapterError):
    pass


class LocalGitRepo:
    """`workdir` must be an existing git checkout."""

    def __init__(
        self,
        *,
        workdir: Path,
        author_name: str = "conclave",
        author_email: str = "conclave@local",
        git_timeout: float = _DEFAULT_GIT_TIMEOUT,
    ) -> None:
        self._workdir = workdir
        self._env = {
            "GIT_AUTHOR_NAME": author_name,
            "GIT_AUTHOR_EMAIL": author_email,
            "GIT_COMMITTER_NAME": author_name,
            "GIT_COMMITTER_EMAIL": author_email,
        }
        self._timeout = git_timeout
        self._lock = asyncio.Lock()

    async def _git(self, *args: str, check: bool = True) -> tuple[int, str, str]:
        cmd = ["git", *args]
        log.debug("git.run", cmd=" ".join(shlex.quote(a) for a in cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self._workdir),
            env={**os.environ, **self._env},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout
            )
        except TimeoutError as e:
            proc.kill()
            await proc.wait()
            raise GitCommandError(f"git {' '.join(args)} timed out") from e
        rc = proc.returncode or 0
        stdout = stdout_b.decode("utf-8", errors="replace")
        stderr = stderr_b.decode("utf-8", errors="replace")
        if check and rc != 0:
            raise GitCommandError(f"git {' '.join(args)} failed: {stderr.strip()}")
        return rc, stdout, stderr

    async def ensure_branch(self, branch: str, *, from_ref: str = "main") -> None:
        async with self._lock:
            rc, _, _ = await self._git("rev-parse", "--verify", branch, check=False)
            if rc == 0:
                await self._git("checkout", branch)
                return
            await self._git("checkout", "-b", branch, from_ref)

    async def read_file(self, path: str, *, ref: str = "HEAD") -> str | None:
        async with self._lock:
            rc, stdout, _ = await self._git("show", f"{ref}:{path}", check=False)
            return stdout if rc == 0 else None

    async def write_file(
        self,
        path: str,
        content: str,
        *,
        message: str,
        branch: str,
    ) -> Commit:
        async with self._lock:
            target = self._workdir / path
            target.parent.mkdir(parents=True, exist_ok=True)
            # Skip the write entirely when content is already current — touching
            # the file would update mtime and re-trigger any mtime watcher.
            existing = target.read_text() if target.exists() else None
            if existing != content:
                await self._git("checkout", branch)
                target.write_text(content)
                await self._git("add", path)
                rc, _, _ = await self._git(
                    "diff", "--cached", "--quiet", "--", path, check=False
                )
                if rc != 0:
                    await self._git("commit", "-m", message)
            _, sha, _ = await self._git("rev-parse", "HEAD")
            return Commit(sha=sha.strip())

    async def list_files(self, prefix: str = "", *, ref: str = "HEAD") -> list[str]:
        async with self._lock:
            _, stdout, _ = await self._git("ls-tree", "-r", "--name-only", ref)
            return [f for f in stdout.splitlines() if not prefix or f.startswith(prefix)]

    async def open_pr(
        self,
        *,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> str:
        raise NotImplementedError("LocalGitRepo cannot open PRs; use GitHubRepo or GitLabRepo")
