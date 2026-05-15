"""Notification adapter — slot 8. Outbound user-facing pings."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable


class NotifyLevel(StrEnum):
    info = "info"
    action = "action"
    alert = "alert"


@runtime_checkable
class NotifyAdapter(Protocol):
    async def notify(self, message: str, *, level: NotifyLevel = NotifyLevel.info) -> None: ...
