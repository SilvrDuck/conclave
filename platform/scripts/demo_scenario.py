#!/usr/bin/env python3
"""Demo driver — walks the canonical senate flow against a running stack.

Run after `docker compose -f infra/compose.yaml up -d` to populate the system
with members, endpoints, calls, proposals, ballots, and ADRs. Then open
http://localhost:5173 to see the Forum UI light up.

Stages:
  1. Founder bootstrap (N=1 trivial pass)
  2. Founder proposes alice (auto-passes; only founder is admitted)
  3. Observer learns about alice's endpoints
  4. Carol joins, calls alice's endpoint
  5. Alice proposes a contract change (consensus_omnium)
  6. Alice + carol cast yes → ADR written
  7. Founder proposes diana (now N=3 admitted, no auto-pass)
  8. Show how the proposal is left open for ballots
"""

from __future__ import annotations

import asyncio
import sys

import httpx

OBSERVER = "http://localhost:8000"
SENATE = "http://localhost:8001"


async def post(client: httpx.AsyncClient, url: str, **body: object) -> dict[str, object]:
    r = await client.post(url, json=body, timeout=15.0)
    r.raise_for_status()
    data: dict[str, object] = r.json()
    return data


async def get(client: httpx.AsyncClient, url: str, **params: object) -> dict[str, object]:
    r = await client.get(url, params=params, timeout=15.0)
    r.raise_for_status()
    data: dict[str, object] = r.json()
    return data


async def main() -> int:
    async with httpx.AsyncClient() as c:
        print("== 1. Health check ==")
        for u in (f"{OBSERVER}/healthz", f"{SENATE}/healthz"):
            r = await c.get(u, timeout=5.0)
            r.raise_for_status()
        print("observer + senate healthy")

        print("\n== 2. Founder bootstrap ==")
        founder = await post(
            c,
            f"{SENATE}/proposals",
            kind="member",
            proposer="founder",
            strategy="majority",
            payload={"pod_name": "founder", "charter_path": "pods/founder/charter.md"},
            rationale="founder bootstrap",
        )
        p = founder["proposal"]  # type: ignore[index]
        print(f"  proposal={p['id']} outcome={p['outcome']} adr={p['adr_id']}")
        if p["outcome"] != "approved":
            print("  ERROR: founder bootstrap should auto-approve")
            return 1

        print("\n== 3. Founder proposes alice ==")
        alice_prop = await post(
            c,
            f"{SENATE}/proposals",
            kind="member",
            proposer="founder",
            strategy="majority",
            payload={"pod_name": "alice", "charter_path": "pods/alice/charter.md"},
            rationale="need an auth/users pod",
        )
        p = alice_prop["proposal"]  # type: ignore[index]
        print(f"  proposal={p['id']} outcome={p['outcome']} adr={p['adr_id']}")

        print("\n== 4. Alice registers endpoints + agenda ==")
        await post(
            c,
            f"{OBSERVER}/ingest/endpoint",
            pod="alice",
            method="GET",
            path="/users/{id}",
            annotation=None,
        )
        await post(
            c,
            f"{OBSERVER}/ingest/endpoint",
            pod="alice",
            method="POST",
            path="/users",
            annotation=None,
        )
        await post(
            c,
            f"{OBSERVER}/ingest/agenda",
            pod="alice",
            items=[
                {
                    "id": "alice-1",
                    "section": "doing",
                    "text": "wire pagination on GET /users/{id}",
                    "since": None,
                    "eta": "~30min",
                    "updated_at": "2026-05-15T17:30:00Z",
                },
                {
                    "id": "alice-2",
                    "section": "next",
                    "text": "migrate session store to redis",
                    "since": None,
                    "eta": None,
                    "updated_at": "2026-05-15T17:30:00Z",
                },
            ],
        )
        ep = await get(c, f"{OBSERVER}/state/endpoints/alice")
        print(f"  alice endpoints: {[(e['method'], e['path']) for e in ep['endpoints']]}")  # type: ignore[index]

        print("\n== 5. Founder proposes carol — needs alice's yes ==")
        carol_prop = await post(
            c,
            f"{SENATE}/proposals",
            kind="member",
            proposer="founder",
            strategy="majority",
            payload={"pod_name": "carol", "charter_path": "pods/carol/charter.md"},
            rationale="UI consumer of /users",
        )
        cpid = carol_prop["proposal"]["id"]  # type: ignore[index]
        print(f"  proposal={cpid} outcome={carol_prop['proposal']['outcome']} (open)")  # type: ignore[index]
        print("  alice casts yes → admits carol")
        await post(c, f"{SENATE}/proposals/{cpid}/ballots", voter="alice", choice="yes")
        out = await get(c, f"{SENATE}/proposals/{cpid}/outcome")
        print(f"  outcome={out['outcome']} adr={out['adr_id']}")

        # carol → alice GET /users/{id}
        await post(
            c,
            f"{OBSERVER}/ingest/call",
            caller="carol",
            callee="alice",
            method="GET",
            path="/users/{id}",
            rate_per_min=0.2,
        )

        print("\n== 6. Alice proposes contract_change (consensus_omnium) ==")
        cc = await post(
            c,
            f"{SENATE}/proposals",
            kind="contract_change",
            proposer="alice",
            strategy="consensus_omnium",
            payload={
                "endpoints": ["GET /users/{id}"],
                "rationale": "add pagination via ?cursor=",
            },
            rationale="add pagination",
        )
        cp = cc["proposal"]  # type: ignore[index]
        pid = cp["id"]
        print(f"  proposal={pid} affected={cp['affected']} outcome={cp['outcome']}")

        print("\n== 7. Alice + carol cast yes ==")
        for voter in ("alice", "carol"):
            await post(
                c,
                f"{SENATE}/proposals/{pid}/ballots",
                voter=voter,
                choice="yes",
                comment="LGTM, ship it",
            )
        outcome = await get(c, f"{SENATE}/proposals/{pid}/outcome")
        print(f"  outcome={outcome['outcome']} adr={outcome['adr_id']}")

        print("\n== 8. Founder proposes diana — left open for tomorrow's UI demo ==")
        diana = await post(
            c,
            f"{SENATE}/proposals",
            kind="member",
            proposer="founder",
            strategy="majority",
            payload={"pod_name": "diana", "charter_path": "pods/diana/charter.md"},
            rationale="we'll need a worker for batch jobs",
        )
        dp = diana["proposal"]  # type: ignore[index]
        print(f"  proposal={dp['id']} outcome={dp['outcome']} (None = open, needs ballots)")

        print("\n== 9. Snapshot ==")
        members = await get(c, f"{OBSERVER}/state/members")
        print(f"  members: {[m['name'] for m in members['members']]}")  # type: ignore[index]
        adrs = await get(c, f"{SENATE}/adrs")
        print(f"  ADRs: {[a['title'] for a in adrs['adrs']]}")  # type: ignore[index]
        open_props = await get(c, f"{SENATE}/proposals")
        print(f"  open proposals: {[(p['id'], p['kind']) for p in open_props['proposals']]}")  # type: ignore[index]

        print("\nDone. Open http://localhost:5173 to see it in the Forum UI.")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
