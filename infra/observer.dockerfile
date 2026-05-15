# Conclave observer / senate-ledger / MCP-server image.
# One image, six entry points (conclave-observer, conclave-senate, conclave-mcp-*).

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/conclave
COPY platform/pyproject.toml platform/uv.lock platform/README.md ./platform/
COPY platform/src ./platform/src
RUN pip install ./platform

ENTRYPOINT ["sh", "-c"]
CMD ["conclave-observer"]
