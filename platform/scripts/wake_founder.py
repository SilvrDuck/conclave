#!/usr/bin/env python3
"""Send a goal_updated event to the founder's inbox topic — wakes Pi.

Run while the compose stack is up. Connects directly to NATS at localhost:4222
and publishes a single event to `pod/founder/inbox`. The harness's recv loop
picks it up, delivers to Pi, and the agent reads /conclave/iusiurandum.md +
its charter to figure out what to do next.
"""

from __future__ import annotations

import argparse
import asyncio

import nats

from conclave_platform.core import EventEnvelope, GoalUpdated, PodName
from conclave_platform.core.events import pod_inbox_topic


async def main(pod: str, goal: str, nats_url: str) -> None:
    nc = await nats.connect(nats_url)
    envelope = EventEnvelope(
        event=GoalUpdated(target_pod=PodName(pod), goal=goal),
    )
    topic = pod_inbox_topic(PodName(pod))
    await nc.publish(topic, envelope.model_dump_json().encode("utf-8"))
    await nc.flush()
    await nc.close()
    print(f"published goal_updated on {topic}: {goal!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pod", default="founder")
    ap.add_argument("--nats-url", default="nats://localhost:4222")
    ap.add_argument(
        "goal",
        nargs="?",
        default="Build a tiny TODO API with auth. Use as many pods as the senate deems necessary.",
    )
    args = ap.parse_args()
    asyncio.run(main(args.pod, args.goal, args.nats_url))
