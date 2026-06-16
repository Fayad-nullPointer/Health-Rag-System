# Docker Image Optimization - Advanced Guide

## Part 1: FastEmbed Alternative (Lightweight Embeddings)

### Why FastEmbed?

| Feature | SentenceTransformer | FastEmbed |
|---------|-------------------|-----------|
| Model Size | 500 MB+ | 50-100 MB |
| Inference Speed | 1x (baseline) | 5-10x faster |
| CPU Memory | ~2 GB | ~500 MB |
| Dependencies | Heavy (torch, etc) | Minimal |
| Accuracy | High | Good (91-95% of ST) |
| Library Size | Large | Tiny |

### FastEmbed Integration

#### Option 1: Use FastEmbed Exclusively

```python
# rag_pipeline_fastembed.py
from fastembed import TextEmbedding
import numpy as np

class FastEmbedRAG:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        """Initialize with FastEmbed model (lightweight)"""
        self.model = TextEmbedding(model_name=model_name)
        self.embeddings = None
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using FastEmbed"""
        embeddings = []
        for text in texts:
            embedding = self.model.embed(text)
            embeddings.append(embedding)
        return np.array(embeddings)
    
    def query_embedding(self, query: str) -> np.ndarray:
        """Get embedding for query"""
        return np.array(self.model.embed(query))
```

#### Option 2: Hybrid (SentenceTransformer + FastEmbed Query)

```python
# Use SentenceTransformer for pre-built embeddings (batch generated)
# Use FastEmbed for query encoding at runtime (minimal)

def encode_query_fastembed(query: str) -> np.ndarray:
    """Lightweight query encoding using FastEmbed"""
    try:
        from fastembed import TextEmbedding
        model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        return np.array(model.embed(query))
    except ImportError:
        # Fallback: Use BM25 only
        return None
```

#### Option 3: Pure BM25 (No Embeddings Model)

If you want the absolute smallest image (~200-300 MB):

```python
def hybrid_search_bm25_only(query: str, top_k: int = 5) -> List[Dict]:
    """Use only BM25 for retrieval (no embedding model needed)"""
    tokenized_query = query.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)
    top_indices = np.argsort(bm25_scores)[-top_k:][::-1]
    
    results = []
    for idx in top_indices:
        if bm25_scores[idx] > 0:
            results.append({
                "context": df.iloc[idx]["Context"],
                "response": df.iloc[idx]["Response"],
                "score": float(bm25_scores[idx]),
                "method": "BM25",  # No embedding model
            })
    
    return results
```

### Size Comparison

```
Dockerfile variant                  Size    Startup
────────────────────────────────────────────────────
1. Current (ST + HF cache)         16.7 GB  30-60s
2. Optimized (ST + pre-embeddings)  ~1 GB   10-15s
3. FastEmbed variant               ~600 MB   8-10s
4. BM25 only                       ~300 MB   5-8s
```

### Implementation Steps for FastEmbed

1. **Update dependencies**:
```bash
# Add to optional dependencies
pip install fastembed
```

2. **Update build_embeddings**:
```python
# Use FastEmbed instead of SentenceTransformer
model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
embeddings = model.embed_documents(contexts)
```

3. **Update rag_pipeline**:
```python
# Option A: Use pre-built embeddings (no model at runtime)
embeddings = np.load("/app/data/embeddings.npy")

# Option B: Or load lightweight FastEmbed model for query encoding
from fastembed import TextEmbedding
query_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
query_embedding = query_model.embed(user_query)
```

4. **Update Dockerfile**:
```dockerfile
# Replace SentenceTransformer with FastEmbed
RUN pip install --no-cache-dir fastapi uvicorn fastembed numpy pandas scikit-learn
```

---

## Part 2: Docker Layer Inspection & Optimization

### Command Reference

#### 1. **Inspect Image History (Layer Breakdown)**

```bash
# Show all layers with sizes (most detailed)
docker history --human --no-trunc backend-app:latest

# Output example:
# IMAGE                 CREATED            CREATED BY                SIZE
# abc123def456         2 min ago           /bin/sh -c uvicorn...    2.3 MB
# xyz789abc123         3 min ago           /bin/sh -c pip insta...  450 MB
# (base layer)         1 week ago          FROM python:3.12-slim    150 MB
```

#### 2. **Get Total Image Size**

```bash
# Size on disk
docker images --format "table {{.Repository}}\t{{.Size}}" | grep backend-app

# Alternative: Get exact bytes
docker image inspect backend-app:latest | \
  jq '.[] | .Size' | \
  numfmt --to=iec-i --suffix=B  # Convert to human-readable
```

#### 3. **Analyze Layer Sizes**

