"""Pod agent bootstrap — registers, supervises workspace, runs Claude Code.

Lifecycle:
1. register_self on mcp-pods (via FastMCP HTTP client).
2. Spawn the workspace service under opentelemetry-instrument.
3. If ENABLE_AGENT=true: kick the agent with an initial "you just booted"
   prompt, then subscribe to this pod's NATS inbox and run one Claude
   Code turn per inbound event. Sessions are persisted (Claude's default)
   so each turn resumes the previous one.

The Claude binary + ~/.claude credentials are bind-mounted into the
container from the host (see infra/compose.yaml). No API key plumbing
needed — the subprocess uses the host's existing subscription.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import signal
import sys
from pathlib import Path

import nats
from fastmcp.client import Client

log = logging.getLogger("pod.bootstrap")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


# ── config ─────────────────────────────────────────────────────────────

MCP_PODS_URL = os.environ.get("MCP_PODS_URL", "http://mcp-pods:8000/mcp")
MCP_PODS_TIMEOUT = float(os.environ.get("MCP_PODS_TIMEOUT", "10"))
NATS_URL = os.environ.get("NATS_URL", "nats://nats:4222")
WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/pod/workspace"))
SERVICE_PORT = os.environ.get("SERVICE_PORT", "8000")
ENABLE_AGENT = os.environ.get("ENABLE_AGENT", "false").lower() == "true"
CHARTER_PATH = Path("/pod/charter.md")
MCP_CONFIG_PATH = "/pod/agent/mcp.json"
def _resolve_claude_bin() -> str:
    """Locate the claude binary inside the pod.

    The host's `~/.local/share/claude/versions/` directory is bind-mounted
    at `/opt/claude`. It contains one ELF binary per installed version;
    we pick the lexically newest (versions are dotted semver, which sorts
    correctly for normal monotonic upgrades).
    """
    override = os.environ.get("CLAUDE_BIN")
    if override:
        return override
    versions = Path("/opt/claude")
    if versions.is_dir():
        candidates = sorted(p for p in versions.iterdir() if p.is_file() and os.access(p, os.X_OK))
        if candidates:
            return str(candidates[-1])
    return "/usr/local/bin/claude"


CLAUDE_BIN = _resolve_claude_bin()
CLAUDE_EFFORT = os.environ.get("CLAUDE_EFFORT", "low")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "haiku")
AGENT_TURN_TIMEOUT_S = float(os.environ.get("AGENT_TURN_TIMEOUT_S", "180"))
AGENT_MAX_BUDGET_USD = os.environ.get("AGENT_MAX_BUDGET_USD", "0.50")

SERVICE_ARGV = (
    "opentelemetry-instrument",
    "uvicorn",
    "main:app",
    "--host",
    "0.0.0.0",
    "--port",
    SERVICE_PORT,
)

_current_proc: asyncio.subprocess.Process | None = None
_session_id: str | None = None  # Claude Code session for --resume


# ── register + service supervisor ─────────────────────────────────────


async def register() -> tuple[str, str]:
    pod_id = os.environ.get("POD_ID")
    display_role = os.environ.get("DISPLAY_ROLE", pod_id or "unnamed")
    if not pod_id:
        log.error("POD_ID env var required")
        sys.exit(1)
    async with Client(MCP_PODS_URL, timeout=MCP_PODS_TIMEOUT) as c:
        result = await c.call_tool(
            "register_self",
            {
                "pod_id": pod_id,
                "display_role": display_role,
                "image_strategy": "code",
                "charter_path": str(CHARTER_PATH),
            },
        )
        log.info("registered: %s", result.data)
    return pod_id, display_role


async def run_service() -> None:
    global _current_proc
    if not WORKSPACE_DIR.exists():
        log.error("workspace dir %s missing", WORKSPACE_DIR)
        return
    while True:
        log.info("starting service: %s", " ".join(SERVICE_ARGV))
        _current_proc = await asyncio.create_subprocess_exec(
            *SERVICE_ARGV, cwd=str(WORKSPACE_DIR)
        )
        rc = await _current_proc.wait()
        _current_proc = None
        log.warning("service exited rc=%s; restarting in 2s", rc)
        await asyncio.sleep(2)


async def shutdown_subprocess() -> None:
    global _current_proc
    proc = _current_proc
    if proc is None or proc.returncode is not None:
        return
    log.info("terminating workspace subprocess (pid=%s)", proc.pid)
    try:
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=5)
    except (TimeoutError, ProcessLookupError):
        log.warning("subprocess didn't exit in 5s, killing")
        proc.kill()
        await proc.wait()


# ── agent: one Claude Code turn per inbox event ───────────────────────


def _build_prompt(pod_id: str, display_role: str, event_kind: str, event: dict) -> str:
    """Render the user-facing prompt for one agent turn."""
    return (
        f"You are the agent for pod `{pod_id}` (display_role: `{display_role}`).\n\n"
        f"Your workspace is /pod/workspace. The service entrypoint is `main.py`\n"
        f"served on :{SERVICE_PORT}. Container restart picks up file changes.\n\n"
        f"You have MCP tools across `senate`, `coms`, `decisions`, `state`, `pods`.\n"
        f"Use them to coordinate with peers. Editing the workspace happens via\n"
        f"your normal Write/Edit tools. Be brief; don't re-explain what you did.\n\n"
        f"### Inbox event: {event_kind}\n"
        f"```json\n{json.dumps(event, indent=2)}\n```\n\n"
        f"Take the right action and reply with a one-line summary."
    )


async def _run_claude(pod_id: str, prompt: str) -> None:
    """Spawn one `claude -p` turn. Captures the session id on first run
    for resumability on subsequent ones. Streams stdout into the pod log."""
    global _session_id
    cmd = [
        CLAUDE_BIN,
        "--print",
        "--output-format", "stream-json",
        "--include-partial-messages",
        "--mcp-config", MCP_CONFIG_PATH,
        "--append-system-prompt-file", str(CHARTER_PATH),
        "--dangerously-skip-permissions",
        "--effort", CLAUDE_EFFORT,
        "--model", CLAUDE_MODEL,
        "--max-budget-usd", AGENT_MAX_BUDGET_USD,
        "--add-dir", str(WORKSPACE_DIR),
    ]
    if _session_id:
        cmd += ["--resume", _session_id]
    cmd += [prompt]

    turn_id = secrets.token_hex(6)
    log.info("agent turn %s starting (session=%s)", turn_id, _session_id or "new")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(WORKSPACE_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def pump_stdout() -> None:
        global _session_id
        assert proc.stdout is not None
        async for line in proc.stdout:
            txt = line.decode(errors="replace").rstrip()
            if not txt:
                continue
            # stream-json format: each line is one JSON event.
            try:
                ev = json.loads(txt)
                # session id appears in the "system"/"init" frame
                if not _session_id and isinstance(ev, dict):
                    sid = ev.get("session_id") or ev.get("session", {}).get("id")
                    if sid:
                        _session_id = sid
                        log.info("agent turn %s captured session=%s", turn_id, sid)
                # Forward visible content tersely.
                kind = ev.get("type") if isinstance(ev, dict) else "?"
                if kind in {"assistant", "result"}:
                    log.info("agent[%s]: %s", turn_id, txt[:240])
            except json.JSONDecodeError:
                log.info("agent[%s]: %s", turn_id, txt[:240])

    async def pump_stderr() -> None:
        assert proc.stderr is not None
        async for line in proc.stderr:
            log.warning("agent[%s] err: %s", turn_id, line.decode(errors='replace').rstrip()[:240])

    try:
        await asyncio.wait_for(
            asyncio.gather(pump_stdout(), pump_stderr(), proc.wait()),
            timeout=AGENT_TURN_TIMEOUT_S,
        )
    except TimeoutError:
        log.error("agent turn %s timed out after %ss; killing", turn_id, AGENT_TURN_TIMEOUT_S)
        proc.kill()
        await proc.wait()
        return
    log.info("agent turn %s finished rc=%s", turn_id, proc.returncode)


async def agent_loop(pod_id: str, display_role: str) -> None:
    """Initial wake + per-event turns."""
    log.info("agent loop active (Claude Code; model=%s effort=%s)", CLAUDE_MODEL, CLAUDE_EFFORT)
    initial = (
        f"You are the agent for pod `{pod_id}` (display_role `{display_role}`).\n\n"
        f"You have just booted into a fresh container. Read your charter (already\n"
        f"appended to your system prompt). Then:\n"
        f"  1. Use `state.proclamations` to look for any pending Augustus direction.\n"
        f"  2. Use `state.members` to see who else is around.\n"
        f"  3. If you're not yet admitted, propose your own admission via\n"
        f"     `senate.propose_admission` with strategy 'consensus_omnium' and\n"
        f"     eligible_voters = [your pod_id] for a clean N=1 pass.\n"
        f"  4. Briefly summarise what you did.\n"
        f"Do NOT edit the workspace yet — wait for a real directive.\n"
    )
    try:
        await _run_claude(pod_id, initial)
    except Exception:
        log.exception("initial agent turn failed")

    # Then subscribe to this pod's inbox + Augustus's broadcast and run
    # one turn per event.
    nc = await nats.connect(NATS_URL)
    subjects = [
        f"conclave.inbox.{pod_id}",
        "conclave.events.operator.ProclamationIssued",
        "conclave.events.operator.DirectMessageFromUser",
    ]
    queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()

    async def on_msg(msg: nats.aio.msg.Msg) -> None:
        try:
            data = json.loads(msg.data.decode())
        except Exception:
            log.warning("inbox: undecodable msg on %s", msg.subject)
            return
        # Filter DM events to this pod only.
        if msg.subject.endswith("DirectMessageFromUser") and data.get("pod_id") != pod_id:
            return
        await queue.put((msg.subject, data))

    for s in subjects:
        await nc.subscribe(s, cb=on_msg)
    log.info("agent loop subscribed to %d inbox subjects", len(subjects))

    while True:
        subject, data = await queue.get()
        kind = subject.rsplit(".", 1)[-1]
        try:
            prompt = _build_prompt(pod_id, display_role, kind, data)
            await _run_claude(pod_id, prompt)
        except Exception:
            log.exception("agent turn for %s failed", kind)


# ── main ───────────────────────────────────────────────────────────────


async def main() -> None:
    pod_id, display_role = await register()

    tasks = [asyncio.create_task(run_service(), name="service")]
    if ENABLE_AGENT:
        tasks.append(asyncio.create_task(agent_loop(pod_id, display_role), name="agent"))
    else:
        log.info("agent disabled (ENABLE_AGENT=false); service-only")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    waiter = asyncio.create_task(stop.wait())
    done, _ = await asyncio.wait({*tasks, waiter}, return_when=asyncio.FIRST_COMPLETED)
    await shutdown_subprocess()
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    for t in done:
        if t is waiter:
            log.info("signal received; exiting")
            return
        if (exc := t.exception()):
            log.error("task %s failed: %s", t.get_name(), exc)


if __name__ == "__main__":
    os.environ.setdefault("OTEL_SERVICE_NAME", os.environ.get("POD_ID", "unknown-pod"))
    os.environ.setdefault(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318"),
    )
    asyncio.run(main())
