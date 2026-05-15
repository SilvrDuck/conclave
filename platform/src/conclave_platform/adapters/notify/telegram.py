"""Telegram NotifyAdapter — degrades to stdout when token/chat-id absent."""

from __future__ import annotations

import httpx
import structlog

from ..base import AdapterError
from .base import NotifyLevel
from .stdout import StdoutNotify

log = structlog.get_logger(__name__)

_DEFAULT_TIMEOUT = 10.0


class TelegramNotify:
    """If `token` is None, every call falls through to StdoutNotify."""

    def __init__(
        self,
        *,
        token: str | None,
        chat_id: str | None,
        api_base: str = "https://api.telegram.org",
        request_timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._token = token
        self._chat_id = chat_id
        self._fallback = StdoutNotify()
        if token and chat_id:
            self._client: httpx.AsyncClient | None = httpx.AsyncClient(
                base_url=f"{api_base}/bot{token}",
                timeout=request_timeout,
            )
        else:
            self._client = None
            log.info("telegram.fallback_to_stdout", reason="no_token_or_chat_id")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def notify(self, message: str, *, level: NotifyLevel = NotifyLevel.info) -> None:
        if self._client is None:
            await self._fallback.notify(message, level=level)
            return
        prefix = {"info": "·", "action": "!", "alert": "**"}.get(level, "·")
        text = f"{prefix} {message}"
        r = await self._client.post(
            "/sendMessage",
            json={"chat_id": self._chat_id, "text": text},
        )
        if r.status_code != 200:
            raise AdapterError(f"telegram.sendMessage failed: {r.status_code} {r.text}")
