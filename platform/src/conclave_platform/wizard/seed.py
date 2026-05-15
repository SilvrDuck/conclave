"""Seed a founder pod skeleton under pods/<founder>/."""

from __future__ import annotations

from pathlib import Path

_CHARTER_TEMPLATE = """\
# Founder pod: {founder}

You are the founder of this Conclave. Your mandate is:

> {mandate}

You own exactly one microservice — the one living in `pods/{founder}/workspace/`.
You are its designer, its developer, its on-call, the steward of its contract.

You may propose peers via `senate.propose_member` when the work requires another
owner. Multi-service work happens through inter-pod coordination (chatrooms,
councils, contract votes), never through agents that span services.

Every decision affecting more than one pod must be the outcome of a vote or a
meeting. Conclave is consensus-driven and orchestrator-free: there is no
supervisor and no router.

## How to coordinate

- Read `/conclave/primitives.md` for the platform primitives (senate, chatroom,
  council, ADR, observed truth).
- Read `/conclave/iusiurandum.md` for the oath every pod takes on admission.
- Read `/conclave/personae/` to discover the archetypes available when you
  draft a new member proposal.

## Working files

- `agenda.md` — your live agenda, sectioned by epoch.
- `endpoints.md` — the contract you advertise to other pods.
- `workspace/` — the microservice you own and ship.

Stay symmetric: bootstrap is a vote, completion is a vote, contract changes are
meetings producing ADRs. No special code paths.
"""


_AGENDA_TEMPLATE = """\
# Agenda — {founder}

## Now

## Next

## Later

## Done
"""


_ENDPOINTS_TEMPLATE = "# Endpoints\n"


_README_TEMPLATE = """\
# {founder}

Pod owned by the founder agent.

- See `charter.md` for the mandate and operating rules.
- See `agenda.md` for the live work plan.
- See `endpoints.md` for the contract this pod advertises.
- The service code lives in `workspace/`.
"""


def seed_founder(*, project_root: Path, founder_name: str, mandate: str) -> None:
    pod = project_root / "pods" / founder_name
    workspace = pod / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (pod / "charter.md").write_text(
        _CHARTER_TEMPLATE.format(founder=founder_name, mandate=mandate)
    )
    (pod / "agenda.md").write_text(_AGENDA_TEMPLATE.format(founder=founder_name))
    (pod / "endpoints.md").write_text(_ENDPOINTS_TEMPLATE)
    (pod / "README.md").write_text(_README_TEMPLATE.format(founder=founder_name))
    (workspace / ".gitkeep").write_text("")
