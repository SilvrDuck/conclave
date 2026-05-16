"""OTel anti-corruption layer.

Translates an OTLP ExportTraceServiceRequest JSON payload into our domain
`Call` and `Endpoint` shapes. Nothing outside this module imports OTel
types or works with raw OTLP fields.

Spec ref: spec/05-ddd-contexts.md §"Anti-corruption layers" §1.

OTLP HTTP/JSON payload shape (truncated):
{
  "resourceSpans": [{
    "resource": {"attributes": [{"key":"service.name","value":{"stringValue":"frontend"}}]},
    "scopeSpans": [{
      "spans": [{
        "name": "GET /healthz",
        "kind": "SPAN_KIND_SERVER",
        "startTimeUnixNano": "...",
        "endTimeUnixNano": "...",
        "attributes": [
          {"key":"http.method","value":{"stringValue":"GET"}},
          {"key":"http.route","value":{"stringValue":"/healthz"}},
          {"key":"http.status_code","value":{"intValue":"200"}},
          {"key":"peer.service","value":{"stringValue":"catalog"}}
        ]
      }]
    }]
  }]
}
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

SPAN_KIND_SERVER = "SPAN_KIND_SERVER"
SPAN_KIND_CLIENT = "SPAN_KIND_CLIENT"
SPAN_KIND_INTERNAL = "SPAN_KIND_INTERNAL"


@dataclass(frozen=True)
class CallSpan:
    src_pod: str
    dst_pod: str
    method: str
    path: str
    status: int | None
    latency_ms: int | None
    observed_at: datetime


@dataclass(frozen=True)
class EndpointSpan:
    pod_id: str
    method: str
    path: str


def translate_traces_request(
    body: dict[str, Any],
) -> tuple[list[CallSpan], list[EndpointSpan]]:
    """Project an OTLP ExportTraceServiceRequest into (calls, endpoints)."""

    calls: list[CallSpan] = []
    endpoints: list[EndpointSpan] = []

    for resource_span in body.get("resourceSpans", []):
        service_name = _resource_attr(resource_span, "service.name")
        for scope_span in resource_span.get("scopeSpans", []):
            for span in scope_span.get("spans", []):
                kind = span.get("kind", SPAN_KIND_INTERNAL)
                attrs = _attrs(span.get("attributes", []))
                method = attrs.get("http.method") or attrs.get("http.request.method")
                # http.route is the templated path; fall back to http.target.
                path = attrs.get("http.route") or attrs.get("url.path") or attrs.get("http.target")

                if kind == SPAN_KIND_SERVER and service_name and method and path:
                    endpoints.append(
                        EndpointSpan(pod_id=service_name, method=str(method), path=str(path))
                    )

                if kind == SPAN_KIND_CLIENT and service_name and method and path:
                    peer = attrs.get("peer.service") or attrs.get("server.address")
                    if not peer:
                        continue
                    status_v = attrs.get("http.status_code") or attrs.get("http.response.status_code")
                    try:
                        status = int(status_v) if status_v is not None else None
                    except (ValueError, TypeError):
                        status = None
                    latency_ms = _latency_ms(span)
                    calls.append(
                        CallSpan(
                            src_pod=service_name,
                            dst_pod=str(peer),
                            method=str(method),
                            path=str(path),
                            status=status,
                            latency_ms=latency_ms,
                            observed_at=_span_end(span),
                        )
                    )

    return calls, endpoints


def _resource_attr(resource_span: dict[str, Any], key: str) -> str | None:
    attrs = _attrs(resource_span.get("resource", {}).get("attributes", []))
    v = attrs.get(key)
    return str(v) if v is not None else None


def _attrs(attr_list: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for attr in attr_list:
        k = attr.get("key")
        v = attr.get("value")
        if k is None or not isinstance(v, dict):
            continue
        # OTLP values are tagged: stringValue / intValue / doubleValue / boolValue
        if "stringValue" in v:
            out[k] = v["stringValue"]
        elif "intValue" in v:
            out[k] = int(v["intValue"])
        elif "doubleValue" in v:
            out[k] = float(v["doubleValue"])
        elif "boolValue" in v:
            out[k] = bool(v["boolValue"])
    return out


def _latency_ms(span: dict[str, Any]) -> int | None:
    start = span.get("startTimeUnixNano")
    end = span.get("endTimeUnixNano")
    if not start or not end:
        return None
    try:
        return max(0, (int(end) - int(start)) // 1_000_000)
    except (TypeError, ValueError):
        return None


def _span_end(span: dict[str, Any]) -> datetime:
    end = span.get("endTimeUnixNano")
    if not end:
        return datetime.now(UTC)
    try:
        return datetime.fromtimestamp(int(end) / 1_000_000_000, tz=UTC)
    except (TypeError, ValueError):
        return datetime.now(UTC)
