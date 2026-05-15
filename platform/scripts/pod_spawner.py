#!/usr/bin/env python3
"""Host-side pod spawner.

Subscribes to NATS for `system/observer/vote_closed` events. When the senate
approves a `kind=member` proposal, fetches the proposal payload from the
senate-ledger, seeds the new pod's skeleton in the project root (if missing),
and launches a fresh `conclave-pod:0.1` container joined to the `conclave`
docker network.

Runs on the host (talks to docker via the local socket); the senate-ledger
container can't launch siblings, so this lives outside the compose graph.

Stop with Ctrl+C.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import signal
import subprocess
from pathlib import Path

import httpx
import nats
import structlog

log = structlog.get_logger(__name__)

DEFAULT_PROJECT_ROOT = Path("/tmp/conclave-demo")  # noqa: S108
POD_IMAGE = "conclave-pod:0.1"
NETWORK = "conclave_conclave"
COMPOSE_PROJECT = "conclave"  # docker compose project name
SENATE_URL = "http://localhost:8001"
NATS_URL = "nats://localhost:4222"
PI_MODEL = "openai-codex/gpt-5.4"


CHARTER_STUB = """# {pod} pod

You are the agent owner of the `{pod}` microservice in this Conclave project.

Your immediate duties:
1. Read `/conclave/iusiurandum.md` and `/conclave/primitives.md`.
2. Read your `pods/{pod}/charter.md` (this file) and `pods/{pod}/agenda.md`.
3. Coordinate with peers via the `coms`, `senate`, `decisions`, and `state`
   MCP servers — never reach across pod boundaries directly.
4. Own the service at `pods/{pod}/workspace/` end-to-end.

