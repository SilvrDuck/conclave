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
COPY system_preamble.md /pod/system_preamble.md
COPY agent /pod/agent
COPY workspace /pod/workspace

# Claude CLI refuses --dangerously-skip-permissions when running as
# root (security check, pass-3 G18). Create a non-root user and chown
# everything the agent and workspace need to read/write. UID 1000
# matches the host user in the typical dev setup.
#
# /home/pod/.claude must exist and be writable by `pod` BEFORE the
# compose mount lands the credential file inside it. Docker would
# otherwise auto-create the parent dir as root, leaving Claude CLI
# unable to write session state for --resume. (G22.)
RUN useradd -m -u 1000 -s /bin/bash pod \
    && mkdir -p /home/pod/.claude/projects \
    && chown -R pod:pod /pod /home/pod

# Move the Claude creds mount target from /root/.claude to /home/pod/.claude
# via HOME=/home/pod (compose template binds the file at that path now).
ENV HOME=/home/pod

USER pod

EXPOSE 8000
CMD ["python", "/pod/agent/bootstrap.py"]
