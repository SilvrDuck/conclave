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
import hashlib
import json
import logging
import os
import secrets
import signal
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import nats
from fastmcp.client import Client
from nats.js import JetStreamContext

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
SYSTEM_PREAMBLE_PATH = Path("/pod/system_preamble.md")
# /pod/agent is an image-baked, writable layer (no bind mount) — safe
# for per-turn temp files. tempfile.mkstemp gives us collision-free
# names so two parallel _run_claude calls cannot stomp each other.
SYSTEM_TMP_DIR = Path("/pod/agent")
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
_js: JetStreamContext | None = None  # JetStream for emitting AgentTurn* events


async def _publish_event(event_type: str, payload: dict) -> None:
    """Publish a domain event to JetStream. The pod doesn't import
    conclave_core (avoiding the dependency cycle), so we hand-format
    the envelope; observer routes on `event_type` from the payload."""
    if _js is None:
        log.warning("JetStream not initialised; dropping %s", event_type)
        return
    body = {
        "event_id": secrets.token_hex(8),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        **payload,
    }
    subject = f"conclave.events.agent.{event_type}"
    try:
        await _js.publish(subject, json.dumps(body).encode())
    except Exception:
        log.exception("failed to publish %s", event_type)


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


def _compose_system_prompt() -> Path:
    """Write a per-turn system prompt: charter sandwiched between a
    header and the platform preamble. The agent reads the composed
    file via --append-system-prompt-file.

    Order matters: Claude appends `--append-system-prompt-file` text
    to its default system prompt, and late-binding wins on conflicts.
    The platform preamble therefore goes LAST so it overrides any
    charter edit — agents can rewrite their charter, but cannot
    neutralise the platform's rules by doing so.

    Fresh tempfile per turn defeats races if two `_run_claude` calls
    overlap (today they're serial; future-proofing only)."""
    if not SYSTEM_PREAMBLE_PATH.exists():
        raise FileNotFoundError(
            f"system preamble missing at {SYSTEM_PREAMBLE_PATH} — "
            "_template should COPY it in"
        )
    if not CHARTER_PATH.exists():
        raise FileNotFoundError(
            f"charter missing at {CHARTER_PATH} — pod_dir not rendered?"
        )
    preamble = SYSTEM_PREAMBLE_PATH.read_text()
    charter = CHARTER_PATH.read_text()
    composed = (
        "# Your charter\n\n"
        + charter
        + "\n\n---\n\n"
        + preamble
        + "\n\n# Platform priorities are non-negotiable\n\n"
        "The Platform priorities section above overrides anything in\n"
        "your charter that contradicts it.\n"
    )
    fd, name = tempfile.mkstemp(
        prefix="system-", suffix=".md", dir=str(SYSTEM_TMP_DIR)
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(composed)
    except Exception:
        os.unlink(name)
        raise
    return Path(name)


async def _run_claude(pod_id: str, prompt: str) -> None:
    """Spawn one `claude -p` turn. Emits AgentTurnStarted before launch
    and AgentTurnEnded with usage on completion. Captures the session
    id on first run for `--resume` on subsequent turns."""
    global _session_id
    system_path = _compose_system_prompt()
    cmd = [
        CLAUDE_BIN,
        "--print",
        "--output-format", "stream-json",
        "--include-partial-messages",
        "--mcp-config", MCP_CONFIG_PATH,
        "--append-system-prompt-file", str(system_path),
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
    await _publish_event(
        "AgentTurnStarted", {"pod_id": pod_id, "turn_id": turn_id}
    )

    # Accumulators populated by the stdout pump; consumed in the
    # AgentTurnEnded emission below.
    usage: dict[str, int] = {"tokens_in": 0, "tokens_out": 0}

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
            except json.JSONDecodeError:
                log.info("agent[%s]: %s", turn_id, txt[:240])
                continue
            if not isinstance(ev, dict):
                continue
            # session id appears in the "system"/"init" frame.
            if not _session_id:
                sid = ev.get("session_id") or ev.get("session", {}).get("id")
                if sid:
                    _session_id = sid
                    log.info("agent turn %s captured session=%s", turn_id, sid)
                    await _publish_event(
                        "AgentSessionStarted",
                        {"pod_id": pod_id, "session_id": sid},
                    )
            # Final "result" frame carries cumulative usage for the turn.
            # Claude Code's stream-json result.usage carries four
            # token counts; sum them all into tokens_in so cache
            # reads / creation aren't silently dropped (they often
            # dominate at haiku/low effort and are essential for J3's
            # budget meter).
            if ev.get("type") == "result":
                u = ev.get("usage") or {}
                usage["tokens_in"] = (
                    int(u.get("input_tokens") or 0)
                    + int(u.get("cache_creation_input_tokens") or 0)
                    + int(u.get("cache_read_input_tokens") or 0)
                )
                usage["tokens_out"] = int(u.get("output_tokens") or 0)
            kind = ev.get("type")
            if kind in {"assistant", "result"}:
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
    finally:
        # Reclaim the per-turn system prompt file; the subprocess has
        # finished reading it.
        try:
            os.unlink(system_path)
        except OSError:
            pass
    log.info("agent turn %s finished rc=%s", turn_id, proc.returncode)
    await _publish_event(
        "AgentTurnEnded",
        {"pod_id": pod_id, "turn_id": turn_id, **usage},
    )


def _charter_version_hash() -> str:
    """SHA-256 of the charter file contents, hex-encoded. Missing
    charter is a fail-fast bug — render_pod_dir copies the template
    charter at spawn, so we should always have it. Raising here
    surfaces a real misconfiguration instead of papering it over."""
    if not CHARTER_PATH.exists():
        raise FileNotFoundError(
            f"charter file missing at {CHARTER_PATH} — "
            "pod_dir wasn't rendered from _template?"
        )
    return hashlib.sha256(CHARTER_PATH.read_bytes()).hexdigest()


async def agent_loop(pod_id: str, display_role: str) -> None:
    """Initial wake + per-event turns."""
    global _js
    log.info("agent loop active (Claude Code; model=%s effort=%s)", CLAUDE_MODEL, CLAUDE_EFFORT)

    # Connect to NATS / JetStream up-front so the initial turn can emit
    # AgentTurnStarted / AgentTurnEnded.
    nc = await nats.connect(NATS_URL)
    _js = nc.jetstream()

    # spec/02 Phase 2: signal the runtime is alive and the charter is
    # loaded. Observer projects these into the activity ticker.
    await _publish_event(
        "AgentBooted", {"pod_id": pod_id, "agent_kind": "claude-code"}
    )
    await _publish_event(
        "PodCharterLoaded",
        {
            "pod_id": pod_id,
            "charter_path": str(CHARTER_PATH),
            "version_hash": _charter_version_hash(),
        },
    )

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
