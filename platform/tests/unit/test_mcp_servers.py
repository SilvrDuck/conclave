"""Smoke-build each MCP server; verify the tools are registered with the right names."""

from __future__ import annotations

import httpx
import pytest

from conclave_platform.adapters.bus import InMemoryBus
from conclave_platform.adapters.docs import InMemoryDocs
from conclave_platform.mcp.coms.server import ComsDeps
from conclave_platform.mcp.coms.server import build_mcp as build_coms
from conclave_platform.mcp.decisions.server import (
    DecisionsDeps,
)
from conclave_platform.mcp.decisions.server import (
    build_mcp as build_decisions,
)
from conclave_platform.mcp.senate.server import SenateDeps
from conclave_platform.mcp.senate.server import build_mcp as build_senate
from conclave_platform.mcp.state.server import StateDeps
from conclave_platform.mcp.state.server import build_mcp as build_state


async def _tools(mcp) -> set[str]:
    return {t.name for t in await mcp._list_tools()}


@pytest.mark.asyncio
async def test_coms_tools_present() -> None:
    bus = InMemoryBus()
    await bus.connect()
    mcp = build_coms(ComsDeps(bus=bus, observer=httpx.AsyncClient(base_url="http://x")))
    names = await _tools(mcp)
    assert {
        "open_chatroom",
        "send",
        "direct_message",
        "convene_council",
        "close",
        "subscribe_to_item",
    } <= names
    await bus.close()


@pytest.mark.asyncio
async def test_senate_tools_present() -> None:
    mcp = build_senate(SenateDeps(senate=httpx.AsyncClient(base_url="http://x")))
    names = await _tools(mcp)
    assert {
        "propose_member",
        "propose_exile",
        "propose_revival",
        "propose_contract_change",
        "propose_completion",
        "cast_ballot",
        "list_open_proposals",
        "outcome",
    } <= names


@pytest.mark.asyncio
async def test_decisions_tools_present() -> None:
    mcp = build_decisions(DecisionsDeps(docs=InMemoryDocs()))
    names = await _tools(mcp)
    assert {"write_adr", "read", "search", "list_adrs"} <= names


@pytest.mark.asyncio
async def test_state_tools_present() -> None:
    mcp = build_state(StateDeps(observer=httpx.AsyncClient(base_url="http://x")))
    names = await _tools(mcp)
    assert {
        "members",
        "endpoints",
        "callers_of",
        "chatrooms",
        "agenda",
        "platform_info",
    } <= names
