"""coms MCP — conversation primitives. Backed by BusAdapter + observer ingest."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog
from fastmcp import FastMCP

from ...adapters import BusAdapter
from ...core import (
    Chatroom,
    CouncilInvited,
    DirectMessage,
    EventEnvelope,
    MessageReceived,
    PodName,
    utc_now,
)
from ...core.events import pod_inbox_topic
from ...core.ids import ChatroomId, CouncilId
from .._common import new_chatroom_id, new_council_id, new_message_id

log = structlog.get_logger(__name__)


@dataclass
class ComsDeps:
    bus: BusAdapter
    observer: httpx.AsyncClient  # used to POST /ingest/chatroom


def build_mcp(deps: ComsDeps) -> FastMCP:
    mcp: FastMCP = FastMCP(name="conclave-coms", version="0.1.0")

    @mcp.tool
    async def open_chatroom(
        participants: list[str],
        topic: str,
        opened_by: str,
    ) -> dict[str, str | list[str]]:
        """Open a chatroom with the named participants. Returns {chatroom_id, topic}."""
        room_id = new_chatroom_id()
        now = utc_now()
        await deps.observer.post(
            "/ingest/chatroom",
            json={
                "chatroom_id": room_id,
                "topic": topic,
                "participants": participants,
                "opened_by": opened_by,
                "opened_at": now.isoformat(),
                "last_active": now.isoformat(),
            },
        )
        # Notify participants
        for p in participants:
            await deps.bus.publish(pod_inbox_topic(PodName(p)), b'{"event":"chatroom_opened"}')
        return {"chatroom_id": room_id, "topic": topic, "participants": participants}

    @mcp.tool
    async def send(
        chatroom_id: str,
        message: str,
        from_pod: str,
    ) -> dict[str, str]:
        """Send a message to a chatroom; every participant gets it on their inbox."""
        msg_id = new_message_id()
        envelope = EventEnvelope(
            event=MessageReceived(
                chatroom_id=ChatroomId(chatroom_id),
                message_id=msg_id,
                from_pod=PodName(from_pod),
                body=message,
            )
        )
        # Publish on the chatroom topic (subscribers = participants' harnesses)
        await deps.bus.publish(f"chatroom/{chatroom_id}", envelope.model_dump_json().encode())
        return {"chatroom_id": chatroom_id, "message_id": msg_id, "ok": "true"}

    @mcp.tool
    async def direct_message(
        peer: str,
        message: str,
        from_pod: str,
    ) -> dict[str, str]:
        """Send a direct message to a single peer."""
        msg_id = new_message_id()
        envelope = EventEnvelope(
            event=DirectMessage(
                target_pod=PodName(peer),
                message_id=msg_id,
                from_pod=PodName(from_pod),
                body=message,
            )
        )
        await deps.bus.publish(pod_inbox_topic(PodName(peer)), envelope.model_dump_json().encode())
        return {"to": peer, "message_id": msg_id, "ok": "true"}

    @mcp.tool
    async def convene_council(
        participants: list[str],
        topic: str,
        convened_by: str,
    ) -> dict[str, str | list[str]]:
        """Convene a council — a time-bounded chatroom that produces a summary."""
        council_id = new_council_id()
        envelope = EventEnvelope(
            event=CouncilInvited(
                council_id=CouncilId(council_id),
                topic=topic,
                convened_by=PodName(convened_by),
            )
        )
        for p in participants:
            targeted = EventEnvelope(
                event=CouncilInvited(
                    target_pod=PodName(p),
                    council_id=CouncilId(council_id),
                    topic=topic,
                    convened_by=PodName(convened_by),
                )
            )
            await deps.bus.publish(
                pod_inbox_topic(PodName(p)), targeted.model_dump_json().encode()
            )
        await deps.bus.publish(
            f"council/{council_id}/announce", envelope.model_dump_json().encode()
        )
        return {"council_id": council_id, "topic": topic, "participants": participants}

    @mcp.tool
    async def close(room_or_council_id: str, summary: str = "") -> dict[str, str]:
        """Close a chatroom or council, optionally recording a summary."""
        await deps.bus.publish(
            f"chatroom/{room_or_council_id}/closed",
            f'{{"summary": "{summary}"}}'.encode(),
        )
        return {"id": room_or_council_id, "ok": "true"}

    @mcp.tool
    async def subscribe_to_item(pod_name: str, item_id: str) -> dict[str, str]:
        """Subscribe this caller to an agenda item's completion. Returns subscription_id."""
        # The harness routes item_completed events. We just record the subscription
        # by publishing intent; the harness consumes it.
        sub_id = f"sub-{pod_name}-{item_id}"
        await deps.bus.publish(
            f"subscriptions/{pod_name}/{item_id}",
            f'{{"subscriber": "{pod_name}"}}'.encode(),
        )
        return {"subscription_id": sub_id}

    @mcp.tool
    async def chatroom_info(chatroom_id: str) -> Chatroom | dict[str, str]:
        """Look up a chatroom's current state from the observer."""
        # Convenience tool — not in the spec's strict signature list but useful for agents.
        r = await deps.observer.get("/state/chatrooms")
        for c in r.json().get("chatrooms", []):
            if c["id"] == chatroom_id:
                return Chatroom(**c)
        return {"error": f"unknown chatroom {chatroom_id}"}

    return mcp


__all__ = ["ComsDeps", "build_mcp"]
