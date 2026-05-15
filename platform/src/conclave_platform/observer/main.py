"""Uvicorn entry — `uv run conclave-observer`."""

from __future__ import annotations

import os

import structlog
import uvicorn

from .app import create_app

log = structlog.get_logger(__name__)


def main() -> None:
    dsn = os.environ.get(
        "OBSERVER_DSN", "sqlite+aiosqlite:///./observer.db"
    )
    host = os.environ.get("OBSERVER_HOST", "0.0.0.0")  # noqa: S104 — container, bound by compose
    port = int(os.environ.get("OBSERVER_PORT", "8000"))
    log.info("observer.start", dsn=dsn, port=port)
    app = create_app(dsn=dsn)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
