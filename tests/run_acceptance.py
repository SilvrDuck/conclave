"""Acceptance driver.

Walks the live platform through enough events to exercise spec/08-v2-
acceptance.md §3–§7 deterministically:
- Opens admission proposals for each demo pod with a *different* voting
  strategy each so §4 sees at least 3 of the 4 strategies fire.
- Renames one pod after admission to demonstrate PodRenamed.
- Convenes a public council "Who owns lyrics?" with 3 participants and
  posts a few messages.
- Sends an Augustus DM to one pod.
- Generates inter-pod HTTP traffic via the web pod so OTel call edges
  show on the Glance graph.

Run against the live stack:
    uv run python tests/run_acceptance.py
"""

from __future__ import annotations

import asyncio
import os

import httpx
from fastmcp.client import Client

OBSERVER = os.environ.get("CONCLAVE_OBSERVER_URL", "http://localhost:8000")
WEB = os.environ.get("CONCLAVE_WEB_URL", "http://localhost:9001")
SENATE = os.environ.get("CONCLAVE_SENATE_MCP_URL", "http://localhost:8101/mcp")
COMS = os.environ.get("CONCLAVE_COMS_MCP_URL", "http://localhost:8102/mcp")
PODS = os.environ.get("CONCLAVE_PODS_MCP_URL", "http://localhost:8105/mcp")


# (proposer, candidate, strategy) — picked so each fires its own
# distinguishing dynamics on the senate band.
ADMISSIONS = [
    ("web", "web", "consensus_omnium"),
    ("catalog", "catalog", "majority"),
    ("lyrics", "lyrics", "supermajority"),
    ("jam", "jam", "sortition"),
    ("catalog-db", "catalog-db", "majority"),
]


async def admit_all() -> None:
    async with Client(SENATE, timeout=15.0) as c:
        for proposer, candidate, strategy in ADMISSIONS:
            r = await c.call_tool(
                "propose_admission",
                {
                    "proposer": proposer,
                    "candidate_pod_id": candidate,
                    "candidate_charter": f"{candidate} pod charter (acceptance run)",
                    "eligible_voters": [proposer],  # N=1: proposer auto-cast YES → trivial pass
                    "strategy": strategy,
                },
            )
            print(f"admit {candidate:14s} via {strategy:18s} → {r.data}")


async def rename_one() -> None:
    """Spec §3: 'first pod renames itself' — exercise PodRenamed."""
    async with Client(PODS, timeout=10.0) as c:
        r = await c.call_tool("rename_self", {"pod_id": "web", "new_display_role": "music-ui"})
        print("rename web → music-ui:", r.data)


async def convene_council() -> None:
    """Public council 'Who owns lyrics?' between web/catalog/lyrics."""
    async with Client(COMS, timeout=10.0) as c:
        r = await c.call_tool(
            "convene_council",
            {
                "topic": "Who owns lyrics?",
                "participants": ["web", "catalog", "lyrics"],
                "private": False,
            },
        )
        cid = r.data["council_id"]
        print(f"council opened: {cid}")
        for sender, body in [
            ("web", "We need to scroll lyrics in sync with playback."),
            ("catalog", "Lyrics are not catalog's concern — different aggregate."),
            ("lyrics", "Agreed; I'll own lyrics + provide /lyrics/{track_id}/at."),
        ]:
            await c.call_tool("post_message",
                              {"council_id": cid, "from_pod": sender, "body": body})
        await c.call_tool(
            "close_council",
            {
                "council_id": cid,
                "summary": "Lyrics service owns the lyrics aggregate. Web pulls /lyrics/{track_id}/at on a 500ms tick. Catalog is unchanged.",
            },
        )
        print(f"council closed: {cid}")


async def send_augustus_dm() -> None:
    async with httpx.AsyncClient(timeout=5.0) as c:
        r = await c.post(
            f"{OBSERVER}/commands",
            json={
                "kind": "SendDirectMessage",
                "pod_id": "jam",
                "body": "Make the jam state persistent on restart, please.",
            },
        )
        print(f"DM to jam → {r.status_code}")


async def generate_call_traffic(n: int = 10) -> None:
    """Hit the web pod's proxy endpoints so OTel records cross-pod
    HTTP spans → /state/calls populates → the Glance graph lights up."""
    async with httpx.AsyncClient(timeout=10.0) as c:
        for i in range(n):
            await c.get(f"{WEB}/api/tracks")
            await c.get(f"{WEB}/api/lyrics/t1?t={i * 2}")
            j = (await c.post(f"{WEB}/api/jam",
                              json={"track_id": "t2", "host": f"u{i}"})).json()
            await c.get(f"{WEB}/api/jam/{j['id']}")
        print(f"traffic: {n} rounds of catalog/lyrics/jam calls via web")


async def main() -> None:
    await admit_all()
    await rename_one()
    await convene_council()
    await send_augustus_dm()
    await generate_call_traffic(n=10)
    print("\n=== final state ===")
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{OBSERVER}/state/pods")
        admitted = [p for p in r.json() if p["admitted"]]
        print(f"admitted pods: {len(admitted)} — {', '.join(p['display_role'] for p in admitted)}")
        r = await c.get(f"{OBSERVER}/state/proposals")
        props = r.json()
        outs = {}
        strats = set()
        for p in props:
            outs[p["outcome"]] = outs.get(p["outcome"], 0) + 1
            strats.add(p["strategy"])
        print(f"proposals total={len(props)} outcomes={outs} strategies={sorted(strats)}")
        r = await c.get(f"{OBSERVER}/state/decisions")
        decs = r.json()
        sealed = [d for d in decs if d["status"] == "sealed"]
        print(f"decisions: {len(decs)} ({len(sealed)} sealed)")
        r = await c.get(f"{OBSERVER}/state/councils")
        cs = r.json()
        print(f"councils: {len(cs)} ({sum(1 for c in cs if c['status'] == 'closed')} closed)")
        r = await c.get(f"{OBSERVER}/state/calls?since_seconds=600")
        calls = r.json()
        pairs = {(c["src_pod"], c["dst_pod"]) for c in calls}
        print(f"calls in last 10 min: {len(calls)}; unique edges: {sorted(pairs)}")


if __name__ == "__main__":
    asyncio.run(main())
