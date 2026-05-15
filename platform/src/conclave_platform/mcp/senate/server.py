"""senate MCP — proposals + ballots. Thin client over the senate ledger."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog
from fastmcp import FastMCP

log = structlog.get_logger(__name__)


@dataclass
class SenateDeps:
    senate: httpx.AsyncClient


def build_mcp(deps: SenateDeps) -> FastMCP:
    mcp: FastMCP = FastMCP(name="conclave-senate", version="0.1.0")

    @mcp.tool
    async def propose_member(
        proposer: str,
        pod_name: str,
        charter_path: str,
        strategy: str = "majority",
        rationale: str = "",
    ) -> dict[str, object]:
        """Propose a new pod. Charter is read from `charter_path` in the monorepo."""
        r = await deps.senate.post(
            "/proposals",
            json={
                "kind": "member",
                "proposer": proposer,
                "strategy": strategy,
                "payload": {"pod_name": pod_name, "charter_path": charter_path},
                "rationale": rationale,
            },
        )
        r.raise_for_status()
        proposal: dict[str, object] = r.json()["proposal"]
        return proposal

    @mcp.tool
    async def propose_exile(
        proposer: str,
        pod_name: str,
        rationale: str,
        strategy: str = "supermajority",
    ) -> dict[str, object]:
        """Propose to exile a member pod."""
        r = await deps.senate.post(
            "/proposals",
            json={
                "kind": "exile",
                "proposer": proposer,
                "strategy": strategy,
                "payload": {"pod_name": pod_name},
                "rationale": rationale,
            },
        )
        r.raise_for_status()
        proposal: dict[str, object] = r.json()["proposal"]
        return proposal

    @mcp.tool
    async def propose_revival(
        proposer: str,
        former_pod_name: str,
        new_charter_path: str,
        strategy: str = "majority",
    ) -> dict[str, object]:
        """Propose to revive an exiled pod under a new charter."""
        r = await deps.senate.post(
            "/proposals",
            json={
                "kind": "revival",
                "proposer": proposer,
                "strategy": strategy,
                "payload": {"pod_name": former_pod_name, "charter_path": new_charter_path},
            },
        )
        r.raise_for_status()
        proposal: dict[str, object] = r.json()["proposal"]
        return proposal

    @mcp.tool
    async def propose_contract_change(
        proposer: str,
        endpoints: list[str],
        rationale: str,
        strategy: str = "consensus_omnium",
    ) -> dict[str, object]:
        """Propose a contract change. endpoints = ['METHOD path', ...]."""
        r = await deps.senate.post(
            "/proposals",
            json={
                "kind": "contract_change",
                "proposer": proposer,
                "strategy": strategy,
                "payload": {"endpoints": endpoints, "rationale": rationale},
                "rationale": rationale,
            },
        )
        r.raise_for_status()
        proposal: dict[str, object] = r.json()["proposal"]
        return proposal

    @mcp.tool
    async def propose_completion(
        proposer: str,
        rationale: str,
        strategy: str = "supermajority",
    ) -> dict[str, object]:
        """Propose that the project is complete."""
        r = await deps.senate.post(
            "/proposals",
            json={
                "kind": "completion",
                "proposer": proposer,
                "strategy": strategy,
                "payload": {"rationale": rationale},
                "rationale": rationale,
            },
        )
        r.raise_for_status()
        proposal: dict[str, object] = r.json()["proposal"]
        return proposal

    @mcp.tool
    async def cast_ballot(
        proposal_id: str,
        voter: str,
        choice: str,  # yes | no | abstain
        comment: str = "",
    ) -> dict[str, object]:
        """Cast a ballot. Choices: yes, no, abstain."""
        r = await deps.senate.post(
            f"/proposals/{proposal_id}/ballots",
            json={"voter": voter, "choice": choice, "comment": comment or None},
        )
        r.raise_for_status()
        proposal: dict[str, object] = r.json()["proposal"]
        return proposal

    @mcp.tool
    async def list_open_proposals() -> list[dict[str, object]]:
        """List proposals that haven't been decided yet."""
        r = await deps.senate.get("/proposals")
        r.raise_for_status()
        return list(r.json().get("proposals", []))

    @mcp.tool
    async def outcome(proposal_id: str) -> dict[str, object]:
        """Get the outcome of a proposal (or `outcome=null` if still open)."""
        r = await deps.senate.get(f"/proposals/{proposal_id}/outcome")
        r.raise_for_status()
        data: dict[str, object] = dict(r.json())
        return data

    return mcp


__all__ = ["SenateDeps", "build_mcp"]
