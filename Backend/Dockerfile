# # ============================================================================
# # Stage 1: Builder - Install dependencies and pre-download models
# # ============================================================================
# FROM python:3.12-slim AS builder

# WORKDIR /build

# # Install system dependencies
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

# # Copy dependency files first (for better layer caching)
# COPY pyproject.toml pyproject.lock* ./

# # Install Python dependencies
# RUN pip install --no-cache-dir --upgrade pip setuptools && \
#     pip install --no-cache-dir uv && \
#     uv pip install --system --no-cache-dir -e .

# # Pre-download transformers model (BAAI/bge-m3) to cache
# # This runs during build, so model is already available at runtime
# ENV HF_HOME=/build/.cache/huggingface
# RUN python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('BAAI/bge-m3'); print('Model cached successfully')"

# # ============================================================================
# # Stage 2: Runtime - Lightweight production image
# # ============================================================================
# FROM python:3.12-slim

# WORKDIR /app

# # Install runtime dependencies only
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     curl \
#     && rm -rf /var/lib/apt/lists/*

# # Create non-root user for security
# RUN useradd -m -u 1000 appuser

# # Copy Python environment from builder
# COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
# COPY --from=builder /usr/local/bin /usr/local/bin

# # Copy pre-cached models from builder (significantly faster startup)
# COPY --from=builder --chown=appuser:appuser /build/.cache /home/appuser/.cache

# # Copy application code
# COPY --chown=appuser:appuser . .

# # Set HuggingFace cache directory
# ENV HF_HOME=/home/appuser/.cache/huggingface
# ENV PYTHONUNBUFFERED=1
# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PATH="/home/appuser/.local/bin:$PATH"

# # Switch to non-root user
# USER appuser

# # Health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD curl -f http://localhost:8000/health || exit 1

# # Expose port
# EXPOSE 8000

# # Run application with uvicorn
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


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
# Pre-build RAG embeddings
# ============================================================================

ENV HF_HOME=/build/.cache/huggingface
ENV TRANSFORMERS_CACHE=/build/.cache/huggingface

RUN mkdir -p /build/data

RUN /build/.venv/bin/python scripts/build_embeddings.py


# ============================================================================
# Stage 2: Runtime
# ============================================================================

FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*


RUN useradd -m -u 1000 appuser


COPY --from=builder /build/.venv /app/.venv

# Copy application
COPY --chown=appuser:appuser . .

# Copy generated embeddings + model cache
COPY --from=builder --chown=appuser:appuser /build/data /app/data
COPY --from=builder --chown=appuser:appuser /build/.cache/huggingface /home/appuser/.cache/huggingface


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