The senate has just admitted you. The mandate that produced your admission
should be visible in the ADR record (`decisions_list_adrs`). Read it first.
"""


def seed_pod_skeleton(project_root: Path, pod: str) -> None:
    pod_dir = project_root / "pods" / pod
    if pod_dir.exists():
        log.info("spawner.pod_exists", pod=pod, path=str(pod_dir))
        return
    pod_dir.mkdir(parents=True, exist_ok=True)
    (pod_dir / "workspace").mkdir(exist_ok=True)
    (pod_dir / "workspace" / ".gitkeep").touch()
    (pod_dir / "charter.md").write_text(CHARTER_STUB.format(pod=pod))
    (pod_dir / "agenda.md").write_text("## doing\n\n## next\n\n## blocked-on\n")
    (pod_dir / "endpoints.md").write_text("# Endpoints\n")
    (pod_dir / "README.md").write_text(f"# {pod}\n\nPod owned by the {pod} agent.\n")
    log.info("spawner.pod_seeded", pod=pod, path=str(pod_dir))


def container_running(name: str) -> bool:
    r = subprocess.run(
        ["docker", "ps", "-q", "--filter", f"name=^{name}$"],
        check=False,
        capture_output=True,
        text=True,
    )
    return bool(r.stdout.strip())


def launch_pod_container(
    pod: str,
    project_root: Path,
    pi_creds: Path,
    docs_root: Path,
    mcp_config: Path,
) -> None:
    container = f"conclave-{pod}"
    if container_running(container):
        log.info("spawner.already_running", pod=pod, container=container)
        return

    args = [
        "docker",
        "run",
        "-d",
        "--name",
        container,
        "--network",
        NETWORK,
        "--label",
        f"com.docker.compose.project={COMPOSE_PROJECT}",
        "-e",
        f"POD_NAME={pod}",
        "-e",
        "BUS_URL=nats://bus:4222",
        "-e",
        "OBSERVER_URL=http://observer:8000",
        "-e",
        "WORKSPACE_ROOT=/workspace",
        "-e",
        "BRANCH=main",
        "-e",
        f"CHARTER_PATH=pods/{pod}/charter.md",
        "-e",
        "PI_SESSION_DIR=/tmp/pi-sessions",
        "-e",
        f"PI_MODEL={PI_MODEL}",
        "-e",
        "PI_MCP_CONFIG=/conclave/mcp.json",
        "-e",
        "HOME=/root",
        "-v",
        f"{project_root}:/workspace",
        "-v",
        f"{pi_creds}:/root/.pi/agent/auth.json",
        "-v",
        f"{docs_root / 'personae'}:/conclave/personae:ro",
        "-v",
        f"{docs_root / 'primitives.md'}:/conclave/primitives.md:ro",
        "-v",
        f"{docs_root / 'iusiurandum.md'}:/conclave/iusiurandum.md:ro",
        "-v",
        f"{docs_root / 'voting-strategies.md'}:/conclave/voting-strategies.md:ro",
        "-v",
        f"{mcp_config}:/conclave/mcp.json:ro",
        POD_IMAGE,
    ]
    r = subprocess.run(args, check=False, capture_output=True, text=True)
    if r.returncode != 0:
        log.error("spawner.launch_failed", pod=pod, err=r.stderr[:400])
        return
    log.info("spawner.launched", pod=pod, container=container, cid=r.stdout.strip()[:12])


async def handle_vote_closed(  # noqa: PLR0911
    payload: bytes,
    *,
    project_root: Path,
    pi_creds: Path,
    docs_root: Path,
    mcp_config: Path,
    senate: httpx.AsyncClient,
    skip_pods: set[str],
) -> None:
    try:
        env = json.loads(payload.decode())
    except json.JSONDecodeError:
        log.warning("spawner.bad_payload", payload=payload[:200])
        return
    event = env.get("event", env)
    if event.get("outcome") != "approved":
        return
    proposal_id = event.get("proposal_id")
    if not proposal_id:
        return
    r = await senate.get(f"/proposals/{proposal_id}")
    if r.status_code != 200:
        log.warning("spawner.proposal_lookup_failed", proposal_id=proposal_id, status=r.status_code)
        return
    proposal = r.json().get("proposal", {})
    if proposal.get("kind") != "member":
        return
    pod_name = proposal.get("payload", {}).get("pod_name")
    if not pod_name:
        return
    if pod_name in skip_pods:
        log.info("spawner.skipped", pod=pod_name)
        return
    seed_pod_skeleton(project_root, pod_name)
    launch_pod_container(
        pod_name,
        project_root=project_root,
        pi_creds=pi_creds,
        docs_root=docs_root,
        mcp_config=mcp_config,
    )


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=str(DEFAULT_PROJECT_ROOT))
    ap.add_argument("--pi-creds", default=str(Path.home() / ".pi" / "agent" / "auth.json"))
    ap.add_argument("--docs-root", default=str(DEFAULT_PROJECT_ROOT))
    ap.add_argument(
        "--mcp-config",
        default=str(Path(__file__).resolve().parents[2] / "infra" / "pod-mcp-config.json"),
    )
    ap.add_argument("--nats-url", default=NATS_URL)
    ap.add_argument("--senate-url", default=SENATE_URL)
    ap.add_argument(
        "--skip",
        action="append",
        default=["founder"],
        help="Pod names to ignore (already launched manually).",
    )
    args = ap.parse_args()

    if not shutil.which("docker"):
        raise SystemExit("docker not in PATH; the spawner runs on the host")

    project_root = Path(args.project_root).resolve()
    pi_creds = Path(args.pi_creds).resolve()
    docs_root = Path(args.docs_root).resolve()
    mcp_config = Path(args.mcp_config).resolve()
    skip_pods = set(args.skip)

    log.info(
        "spawner.start",
        nats=args.nats_url,
        senate=args.senate_url,
        project=str(project_root),
        skip=sorted(skip_pods),
    )

    nc = await nats.connect(args.nats_url)
    senate = httpx.AsyncClient(base_url=args.senate_url, timeout=10.0)
    stop = asyncio.Event()

    async def _on_msg(msg: nats.aio.msg.Msg) -> None:
        await handle_vote_closed(
            msg.data,
            project_root=project_root,
            pi_creds=pi_creds,
            docs_root=docs_root,
            mcp_config=mcp_config,
            senate=senate,
            skip_pods=skip_pods,
        )

    await nc.subscribe("system/observer/vote_closed", cb=_on_msg)
    log.info("spawner.subscribed", topic="system/observer/vote_closed")

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()

    await senate.aclose()
    await nc.drain()
    log.info("spawner.stopped")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    asyncio.run(main())
