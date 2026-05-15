"""Shared adapter primitives — mounts, processes, exceptions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AdapterError(RuntimeError):
    """Base class for adapter-layer errors."""


class AdapterNotImplementedError(AdapterError, NotImplementedError):
    """Raised by stub adapters. Catchable as either AdapterError or NotImplementedError."""


class MountMode(StrEnum):
    ro = "ro"
    rw = "rw"


@dataclass(frozen=True, slots=True)
class Mount:
    host_path: str
    container_path: str
    mode: MountMode = MountMode.rw


@dataclass(frozen=True, slots=True)
class Commit:
    sha: str
    url: str | None = None
