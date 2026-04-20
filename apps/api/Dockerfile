FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir build

COPY packages/titirilquen_core /build/titirilquen_core
RUN cd /build/titirilquen_core && python -m build --wheel --outdir /build/dist

COPY apps/api/pyproject.toml apps/api/README.md /build/api/
COPY apps/api/src /build/api/src
RUN cd /build/api && python -m build --wheel --outdir /build/dist

# ------------------------------------------------------------------

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/dist /tmp/wheels

RUN pip install --no-cache-dir \
    /tmp/wheels/titirilquen_core-*.whl \
    /tmp/wheels/titirilquen_api-*.whl \
    && rm -rf /tmp/wheels

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
