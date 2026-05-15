"""InMemoryBus: pub/sub fan-out and request/reply timeout."""

from __future__ import annotations

import asyncio

import pytest

from conclave_platform.adapters.bus import BusAdapter, InMemoryBus


async def test_publish_subscribe_fan_out() -> None:
    bus = InMemoryBus()
    await bus.connect()
    seen_a: list[bytes] = []
    seen_b: list[bytes] = []
    await bus.subscribe("topic.x", seen_a.append.__call__ if False else _appender(seen_a))
    await bus.subscribe("topic.x", _appender(seen_b))

    await bus.publish("topic.x", b"hello")
    await asyncio.sleep(0)  # let tasks drain
    await asyncio.sleep(0)
    assert seen_a == [b"hello"]
    assert seen_b == [b"hello"]
    await bus.close()


async def test_subscribe_for_other_topic_does_not_fire() -> None:
    bus = InMemoryBus()
    await bus.connect()
    seen: list[bytes] = []
    await bus.subscribe("topic.x", _appender(seen))
    await bus.publish("topic.y", b"miss")
    await asyncio.sleep(0)
    assert seen == []
    await bus.close()


async def test_request_with_no_responder_times_out() -> None:
    bus = InMemoryBus()
    await bus.connect()
    with pytest.raises(TimeoutError):
        await bus.request("topic.rpc", b"q", timeout=0.05)
    await bus.close()


async def test_request_responder_round_trip() -> None:
    bus = InMemoryBus()
    await bus.connect()

    async def echo(payload: bytes) -> bytes:
        return b"echo:" + payload

    bus.register_responder("topic.rpc", echo)
    resp = await bus.request("topic.rpc", b"hi", timeout=1.0)
    assert resp == b"echo:hi"
    await bus.close()


async def test_unsubscribe_stops_delivery() -> None:
    bus = InMemoryBus()
    await bus.connect()
    seen: list[bytes] = []
    sub = await bus.subscribe("t", _appender(seen))
    await bus.publish("t", b"1")
    await asyncio.sleep(0)
    await sub.unsubscribe()
    await bus.publish("t", b"2")
    await asyncio.sleep(0)
    assert seen == [b"1"]
    await bus.close()


def test_inmemory_satisfies_protocol() -> None:
    assert isinstance(InMemoryBus(), BusAdapter)


def _appender(target: list[bytes]):
    async def _h(payload: bytes) -> None:
        target.append(payload)

    return _h
