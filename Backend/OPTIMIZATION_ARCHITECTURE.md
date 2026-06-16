# Docker Image Optimization Architecture

## Goal
Reduce Docker image size from **16.7 GB → <1 GB** while maintaining RAG functionality and startup performance.

---

## Current State Analysis

### Image Breakdown (16.7 GB)
- **HuggingFace Cache** (.cache): 4.56 GB
- **site-packages**: 5.79 GB
- **Build artifacts**: ~3 GB
- **Base OS + other**: ~3.35 GB

### Root Causes
1. ❌ Downloading BAAI/bge-m3 model (500MB+) during Docker build
2. ❌ Storing HuggingFace cache in final image
3. ❌ Including build tools, dev dependencies in runtime
4. ❌ SentenceTransformer brings heavy dependencies (torch, scikit-learn, etc.)
5. ❌ No layer cleanup between build and runtime stages

---

## Optimized Architecture

### Workflow: CI/CD → Image → Runtime

```
┌─────────────────────────────────────────────────────────────────┐
│ GitHub Actions (Pre-build Phase)                                │
├─────────────────────────────────────────────────────────────────┤
│ 1. Cache BAAI/bge-m3 model (~500 MB)                           │
│ 2. Generate embeddings.npy using build_embeddings.py            │
│ 3. Upload embeddings.npy as artifact                            │
│ 4. Build Docker image → Download embeddings artifact            │
│ 5. Push image to Docker Hub                                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Dockerfile (Multi-Stage Build)                                  │
├─────────────────────────────────────────────────────────────────┤
│ Stage 1: Builder (temporary, discarded)                         │
│   - Python 3.12-slim                                            │
│   - Download SentenceTransformer model (temp)                   │
│   - Install build dependencies                                  │
│   - Generate embeddings if not from CI/CD                       │
│                                                                  │
│ Stage 2: Runtime (final image ~600-800 MB)                      │
│   - Python 3.12-slim                                            │
│   - Copy embeddings.npy from CI/CD                              │
│   - Install only runtime dependencies (stripped)                │
│   - NO cache, NO build tools, NO models                         │
│   - Strip site-packages of unnecessary files                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Runtime Container                                               │
├─────────────────────────────────────────────────────────────────┤
│ 1. Load pre-generated embeddings.npy (~10 MB)                  │
│ 2. Initialize BM25 from DataFrame                               │
│ 3. Start Qdrant client (connect to separate container)          │
│ 4. Load FastEmbed model (optional, much smaller)                │
│ 5. Serve FastAPI endpoints                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Optimization Strategies

### 1. **Pre-Built Embeddings (CI/CD)**
- ✅ Generate embeddings.npy in GitHub Actions with cached model
- ✅ Store as artifact, download during image build
- ✅ No runtime model downloads
- ✅ Instant RAG readiness

### 2. **Multi-Stage Dockerfile**
```
Stage 1 (Builder): ~8-10 GB
  └─ Download SentenceTransformer (temp)
  └─ Install build tools (temp)
  └─ Create production wheels (reused)

Stage 2 (Runtime): ~600-800 MB
  └─ Copy only wheels + embeddings
  └─ Strip site-packages (.dist-info, tests, docs, etc.)
  └─ Remove cache, build artifacts
