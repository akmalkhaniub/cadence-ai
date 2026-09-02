# Stage 1: Build virtualenv using uv
FROM python:3.12-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Stage 2: Runtime Image
FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app

RUN groupadd -r cadence && useradd -r -g cadence cadence

COPY --from=builder /app/.venv /app/.venv
COPY . /app

ENV PATH="/app/.venv/bin:$PATH"
USER cadence

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
