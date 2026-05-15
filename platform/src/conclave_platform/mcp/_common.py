"""Helpers shared by all four MCP servers."""

from __future__ import annotations

import os
import uuid

from ..core import PodName, utc_now
from ..core.ids import ChatroomId, CouncilId, MessageId


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def new_chatroom_id() -> ChatroomId:
    return ChatroomId(new_id("c"))


def new_council_id() -> CouncilId:
    return CouncilId(new_id("k"))


def new_message_id() -> MessageId:
    return MessageId(new_id("m"))


def pod_self() -> PodName:
    """The container's POD_NAME (or 'unknown' if unset — useful for tests)."""
    return PodName(os.environ.get("POD_NAME", "unknown"))


__all__ = ["new_chatroom_id", "new_council_id", "new_id", "new_message_id", "pod_self", "utc_now"]
