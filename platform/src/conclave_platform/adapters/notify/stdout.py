"""Stdout NotifyAdapter — fallback when Telegram isn't configured."""

from __future__ import annotations

import sys

from .base import NotifyLevel


class StdoutNotify:
    async def notify(self, message: str, *, level: NotifyLevel = NotifyLevel.info) -> None:
        sys.stdout.write(f"[notify:{level}] {message}\n")
        sys.stdout.flush()
