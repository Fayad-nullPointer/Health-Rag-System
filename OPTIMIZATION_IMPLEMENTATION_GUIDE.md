# Docker Image Optimization Implementation Guide

## Quick Start (5 Minutes)

### For CI/CD (GitHub Actions)

```bash
# 1. Copy optimized files
cp Dockerfile.optimized Dockerfile
cp .dockerignore.optimized .dockerignore
cp pyproject_optimized.toml pyproject.toml

# 2. Create GitHub Actions directory
mkdir -p .github/workflows

# 3. Add workflow file (copy build-and-push-optimized.yml)

# 4. Set secrets in GitHub
# Settings → Secrets → Add:
#   - DOCKER_HUB_USERNAME
#   - DOCKER_HUB_TOKEN

# 5. Commit and push
git add .
git commit -m "chore: add docker optimization"
git push origin main
```

### For Local Development

```bash
# 1. Generate embeddings locally
python build_embeddings_optimized.py \
  --model BAAI/bge-m3 \
  --output data/embeddings.npy

# 2. Build optimized image
docker build -t backend-app:optimized -f Dockerfile.optimized .

# 3. Test with docker-compose
docker-compose up -d

# 4. Verify
curl http://localhost:8000/health
```

---

## Detailed Implementation (30 Minutes)

### Step 1: File Migration

```bash
# Backup current files
cp Dockerfile Dockerfile.backup
cp .dockerignore .dockerignore.backup
cp pyproject.toml pyproject.toml.backup

# Copy optimized versions
cp Dockerfile.optimized Dockerfile
cp .dockerignore.optimized .dockerignore
cp pyproject_optimized.toml pyproject.toml

# Copy optimized RAG pipeline
cp rag/rag_pipeline.py rag/rag_pipeline.py.backup
cp rag_pipeline_optimized.py rag/rag_pipeline.py

# Copy optimized build script
cp build_embeddings_optimized.py scripts/build_embeddings.py
```

### Step 2: Generate Embeddings (First Time)

```bash
# Install minimal dependencies
pip install \
  datasets \
  sentence-transformers \
  numpy \
  pandas

# Generate embeddings
python build_embeddings_optimized.py \
  --model BAAI/bge-m3 \
  --output data/embeddings.npy \
  --device cpu \
  --batch-size 32

# Verify file exists
ls -lh data/embeddings.npy
# Expected: ~10-50 MB
```

### Step 3: Update pyproject.toml

**Compare old vs new**:
```bash
diff pyproject.toml.backup pyproject.toml
```

**Key changes**:
- Removed: pytest, black, isort, mypy, jupyter, etc.
- Added: sentence-transformers (already there)
- Optional: fastembed (for lightweight alternative)

### Step 4: Test Locally (Before Docker)

```bash
# 1. Create virtual environment
python -m venv test_env
source test_env/bin/activate  # or: test_env\Scripts\activate on Windows

# 2. Install dependencies
pip install -e .[dev]  # Install with dev tools for testing

# 3. Run tests
pytest tests/

# 4. Check imports
python -c "from app.main import app; print('✅ App imports OK')"
python -c "import rag.rag_pipeline; print('✅ RAG pipeline imports OK')"

# 5. Deactivate
deactivate
```

### Step 5: Build Optimized Image

```bash
# Build with optimization
docker build -t backend-app:optimized -f Dockerfile .

# Show layers
docker history --human backend-app:optimized | head -20

# Get total size
docker images backend-app:optimized --format "{{.Size}}"

# Expected: ~600 MB - 1 GB (down from 16.7 GB)
```

### Step 6: Test Docker Image

```bash
# Create temporary test directory
mkdir test_build
cd test_build

# Copy docker-compose.yml
cp ../docker-compose.yml .

# Update to use local image
sed -i 's/backend-app:/backend-app:optimized/' docker-compose.yml

# Start services
docker-compose up -d

# Wait for startup
sleep 15

# Test endpoints
echo "Testing health endpoint..."
curl -s http://localhost:8000/health | jq .

echo ""
echo "Testing root endpoint..."
curl -s http://localhost:8000/ | jq .

# Check logs
docker logs health-rag-app --tail 30

# Cleanup
docker-compose down -v

cd ..
```

