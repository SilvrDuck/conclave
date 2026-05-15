"""Adapter layer — one Protocol per slot, ≥2 implementations each.

Selecting an implementation is the wizard's job; building one at runtime is
the factory's. Importing here drags every backend client into memory, so the
factory does deferred imports.
"""

from .base import AdapterError, AdapterNotImplementedError, Commit, Mount, MountMode
from .bus import BusAdapter, Handler, Subscription
from .ci import CIAdapter, WorkflowConclusion, WorkflowRun
from .cli import CliAdapter, CliSession
from .docs import DocsAdapter
from .log import LogAdapter
from .notify import NotifyAdapter, NotifyLevel
from .repo import RepoAdapter
from .runtime import PodStatus, RuntimeAdapter
from .trace import SpanEvent, TraceAdapter

__all__ = [
    "AdapterError",
    "AdapterNotImplementedError",
    "BusAdapter",
    "CIAdapter",
    "CliAdapter",
    "CliSession",
    "Commit",
    "DocsAdapter",
    "Handler",
    "LogAdapter",
    "Mount",
    "MountMode",
    "NotifyAdapter",
    "NotifyLevel",
    "PodStatus",
    "RepoAdapter",
    "RuntimeAdapter",
    "SpanEvent",
    "Subscription",
    "TraceAdapter",
    "WorkflowConclusion",
    "WorkflowRun",
]
