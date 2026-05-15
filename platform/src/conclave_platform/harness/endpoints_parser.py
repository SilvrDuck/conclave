"""endpoints.md parser. One section per HTTP endpoint; free-form annotation body.

    ## GET /users/{id}
    Returns the user record. 404 when missing.

    ## POST /users
    Create a user; idempotent on email.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^##\s+(?P<method>[A-Z]+)\s+(?P<path>\S+)\s*$")


@dataclass(frozen=True, slots=True)
class EndpointEntry:
    method: str
    path: str
    annotation: str


def parse_endpoints(text: str) -> list[EndpointEntry]:
    out: list[EndpointEntry] = []
    current: EndpointEntry | None = None
    buf: list[str] = []
    for raw in text.splitlines():
        m = _HEADING_RE.match(raw)
        if m:
            if current is not None:
                out.append(_finalize(current, buf))
                buf = []
            current = EndpointEntry(
                method=m.group("method").upper(), path=m.group("path"), annotation=""
            )
        elif current is not None:
            buf.append(raw)
    if current is not None:
        out.append(_finalize(current, buf))
    return out


def _finalize(entry: EndpointEntry, buf: list[str]) -> EndpointEntry:
    body = "\n".join(buf).strip()
    return EndpointEntry(method=entry.method, path=entry.path, annotation=body)


__all__ = ["EndpointEntry", "parse_endpoints"]