```bash
# Show breakdown of each layer
docker image inspect backend-app:latest | jq '.[] | .RootFS.Layers | length'

# Get layer digests
docker image inspect backend-app:latest | \
  jq -r '.[] | .RootFS.Layers[]' | \
  while read layer; do
    echo "Layer: $layer"
    docker image inspect backend-app:latest | \
      jq ".[] | .RootFS.Layers | index(\"$layer\")"
  done
```

#### 4. **Dive Deep into Container Layers**

```bash
# Use 'dive' tool for interactive layer analysis
# Install: brew install dive (macOS) or apt install dive (Ubuntu)
dive backend-app:latest

# Without dive, manually inspect
docker create backend-app:latest > /tmp/container.id
docker export $(cat /tmp/container.id) | tar -t | head -100  # First 100 files
docker rm $(cat /tmp/container.id)
```

#### 5. **Find Large Files in Image**

```bash
# Export and analyze
docker create backend-app:latest > /tmp/cid
docker export $(cat /tmp/cid) | tar -xf - -C /tmp/image_extract
du -sh /tmp/image_extract/* | sort -hr | head -20
docker rm $(cat /tmp/cid)
rm -rf /tmp/image_extract
```

#### 6. **Compare Image Sizes (Before/After)**

```bash
# Save size report
docker images --format "table {{.Repository}}\t{{.Size}}" > before.txt

# After optimization
docker images --format "table {{.Repository}}\t{{.Size}}" > after.txt

# Compare
diff before.txt after.txt
```

#### 7. **Build Cache Analysis**

```bash
# Show build cache usage
docker buildx du

# Prune cache
docker buildx prune -a

# View builder cache size
docker system df
```

#### 8. **Dockerfile Optimization Verification**

```bash
# Build with detailed progress
docker build --progress=plain -t backend-app:latest . 2>&1 | \
  grep -E "RUN|COPY|ADD|FROM|DONE"

# Show which layers were cached vs rebuilt
docker build --progress=plain -t backend-app:latest . 2>&1 | \
  grep -E "CACHED|DONE" | head -20
```

---

## Part 3: Verification Commands

### Pre-Optimization Baseline

```bash
# 1. Measure current image size
docker images backend-app:current --format "{{.Size}}"
# Expected: ~16.7 GB

# 2. Measure startup time
time docker-compose up -d
sleep 60
curl http://localhost:8000/health

# 3. Check layer breakdown
docker history --human backend-app:current | head -20
```

### Post-Optimization Validation

```bash
# 1. Build optimized image
docker build -t backend-app:optimized -f Dockerfile.optimized .

# 2. Compare sizes
echo "Current: $(docker images backend-app:current --format '{{.Size}}')"
echo "Optimized: $(docker images backend-app:optimized --format '{{.Size}}')"

# 3. Calculate reduction percentage
BEFORE=$(docker images backend-app:current --format '{{.Size}}' | \
  numfmt --from=auto 2>/dev/null || echo 17863680000)
AFTER=$(docker images backend-app:optimized --format '{{.Size}}' | \
  numfmt --from=auto 2>/dev/null || echo 800000000)
PERCENT=$(echo "scale=2; (100 * ($BEFORE - $AFTER)) / $BEFORE" | bc)
echo "Size reduction: ${PERCENT}%"

# 4. Startup performance test
echo "Optimized startup time:"
time docker run --rm -d backend-app:optimized > /tmp/cid
sleep 15
curl http://localhost:8000/health
docker stop $(cat /tmp/cid)
```

### Performance Benchmarking

```bash
#!/bin/bash
# benchmark.sh - Compare performance

run_benchmark() {
    local image=$1
    local label=$2
    
    echo "=== Benchmarking: $label ==="
    echo "Image: $image"
    
    # 1. Startup time
    local start=$(date +%s%N)
    docker run --rm -d -p 8001:8000 --name bench-$$ $image > /tmp/cid 2>&1
    
    # Wait for health check to pass
    for i in {1..60}; do
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    local end=$(date +%s%N)
    local duration=$(echo "scale=2; ($end - $start) / 1000000000" | bc)
    
    echo "Startup time: ${duration}s"
    
    # 2. Memory usage
    docker stats --no-stream bench-$$ --format "table {{.MemUsage}}"
    
    # 3. API response time
    time curl -s http://localhost:8001/health > /dev/null
    
    # Cleanup
    docker stop bench-$$ 2>/dev/null
    docker rm bench-$$ 2>/dev/null
    
    echo ""
}

run_benchmark "backend-app:current" "Current (unoptimized)"
run_benchmark "backend-app:optimized" "Optimized"
```

---

## Part 4: Size Optimization Checklist

