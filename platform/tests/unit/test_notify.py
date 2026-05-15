"""Notify adapters: stdout always works, telegram falls back without token."""

from __future__ import annotations

import httpx
import pytest
import respx

from conclave_platform.adapters.notify import (
    NotifyAdapter,
    NotifyLevel,
    StdoutNotify,
    TelegramNotify,
)


async def test_stdout_writes_message(capsys: pytest.CaptureFixture[str]) -> None:
    n = StdoutNotify()
    await n.notify("hello")
    captured = capsys.readouterr()
    assert "hello" in captured.out


async def test_telegram_falls_back_without_token(capsys: pytest.CaptureFixture[str]) -> None:
    n = TelegramNotify(token=None, chat_id="123")
    await n.notify("ping")
    assert "ping" in capsys.readouterr().out


@respx.mock
async def test_telegram_calls_send_message() -> None:
    route = respx.post("https://api.telegram.org/botT/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    n = TelegramNotify(token="T", chat_id="123")
    await n.notify("hi", level=NotifyLevel.action)
    assert route.called
    payload = route.calls.last.request.read()
    assert b"hi" in payload
    assert b"!" in payload  # action level prefix
    await n.close()


def test_satisfies_protocol() -> None:
    assert isinstance(StdoutNotify(), NotifyAdapter)
    assert isinstance(TelegramNotify(token=None, chat_id=None), NotifyAdapter)
