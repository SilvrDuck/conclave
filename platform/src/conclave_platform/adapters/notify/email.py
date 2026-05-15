"""Email NotifyAdapter — stub for alpha. See `stdout` / `telegram` for wired pairs."""

from __future__ import annotations

from ..base import AdapterNotImplementedError
from .base import NotifyLevel

_MSG = "Email notify not wired in alpha"


class EmailNotify:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addr: str,
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._from_addr = from_addr
        self._to_addr = to_addr

    async def notify(self, message: str, *, level: NotifyLevel = NotifyLevel.info) -> None:
        raise AdapterNotImplementedError(_MSG)