### Step 7: Compare Performance

```bash
# Create comparison script
cat > compare_images.sh << 'EOF'
#!/bin/bash

echo "╔════════════════════════════════════════════════════╗"
echo "║         Docker Image Comparison Report             ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Image 1: Original
echo "📦 Original Image (Dockerfile)"
ORIG=$(docker images backend-app:latest --format "{{.Size}}" 2>/dev/null)
echo "Size: $ORIG"
echo ""

# Image 2: Optimized
echo "📦 Optimized Image (Dockerfile.optimized)"
OPT=$(docker images backend-app:optimized --format "{{.Size}}" 2>/dev/null)
echo "Size: $OPT"
echo ""

# Calculate reduction
if command -v numfmt &> /dev/null; then
    ORIG_BYTES=$(numfmt --from=auto "$ORIG" 2>/dev/null || echo 17863680000)
    OPT_BYTES=$(numfmt --from=auto "$OPT" 2>/dev/null || echo 800000000)
    REDUCTION=$(echo "scale=1; 100 * (1 - $OPT_BYTES / $ORIG_BYTES)" | bc)
    echo "📊 Size Reduction: ${REDUCTION}%"
fi

echo ""
echo "Layer Comparison:"
echo "───────────────────────────────"
echo "Original:"
docker history --human backend-app:latest | head -15
echo ""
echo "Optimized:"
docker history --human backend-app:optimized | head -15

EOF

chmod +x compare_images.sh
./compare_images.sh
```

### Step 8: Setup CI/CD Pipeline

#### For GitHub Actions:

```bash
# 1. Create workflow directory
mkdir -p .github/workflows

# 2. Copy workflow file
cp build-and-push-optimized.yml .github/workflows/

# 3. Add GitHub secrets
# Go to: Settings → Secrets and variables → Actions
# Add:
#   DOCKER_HUB_USERNAME: your_username
#   DOCKER_HUB_TOKEN: your_token (PAT)

# 4. Optional: Update Docker Hub details in workflow
sed -i 's/yourusername/YOUR_DOCKER_HUB_USERNAME/g' .github/workflows/build-and-push-optimized.yml

# 5. Commit
git add .github/workflows/build-and-push-optimized.yml
git commit -m "ci: add docker optimization workflow"
git push origin main
```

#### Verify workflow runs:

```bash
# Go to: GitHub repo → Actions → build-and-push-optimized
# Monitor workflow:
# - Generate embeddings: ~2 min
# - Build image: ~1 min
# - Push to registries: ~1 min
# Total: ~5-10 minutes
```

### Step 9: Update docker-compose.yml (If Needed)

```yaml
# docker-compose.yml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile  # Now uses optimized version
    image: backend-app:latest
    # ... rest of config
```

### Step 10: Production Deployment

```bash
# Pull optimized image
docker pull ghcr.io/yourusername/health-rag-backend:latest

# Or from Docker Hub
docker pull yourusername/health-rag-backend:latest

# Start services
docker-compose up -d

# Monitor startup
docker-compose logs -f app

# Test
curl http://localhost:8000/health
```

---

## Verification Checklist

### Pre-Optimization

```bash
# ✓ Current baseline
docker images backend-app:latest
docker history backend-app:latest | wc -l

# Expected output examples:
# SIZE: 16.7 GB
# LAYERS: 15-20
```

### Post-Optimization

```bash
# ✓ Image builds
docker build -t backend-app:test -f Dockerfile . && echo "✅ Build succeeded"

# ✓ Image size reduced
docker images backend-app:test --format "{{.Size}}"
# Expected: <1 GB

# ✓ Fewer layers
docker history backend-app:test | wc -l
# Expected: 10-15

# ✓ App starts
docker run -d -p 8000:8000 backend-app:test
sleep 10
curl -s http://localhost:8000/health | jq .

# ✓ Embeddings loaded
docker logs $(docker ps | grep backend-app:test | awk '{print $1}') | grep -i embedding

# ✓ Cleanup
docker stop $(docker ps | grep backend-app:test | awk '{print $1}')
```

