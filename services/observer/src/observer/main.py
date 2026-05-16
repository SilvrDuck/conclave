"""FastAPI app entry point + lifecycle wiring."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from conclave_core import Bus
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from observer.api import commands, inbox, ingest, stream
from observer.api import state as state_api
from observer.config import Config
from observer.reactors.block import BlockDetector
from observer.reactors.digester import ActivityDigester
from observer.reactors.health import HealthWatcher
from observer.services.observation import ObservationService
from observer.services.operator import OperatorService
from observer.state import AppState, EventBroadcaster

log = logging.getLogger("observer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config = Config.from_env()
    log.info("connecting to postgres at %s", _redact_url(config.database_url))
    pool = await asyncpg.create_pool(dsn=config.database_url, min_size=2, max_size=10)
    if pool is None:
        raise RuntimeError("asyncpg pool init failed")

    log.info("connecting to NATS at %s", config.nats_url)
    async with Bus.connect(config.nats_url) as bus:
        broadcaster = EventBroadcaster()
        bus_close = asyncio.Event()
        app_state = AppState(
            config=config,
            pool=pool,
            bus=bus,
            event_broadcaster=broadcaster,
            bus_close=bus_close,
        )
        app.state.observer = app_state

        # In-process services
        operator = OperatorService(pool=pool, bus=bus)
        observation = ObservationService(pool=pool, broadcaster=broadcaster)

        # Wire bus subscribers
        await operator.start()
        await observation.start(bus)

        # Reactors
        reactors = [
            HealthWatcher(pool=pool, bus=bus),
            BlockDetector(pool=pool, bus=bus),
            ActivityDigester(pool=pool),
        ]
        for r in reactors:
            await r.start()

        log.info("observer ready")
        try:
            yield
        finally:
            log.info("observer shutting down")
            for r in reactors:
                await r.stop()
            await pool.close()


app = FastAPI(title="conclave-observer", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(commands.router)
app.include_router(state_api.router)
app.include_router(inbox.router)
app.include_router(ingest.router)
app.include_router(stream.router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


def _redact_url(url: str) -> str:
    if "@" not in url:
        return url
    scheme, _, rest = url.partition("://")
    _, _, host = rest.partition("@")
    return f"{scheme}://***@{host}"
