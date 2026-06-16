# ============================================================================
# Stage 1: Builder - Install dependencies and pre-download models
# ============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (for better layer caching)
COPY pyproject.toml pyproject.lock* ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir uv && \
    uv pip install --system --no-cache-dir -e .

# Pre-download transformers model (BAAI/bge-m3) to cache
# This runs during build, so model is already available at runtime
ENV HF_HOME=/build/.cache/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('BAAI/bge-m3'); print('Model cached successfully')"

# ============================================================================
# Stage 2: Runtime - Lightweight production image
# ============================================================================
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Copy Python environment from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy pre-cached models from builder (significantly faster startup)
COPY --from=builder --chown=appuser:appuser /build/.cache /home/appuser/.cache

# Copy application code
COPY --chown=appuser:appuser . .

# Set HuggingFace cache directory
ENV HF_HOME=/home/appuser/.cache/huggingface
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/home/appuser/.local/bin:$PATH"

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