```

### 3. **Lightweight SentenceTransformer Replacement**
- **Current**: SentenceTransformer (500MB+ model, heavy dependencies)
- **Alternative**: FastEmbed (50-100MB model, minimal deps)
- **Trade-off**: FastEmbed slightly less accurate but 5-10x smaller
- **Both**: Keep SentenceTransformer for flexibility, load on-demand

### 4. **Dependency Stripping**
Remove from final image:
- ❌ `.dist-info/`, `.pyc`, `__pycache__`
- ❌ Tests, docs, examples
- ❌ Build tools (build-essential, gcc, make)
- ❌ Development packages
- ✅ Only: Core runtime dependencies

### 5. **Base Image Optimization**
- Use `python:3.12-slim` (NOT full) - saves ~500 MB
- Minimal OS layer
- Essential build tools removed post-install

---

## File Structure (Post-Optimization)

```
Backend/
├── Dockerfile (multi-stage, optimized)
├── .dockerignore (comprehensive)
├── build_embeddings.py (CI/CD standalone)
├── rag_pipeline.py (loads pre-built embeddings)
├── pyproject.toml (production-only deps)
├── .github/workflows/
│   └── build-and-push.yml (CI/CD with artifact generation)
├── config/
│   └── .env (runtime config)
├── data/
│   └── embeddings.npy (pre-generated, ~10 MB)
└── ... (rest of app)
```

---

## Expected Image Sizes (Per Stage)

| Stage | Size | Notes |
|-------|------|-------|
| **Current** | 16.7 GB | Baseline |
| **Remove cache** | ~12 GB | -4.56 GB |
| **Strip site-packages** | ~8 GB | Remove .dist-info, tests |
| **Remove build tools** | ~6 GB | No gcc, make, build-essential |
| **Lightweight base** | ~5.5 GB | slim image |
| **Optimized multi-stage** | ~800 MB | Builder discarded, only essentials |
| **FastEmbed variant** | ~500 MB | SentenceTransformer → FastEmbed |

---

## Implementation Steps

### Phase 1: CI/CD Infrastructure
1. Create `build_embeddings.py` (standalone, no Docker)
2. Create GitHub Actions workflow
3. Cache HuggingFace models
4. Generate embeddings artifact

### Phase 2: Docker Optimization
1. Update Dockerfile (multi-stage)
2. Create optimized .dockerignore
3. Strip unnecessary files from site-packages
4. Download embeddings from CI/CD artifact

### Phase 3: Application Code
1. Update `rag_pipeline.py` to load pre-built embeddings
2. Remove runtime model downloads
3. Add health checks, startup validation

### Phase 4: Dependency Optimization
1. Update pyproject.toml (production-only)
2. Consider FastEmbed alternative
3. Remove unnecessary transitive dependencies

### Phase 5: Testing & Validation
1. Build locally and measure sizes
2. Inspect layers: `docker history backend-app:latest`
3. Run startup tests
4. Compare performance vs. original

---

## Dependency Impact Analysis

### Current Heavy Dependencies
- **torch** (PyTorch): ~600 MB → Remove if FastEmbed used
- **scikit-learn**: ~300 MB → Keep (BM25, classifiers)
- **sentence-transformers**: ~400 MB → FastEmbed: ~50 MB
- **transformers** (HuggingFace): ~500 MB → Embedded in FastEmbed
- **numpy, pandas**: ~200 MB → Keep (data processing)

### Production-Only Dependencies
Remove:
- pytest, black, isort, flake8, mypy
- jupyter, notebook
- dev-only packages

Keep:
- fastapi, uvicorn
- sqlalchemy
- numpy, pandas
- scikit-learn (BM25)
- sentence-transformers OR fastembed
- qdrant-client
- python-dotenv
- groq/openai

---

## Runtime Initialization (Optimized)

```python
# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Database setup (fast)
    Base.metadata.create_all(bind=engine)
    
    # 2. Load pre-built embeddings (10 MB load, instant)
    embeddings = np.load("/app/data/embeddings.npy")
    
    # 3. Initialize BM25 (fast, from DataFrame)
    tokenized_corpus = [text.lower().split() for text in df["Context"]]
    bm25 = BM25Okapi(tokenized_corpus)
    
    # 4. Connect to Qdrant (already running)
    qdrant_client = QdrantClient(host="qdrant", port=6333)
    
    # 5. Initialize FastEmbed (lightweight, optional)
    from fastembed import SparseTextEmbedding
    embedding_model = SparseTextEmbedding(model_name="BM25")
    
    # Startup complete, RAG ready
    RAG_READY_EVENT.set()
    
    yield
    
    logger.info("Shutting down...")
```

### Startup Timeline (Optimized)
- Database: ~1 sec
- Load embeddings: ~2 sec
- BM25 init: ~5 sec
- Qdrant connect: ~2 sec
- **Total**: ~10 seconds (vs. 30-60 current)

---

## Docker Build Command

```bash
# Build with GitHub Actions artifacts
docker build -t backend-app:latest \
  --build-arg EMBEDDINGS_URL="path/to/embeddings.npy" \
  .

# Or locally (generate embeddings first)
python build_embeddings.py
docker build -t backend-app:latest .

# Inspect sizes
docker history backend-app:latest
docker image inspect backend-app:latest | grep -i size
du -sh $(docker inspect -f '{{.GraphDriver.Data.MergedDir}}' backend-app:latest)
```

---

## Validation Checklist

- [ ] Image builds successfully
- [ ] Image size < 1 GB
- [ ] App starts in < 15 seconds
- [ ] Health endpoint returns `rag_ready: true`
- [ ] All API endpoints functional
- [ ] docker-compose up works
- [ ] No model re-downloads at runtime
- [ ] Embeddings loaded correctly
- [ ] Qdrant connection working
- [ ] Performance matches or exceeds original

---

## Rollback Plan

If optimizations cause issues:
1. Revert Dockerfile to previous version
2. Keep .dockerignore changes (safe)
3. Restore build_embeddings.py (non-breaking)
4. Test incrementally

---

## Cost & Benefit Summary

| Metric | Current | Optimized | Improvement |
|--------|---------|-----------|-------------|
| Image Size | 16.7 GB | ~800 MB | **95% reduction** |
| Pull Time | ~5 min | ~20 sec | **15x faster** |
| Startup Time | 30-60 sec | ~10 sec | **3-6x faster** |
| Build Time (CI/CD) | ~5 min | ~8 min | Acceptable for size gain |
| Cache Hit Rate | ~30% | ~95% | Fewer rebuilds |

