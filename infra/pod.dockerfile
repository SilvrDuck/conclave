# Conclave pod image — harness + Pi + pi-mcp-adapter, ready to run.
#
# Build:    docker build -f infra/pod.dockerfile -t conclave-pod:0.1 .
# Run:      mount /workspace (the monorepo) and /root/.pi/agent/auth.json (ro).
#           Set POD_NAME, BUS_URL, OBSERVER_URL, BRANCH, CHARTER_PATH env vars.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    NODE_VERSION=20

# git, curl, ca-certs (for HTTPS), and Node 20 from NodeSource.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

# Install Pi 0.74 and the MCP adapter that lets Pi reach our MCP servers.
RUN npm install -g @earendil-works/pi-coding-agent@0.74.0 \
 && pi --version

# Pre-install pi-mcp-adapter into Pi's tool registry so it's available on first
# agent run. Pi reads ~/.pi/agent for config; we keep that mount point free.
ENV HOME=/root
RUN mkdir -p /root/.pi/agent \
 && pi install npm:pi-mcp-adapter@2.6.1 || true

# Bring in the platform source as a wheel and install it.
WORKDIR /opt/conclave
COPY platform/pyproject.toml platform/uv.lock platform/README.md ./platform/
COPY platform/src ./platform/src
RUN pip install ./platform

# The /conclave/ mount is platform-owned and read-only. Placeholders so the
# Pi can read primitives, personae, etc. when the host doesn't override.
RUN mkdir -p /conclave/personae

WORKDIR /workspace
ENTRYPOINT ["conclave-harness"]