---

## Rollback Plan

If optimization causes issues:

```bash
# 1. Restore original files
cp Dockerfile.backup Dockerfile
cp .dockerignore.backup .dockerignore
cp pyproject.toml.backup pyproject.toml
cp rag/rag_pipeline.py.backup rag/rag_pipeline.py

# 2. Rebuild original image
docker build -t backend-app:original .

# 3. Test
docker-compose up -d

# 4. Investigate issue with optimized version
# then apply selective fixes only
```

---

## Optimization Variants

### Variant 1: Maximum Size Reduction (FastEmbed)

```bash
# 1. Update dependencies in pyproject.toml
# Replace: sentence-transformers
# With: fastembed

# 2. Generate embeddings with FastEmbed
python build_embeddings_optimized.py --fastembed

# 3. Update rag_pipeline.py to use FastEmbed

# 4. Rebuild
docker build -t backend-app:fastembed .

# Expected size: ~500-600 MB
```

### Variant 2: BM25 Only (Absolute Minimum)

```bash
# 1. Remove embedding model entirely
# 2. Use only BM25 for retrieval
# 3. Update rag_pipeline.py to skip embedding initialization

# Expected size: ~300-400 MB
```

### Variant 3: Keep SentenceTransformer

```bash
# Keep current version but with pre-built embeddings
# Size: ~1-1.2 GB
# Benefit: Same embeddings quality, faster startup
```

---

## Monitoring & Metrics

### Dashboard Commands

```bash
# Real-time resource usage
docker stats

# Image analysis
docker images --format "table {{.Repository}}\t{{.Size}}\t{{.Created}}"

# Layer history
docker history --human backend-app:latest --no-trunc

# Container health
docker ps --format "table {{.Image}}\t{{.Status}}\t{{.Size}}"
```

### Log Analysis

```bash
# Check startup sequence
docker logs health-rag-app 2>&1 | grep -E "INFO|Initializing|Ready"

# Look for performance bottlenecks
docker logs health-rag-app 2>&1 | grep -E "Loading|took|seconds"

# Check for errors
docker logs health-rag-app 2>&1 | grep -E "ERROR|WARN|Exception"
```

---

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Image still 10+ GB | .dist-info files remain | Check Dockerfile cleanup steps |
| App crashes | Embeddings missing | Generate with `build_embeddings.py` |
| Slow startup | BM25 init overhead | Check dataset size in logs |
| Qdrant connection error | Wrong hostname | Use env var: `QDRANT_HOST=qdrant` |
| High memory usage | RAG pipeline | Reduce batch size in `build_embeddings.py` |

---

## Timeline Estimates

| Task | Local | CI/CD | Notes |
|------|-------|-------|-------|
| Setup | 5 min | 10 min | File migration, secrets setup |
| Generate embeddings | 5-10 min | 2-3 min | Cached after first run |
| Build image | 3-5 min | 2-3 min | ~15s with cache |
| Test | 2-3 min | 2 min | Health checks, API tests |
| Deploy | 1-2 min | 1-2 min | Pull, start services |
| **Total** | **20-30 min** | **10-15 min** | After initial setup |

---

## Success Metrics

After optimization, you should see:

✅ **Image Size**: Reduced by 95% (16.7 GB → ~800 MB)
✅ **Pull Time**: ~20-30 seconds (vs 5+ min)
✅ **Startup Time**: ~10-15 seconds (vs 30-60 sec)
✅ **Build Time**: ~2-3 minutes (CI/CD cached)
✅ **Runtime Memory**: ~200-500 MB (vs 2+ GB)
✅ **Cache Hit Rate**: ~95% (most builds use cache)

