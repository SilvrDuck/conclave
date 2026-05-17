"""Pod spawner — renders pods/_template into a concrete pod dir and
brings it up via docker compose.

Triggered by the SpawnFirstPod policy (spec/02 Phase 1 last row):

    on ProclamationIssued AND count(non-exiled pods) == 0
        → SpawnPod(role='tbd', image_strategy='code')

The platform owns the spawn; the proclamation gives it a reason.
"""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
import shutil
from pathlib import Path
from string import Template

log = logging.getLogger("mcp-pods.spawner")

TEMPLATE_DIR = Path("/workspace/pods/_template")
PODS_DIR = Path("/workspace/pods")
COMPOSE_FILE = "infra/compose.yaml"
COMPOSE_UP_TIMEOUT_S = 180
TEMPLATE_IMAGE_TAG = "conclave/pod-template:latest"
TEMPLATE_BUILD_TIMEOUT_S = 600


class SpawnError(RuntimeError):
    pass


def mint_pod_id() -> str:
    return f"pod-{secrets.token_hex(6)}"


def _host_env() -> dict[str, str]:
    """Read host paths plumbed in by kickstart.sh via compose env."""
    missing = [
        k
        for k in ("HOST_PROJECT_DIR", "HOST_CLAUDE_CREDENTIALS", "HOST_CLAUDE_VERSIONS")
        if not os.environ.get(k)
    ]
    if missing:
        raise SpawnError(
            f"missing host-path env: {missing} — kickstart.sh did not export them"
        )
    return {
        "HOST_PROJECT_DIR": os.environ["HOST_PROJECT_DIR"],
        "HOST_CLAUDE_CREDENTIALS": os.environ["HOST_CLAUDE_CREDENTIALS"],
        "HOST_CLAUDE_VERSIONS": os.environ["HOST_CLAUDE_VERSIONS"],
    }


def _chown_to_host(path: Path) -> None:
    """Recursively chown `path` to HOST_UID:HOST_GID. mcp-pods runs as
    root inside its container, so without this every rendered file is
    owned by root on the host and `rm -rf` from the loop fails.

    Note: this only chowns the rendered shell (template files + compose
    snippet). The pod container itself runs as root and writes to
    `workspace/` + `charter.md` at runtime — those files end up
    root-owned again. The canonical workaround is nuke.sh's docker
    fallback. Running the pod as host UID is the principled fix (filed
    as a backlog task)."""
    raw_uid = os.environ.get("HOST_UID")
    raw_gid = os.environ.get("HOST_GID")
    if raw_uid is None or raw_gid is None:
        log.warning("HOST_UID/HOST_GID not set; skipping chown of %s", path)
        return
    try:
        uid = int(raw_uid)
        gid = int(raw_gid)
    except ValueError:
        log.warning(
            "HOST_UID=%r HOST_GID=%r not integers; skipping chown of %s",
            raw_uid,
            raw_gid,
            path,
        )
        return
    if uid == 0 and gid == 0:
        # Defaults to 0/0 when compose's `${HOST_UID:-0}` fallback fires
        # because kickstart didn't export them. The legitimate case is a
        # genuine root host user, which is rare. Warn instead of silently
        # rendering a root-owned tree.
        log.warning(
            "HOST_UID and HOST_GID are both 0 — kickstart may not have "
            "exported them. Rendering %s without chown; nuke.sh's docker "
            "fallback will handle removal.",
            path,
        )
        return
    # follow_symlinks=False so a hostile/buggy template can't ever redirect
    # the chown out of the tree.
    os.chown(path, uid, gid, follow_symlinks=False)
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            os.chown(
                os.path.join(root, name), uid, gid, follow_symlinks=False
            )


