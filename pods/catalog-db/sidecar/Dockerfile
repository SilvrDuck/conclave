# Adopted-pod sidecar image — agent only. The OSS main container is
# pulled directly by compose; this image is just the agent.

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 \
    OTEL_SERVICE_NAME=conclave-pod-sidecar \
    OTEL_TRACES_EXPORTER=otlp \
    OTEL_METRICS_EXPORTER=none \
    OTEL_LOGS_EXPORTER=none \
    OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

WORKDIR /pod/sidecar
COPY sidecar/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    opentelemetry-bootstrap -a install

COPY sidecar/bootstrap.py .
COPY charter.md /pod/charter.md

CMD ["python", "/pod/sidecar/bootstrap.py"]
