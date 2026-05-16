"""FastMCP server: senate. Exposes propose_* and cast_ballot tools.

The Forum-side write path is handled by a parallel bus subscription on
`conclave.commands.senate.CastBallot` so the four-write Forum can ballot
on behalf of Augustus without speaking MCP.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from conclave_core import Bus
from conclave_core import pool as conclave_pool
from conclave_core.models import (
    AUGUSTUS,
    ProposalKind,
    StrategyName,
    VoteChoice,
)
from fastmcp import Context, FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from mcp_senate.deadline import DeadlineCloser
from mcp_senate.service import ProposalArgs, SenateService

log = logging.getLogger("mcp-senate")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL", "postgres://conclave:conclave@localhost:5432/conclave"
    )


def nats_url() -> str:
    return os.environ.get("NATS_URL", "nats://localhost:4222")


@asynccontextmanager
async def lifespan(server: FastMCP):
    # conclave_pool sets up the jsonb codec so dict→jsonb works without an
    # explicit json.dumps at every call site.
    async with conclave_pool(schema="senate", min_size=1, max_size=5) as pool:
        async with Bus.connect(nats_url()) as bus:
            service = SenateService(pool=pool, bus=bus)
            deadline = DeadlineCloser(service=service)
            await deadline.start()

            async def on_cast_ballot_cmd(data: dict[str, Any]) -> None:
                try:
                    await service.cast_ballot(
                        proposal_id=data["proposal_id"],
                        voter=data.get("voter", AUGUSTUS),
                        choice=VoteChoice(data["choice"]),
                        comment=data.get("comment"),
                    )
                except Exception:
                    log.exception("CastBallot cmd handler failed")

            await bus.subscribe(
                "conclave.commands.senate.CastBallot",
                on_cast_ballot_cmd,
                durable="mcp-senate-castballot",
            )

            try:
                yield {"service": service}
            finally:
                await deadline.stop()


mcp = FastMCP(name="conclave-senate", lifespan=lifespan)


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _service(ctx: Any) -> SenateService:
    """Pull the lifespan-yielded SenateService out of the MCP request context."""
    return ctx.request_context.lifespan_context["service"]


# ─── tools ───────────────────────────────────────────────────────────────


@mcp.tool
async def propose_admission(
    proposer: str,
    candidate_pod_id: str,
    candidate_charter: str,
    eligible_voters: list[str],
    strategy: str = "majority",
    ctx: Context | None = None,
) -> dict[str, str]:
    """Open an admission proposal for a new pod.

    `eligible_voters` is the current set of admitted pods (+ optionally Augustus).
    For the bootstrap case where this is the first pod and there are no other
    members, pass `[proposer]` — the N=1 trivial-pass works by way of the
    proposer's auto-cast YES against a consensus_omnium / majority strategy.
    """
    args = ProposalArgs(
        kind=ProposalKind.ADMISSION,
        proposer=proposer,
        strategy=StrategyName(strategy),
        summary=f"Admit pod {candidate_pod_id}",
        payload={"pod_id": candidate_pod_id, "charter": candidate_charter},
        eligible=eligible_voters,
    )
    proposal_id = await _service(ctx).open_proposal(args)
    return {"proposal_id": proposal_id}


@mcp.tool
async def propose_exile(
    proposer: str,
    target_pod_id: str,
    rationale: str,
    eligible_voters: list[str],
    strategy: str = "supermajority",
    ctx: Context | None = None,
) -> dict[str, str]:
    """Open an exile proposal — remove a pod from the senate."""
    args = ProposalArgs(
        kind=ProposalKind.EXILE,
        proposer=proposer,
        strategy=StrategyName(strategy),
        summary=f"Exile pod {target_pod_id}",
        payload={"pod_id": target_pod_id, "rationale": rationale},
        eligible=eligible_voters,
    )
    return {"proposal_id": await _service(ctx).open_proposal(args)}


@mcp.tool
async def propose_image_swap(
    proposer: str,
    pod_id: str,
    old_image: str,
    new_image: str,
    new_mode: str,
    rationale: str,
    eligible_voters: list[str],
    strategy: str = "majority",
    ctx: Context | None = None,
) -> dict[str, str]:
    """Propose swapping a pod's image (e.g. code → adopted postgres:16).

    Spec §5 (acceptance): this is required to land at least once in the
    golden run.
    """
    args = ProposalArgs(
        kind=ProposalKind.IMAGE_SWAP,
        proposer=proposer,
        strategy=StrategyName(strategy),
        summary=f"Image swap for {pod_id}: {old_image} → {new_image}",
        payload={
            "pod_id": pod_id,
            "old_image": old_image,
            "new_image": new_image,
            "new_mode": new_mode,
            "rationale": rationale,
        },
        eligible=eligible_voters,
    )
    return {"proposal_id": await _service(ctx).open_proposal(args)}


@mcp.tool
async def propose_contract_change(
    proposer: str,
    endpoints: list[dict[str, str]],
    rationale: str,
    affected_pods: list[str],
    strategy: str = "consensus_omnium",
    ctx: Context | None = None,
) -> dict[str, str]:
    """Open a contract change proposal — affected pods must converge."""
    args = ProposalArgs(
        kind=ProposalKind.CONTRACT_CHANGE,
        proposer=proposer,
        strategy=StrategyName(strategy),
        summary=f"Contract change: {len(endpoints)} endpoint(s)",
        payload={"endpoints": endpoints, "rationale": rationale},
        eligible=affected_pods,
    )
    return {"proposal_id": await _service(ctx).open_proposal(args)}


@mcp.tool
async def propose_completion(
    proposer: str,
    proclamation_seq: int,
    summary: str,
    eligible_voters: list[str],
    strategy: str = "supermajority",
    ctx: Context | None = None,
) -> dict[str, str]:
    """Propose that a proclamation be marked completed."""
    args = ProposalArgs(
        kind=ProposalKind.COMPLETION,
        proposer=proposer,
        strategy=StrategyName(strategy),
        summary=summary,
        payload={"proclamation_seq": proclamation_seq},
        eligible=eligible_voters,
    )
    return {"proposal_id": await _service(ctx).open_proposal(args)}


@mcp.tool
async def cast_ballot(
    proposal_id: str,
    voter: str,
    choice: str,
    comment: str | None = None,
    ctx: Context | None = None,
) -> dict[str, str]:
    """Cast a ballot (yes / no / abstain) on an open proposal."""
    await _service(ctx).cast_ballot(
        proposal_id=proposal_id,
        voter=voter,
        choice=VoteChoice(choice),
        comment=comment,
    )
    return {"status": "cast"}


@mcp.tool
async def list_open_proposals(ctx: Context | None = None) -> list[dict[str, Any]]:
    """Return every currently-open proposal with its key fields."""
    return await _service(ctx).list_open_proposals()


@mcp.tool
async def outcome(proposal_id: str, ctx: Context | None = None) -> dict[str, Any] | None:
    """Return the outcome (or `open`) for one proposal_id."""
    return await _service(ctx).outcome(proposal_id)


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(transport="http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
