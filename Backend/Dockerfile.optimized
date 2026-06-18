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


# ===============================
# Build embeddings + HF cache
# ===============================

ENV HF_HOME=/build/.cache/huggingface
ENV TRANSFORMERS_CACHE=/build/.cache/huggingface


RUN mkdir -p /build/data


RUN /build/.venv/bin/python scripts/build_embeddings.py



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


COPY --from=builder /build/data /app/data


COPY --from=builder /build/.cache/huggingface \
    /home/appuser/.cache/huggingface


COPY --chown=appuser:appuser . .


RUN mkdir -p \
    /app/db \
    /app/logs \
    /home/appuser/.cache/huggingface \
    && chown -R appuser:appuser \
        /app \
        /home/appuser/.cache


USER appuser


ENV PATH="/app/.venv/bin:$PATH"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

ENV HF_HOME=/home/appuser/.cache/huggingface
ENV TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface


EXPOSE 8000


HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
CMD curl -f http://localhost:8000/health || exit 1


CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]