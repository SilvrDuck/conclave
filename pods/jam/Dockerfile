# Multi-stage: agent + workspace deps + a thin runtime layer.
# Build with: docker build -t conclave/pod-<id> pods/<id>/
#
# At runtime the container reads:
#   POD_ID                 stable id (also docker-compose service name)
#   DISPLAY_ROLE           initial role (the agent renames itself once
#                          its mandate is clear)
#   MCP_PODS_URL           default http://mcp-pods:8000/mcp
#   OTEL_EXPORTER_OTLP_ENDPOINT  default http://otel-collector:4318
#   ENABLE_AGENT           "true" to start the Claude Code agent loop
#
# Workspace listens on :8000. Traefik routes <role>.conclave.local → here.

FROM python:3.12-slim-bookworm AS deps
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /pod
COPY agent/requirements.txt /pod/agent-requirements.txt
COPY workspace/requirements.txt /pod/workspace-requirements.txt
RUN pip install -r /pod/agent-requirements.txt -r /pod/workspace-requirements.txt && \
    opentelemetry-bootstrap -a install

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 \
    WORKSPACE_DIR=/pod/workspace \
    OTEL_SERVICE_NAME=conclave-pod \
    OTEL_TRACES_EXPORTER=otlp \
    OTEL_METRICS_EXPORTER=none \
    OTEL_LOGS_EXPORTER=none \
    OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

# Bring the pre-built site-packages from the deps stage.
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

WORKDIR /pod
COPY charter.md /pod/charter.md
COPY agent /pod/agent
COPY workspace /pod/workspace

EXPOSE 8000
CMD ["python", "/pod/agent/bootstrap.py"]
