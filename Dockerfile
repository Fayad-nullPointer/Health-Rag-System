FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Step 1: Install PyTorch CPU-only from the dedicated PyTorch index ──
# This is done separately because torch needs --index-url pointing to the
# PyTorch CPU wheel server; mixing it with --extra-index-url in a single
# pip install can cause resolver conflicts and CUDA wheels being pulled.
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu

# ── Step 2: Install remaining Python dependencies ──
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Step 3: Copy core application files ──
COPY config.py .
COPY api.py .
COPY auth.py .
COPY cache_layer.py .
COPY memory.py .
COPY pipeline.py .

# ── Step 4: Copy necessary directories ──
COPY classifier/ ./classifier/
COPY routes/ ./routes/
COPY static/ ./static/
COPY locales/ ./locales/

# ── Step 5: Setup container ──
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# ── Step 6: Run application ──
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]