def render_pod_dir(pod_id: str, display_role: str) -> Path:
    """Copy pods/_template -> pods/<pod_id>/ and render the compose
    snippet. Idempotent: returns the existing dir if it's already there.
    """
    pod_dir = PODS_DIR / pod_id
    if pod_dir.exists():
        log.info("pod dir %s already present; reusing", pod_dir)
    else:
        shutil.copytree(TEMPLATE_DIR, pod_dir)
        log.info("rendered pod dir %s from _template", pod_dir)

    tmpl_path = pod_dir / "pod.compose.yaml.tmpl"
    out_path = pod_dir / "pod.compose.yaml"
    if not tmpl_path.exists():
        raise SpawnError(f"missing template at {tmpl_path}")

    host = _host_env()
    rendered = Template(tmpl_path.read_text()).safe_substitute(
        POD_ID=pod_id,
        DISPLAY_ROLE=display_role,
        **host,
        CLAUDE_MODEL=os.environ.get("CLAUDE_MODEL", "haiku"),
        CLAUDE_EFFORT=os.environ.get("CLAUDE_EFFORT", "low"),
    )
    out_path.write_text(rendered)
    log.info("rendered %s", out_path)
    _chown_to_host(pod_dir)
    return pod_dir


async def compose_up(pod_id: str) -> None:
    """Run `docker compose -f infra/compose.yaml -f pods/<id>/pod.compose.yaml
    --profile pod-<id> up -d` from $HOST_PROJECT_DIR (mcp-pods's
    /workspace mount, which the daemon sees as the host project root).

    The pod service is image-based (uses the prebuilt
    conclave/pod-template), so no --build flag is needed."""
    pod_compose = f"pods/{pod_id}/pod.compose.yaml"
    cmd = [
        "docker",
        "compose",
        "-f",
        COMPOSE_FILE,
        "-f",
        pod_compose,
        "--profile",
        f"pod-{pod_id}",
        "up",
        "-d",
    ]
    log.info("compose up: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd="/workspace",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=COMPOSE_UP_TIMEOUT_S
        )
    except TimeoutError as e:
        proc.kill()
        await proc.wait()
        raise SpawnError(f"compose up timed out after {COMPOSE_UP_TIMEOUT_S}s") from e
    if proc.returncode != 0:
        raise SpawnError(
            f"compose up failed rc={proc.returncode}\n"
            f"stdout: {stdout.decode(errors='replace')}\n"
            f"stderr: {stderr.decode(errors='replace')}"
        )
    log.info("compose up ok for %s", pod_id)


async def build_template_image() -> None:
    """Pre-build the pod-template image so spawn doesn't pay the build
    cost on the §2 critical path. Idempotent: docker's layer cache makes
    repeat builds fast."""
    cmd = [
        "docker",
        "build",
        "-t",
        TEMPLATE_IMAGE_TAG,
        str(TEMPLATE_DIR),
    ]
    log.info("building template image: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=TEMPLATE_BUILD_TIMEOUT_S
        )
    except TimeoutError as e:
        proc.kill()
        await proc.wait()
        raise SpawnError(
            f"template build timed out after {TEMPLATE_BUILD_TIMEOUT_S}s"
        ) from e
    if proc.returncode != 0:
        raise SpawnError(
            f"template build failed rc={proc.returncode}\n"
            f"stderr: {stderr.decode(errors='replace')[-2000:]}"
        )
    log.info("template image built: %s", TEMPLATE_IMAGE_TAG)


async def template_image_present() -> bool:
    """Return True if conclave/pod-template:latest exists locally."""
    proc = await asyncio.create_subprocess_exec(
        "docker",
        "image",
        "inspect",
        TEMPLATE_IMAGE_TAG,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    rc = await proc.wait()
    return rc == 0


async def spawn_pod(pod_id: str, display_role: str) -> None:
    """Render the pod dir and bring it up. Caller is responsible for
    having claimed the pod_id row in pods.pods first.

    Ensures the template image exists before invoking compose; if a
    previous build failed during lifespan, retry it here so the spawn
    still completes (slower, but correct)."""
    if not await template_image_present():
        log.warning("template image missing; building inline on spawn path")
        await build_template_image()
    await asyncio.to_thread(render_pod_dir, pod_id, display_role)
    await compose_up(pod_id)