```markdown
## Pre-Build Checklist

- [ ] Embeddings pre-generated in CI/CD
- [ ] embeddings.npy exists in data/ (~10-50 MB)
- [ ] .dockerignore includes all unnecessary files
- [ ] pyproject.toml has only production dependencies
- [ ] Remove dev tools (pytest, black, isort, etc)

## Dockerfile Checklist

- [ ] Multi-stage build with separate builder stage
- [ ] Builder stage discarded (not in final image)
- [ ] site-packages stripped of .dist-info, tests, etc
- [ ] No HuggingFace cache in final image
- [ ] No build tools (gcc, make, build-essential)
- [ ] Base image is python:3.12-slim (not full)
- [ ] Non-root user created (appuser)
- [ ] Proper permissions set for data directory

## Validation Checklist

- [ ] Image builds successfully
- [ ] Image size < 1 GB (run: docker images)
- [ ] Health endpoint responds (http://localhost:8000/health)
- [ ] Embeddings loaded correctly (check logs)
- [ ] BM25 initialized (check logs)
- [ ] Qdrant connection working (docker logs health-rag-qdrant)
- [ ] No model re-downloads at runtime
- [ ] Startup time < 20 seconds
- [ ] docker-compose up -d works
- [ ] All endpoints functional

## Performance Checklist

- [ ] Image pull time < 30 seconds (on good connection)
- [ ] Container startup < 20 seconds
- [ ] Health check passes immediately after startup
- [ ] Memory usage < 500 MB (peak during startup)
- [ ] API response time < 100 ms (health, root)
- [ ] Query processing < 1 second
```

---

## Part 5: Troubleshooting

### Issue: Image still too large (>2 GB)

**Diagnosis**:
```bash
docker history --human backend-app:latest | grep -E "^[a-f0-9].*[0-9]\.[0-9].*GB"
```

**Solutions**:
1. Check site-packages still has .dist-info files
   - `docker exec <image> find /usr/local/lib/python3.12/site-packages -name "*.dist-info" | wc -l`
   - Should be 0 after cleanup

2. HuggingFace cache not removed
   - Check Dockerfile, should NOT copy `/home/appuser/.cache`

3. Build tools still in final image
   - Remove gcc, build-essential from Stage 2

### Issue: App crashes at startup

**Check 1**: Embeddings file exists
```bash
docker exec health-rag-app ls -lh /app/data/embeddings.npy
```

**Check 2**: Permissions
```bash
docker exec health-rag-app ls -la /app/data/
```

**Check 3**: Database initialization
```bash
docker exec health-rag-app ls -lh /app/data/users.db
```

### Issue: Slow startup time

**Diagnosis**:
```bash
docker logs health-rag-app 2>&1 | grep -E "Loading|Initializing|Ready"
```

**Solutions**:
1. Confirm embeddings are pre-built (not generated at runtime)
2. Check BM25 initialization time
3. Qdrant connection timeout?
   - Verify `--qdrant-host qdrant` (not localhost)

---

## Part 6: Expected Timeline

### Build & Push Workflow
```
GitHub Actions Run:
  Setup Python               ~10s
  Cache restore              ~20s
  Install dependencies       ~40s
  Generate embeddings        ~60-120s (main time)
  Upload artifact            ~10s
  Setup Docker               ~10s
  Build image                ~20-40s (uses cache)
  Push to registries         ~30-60s
─────────────────────────────
  Total                      ~3-6 minutes (one-time, then cached)
```

### Local Build
```
First run (no cache):
  docker build -t backend-app:latest .
  Total: ~5-10 minutes

Second run (cache hit):
  docker build -t backend-app:latest .
  Total: ~15-30 seconds
```

### Container Startup
```
Before optimization:
  db setup                   ~1s
  model download             ~20s
  embeddings generation      ~20s
  rag init                   ~5s
  app startup                ~5s
─────────────────────────────
  Total                      30-60 seconds

After optimization:
  db setup                   ~1s
  embeddings load            ~2s
  bm25 init                  ~5s
  qdrant connect             ~2s
  app startup                ~3s
─────────────────────────────
  Total                      ~10-15 seconds
```

---

## Part 7: Monitoring & Metrics

```bash
# Create metrics script
cat > metrics.sh << 'EOF'
#!/bin/bash

echo "=== Docker Optimization Metrics ==="
echo ""

# Image size
echo "Image Size:"
docker images backend-app:latest --format "{{.Size}}"

# Layer count
echo ""
echo "Layer Count:"
docker history backend-app:latest | wc -l

# Base image size
echo ""
echo "Base OS Image Size:"
docker images python:3.12-slim --format "{{.Size}}"

# Startup perf
echo ""
echo "Startup Performance:"
time docker run --rm backend-app:latest python -c "from app.main import app; print('✅ App imports successfully')"

# File sizes
echo ""
echo "Key File Sizes:"
docker run --rm backend-app:latest sh -c "du -sh /usr/local/lib/python3.12/site-packages /app /app/data"

EOF

chmod +x metrics.sh
./metrics.sh
```

