# ============================================================================
# Stage 1: Builder
# ============================================================================

FROM python:3.14-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*


RUN pip install --no-cache-dir uv


COPY pyproject.toml uv.lock ./


RUN uv sync --frozen --no-dev --no-install-project --python-preference only-system


COPY . .


RUN uv sync --frozen --no-dev --python-preference only-system



# ============================================================================
# Runtime
# ============================================================================

FROM python:3.14-slim


WORKDIR /app


RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*


RUN useradd -m -u 1000 appuser


COPY --from=builder /build/.venv /app/.venv


# copy existing embeddings
COPY data /app/data


COPY --chown=appuser:appuser . .


RUN mkdir -p \
    /app/db \
    /app/logs \
    && chown -R appuser:appuser /app


USER appuser


ENV PATH="/app/.venv/bin:$PATH"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app


EXPOSE 8000


RUN chmod +x start.sh


CMD ["./start.sh"]