"""Process-wide config. Read once at start; never mutated."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    database_url: str
    nats_url: str
    tempo_url: str | None
    bind_host: str
    bind_port: int

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            database_url=os.environ.get(
                "DATABASE_URL",
                "postgres://conclave:conclave@localhost:5432/conclave",
            ),
            nats_url=os.environ.get("NATS_URL", "nats://localhost:4222"),
            tempo_url=os.environ.get("TEMPO_URL"),
            bind_host=os.environ.get("HOST", "0.0.0.0"),
            bind_port=int(os.environ.get("PORT", "8000")),
        )
