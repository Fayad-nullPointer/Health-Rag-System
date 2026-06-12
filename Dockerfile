FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Step 1: Copy dependencies ──
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Step 2: Copy core application files ──
COPY config.py .
COPY api.py .
COPY auth.py .
COPY cache_layer.py .
COPY memory.py .
COPY pipeline.py .

# ── Step 3: Copy necessary directories ──
COPY classifier/ ./classifier/
COPY routes/ ./routes/
COPY static/ ./static/
COPY locales/ ./locales/

# ── Step 4: Setup container ──
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# ── Step 5: Run application ──
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]