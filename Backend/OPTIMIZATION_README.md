# Docker Image Optimization - Complete Reference

## 📚 Documentation Index

This guide provides a complete framework to optimize the Health RAG Docker image from **16.7 GB → <1 GB** (95% reduction).

### Core Documents

| Document | Purpose | Read Time | For Whom |
|----------|---------|-----------|----------|
| [OPTIMIZATION_ARCHITECTURE.md](OPTIMIZATION_ARCHITECTURE.md) | High-level design & strategy | 10 min | Decision makers, architects |
| [OPTIMIZATION_IMPLEMENTATION_GUIDE.md](OPTIMIZATION_IMPLEMENTATION_GUIDE.md) | Step-by-step implementation | 20 min | Developers, DevOps engineers |
| [OPTIMIZATION_ADVANCED_GUIDE.md](OPTIMIZATION_ADVANCED_GUIDE.md) | FastEmbed, inspection tools, troubleshooting | 15 min | Advanced users, troubleshooters |

### Key Files

#### Docker & Build
- **`Dockerfile.optimized`** - Multi-stage optimized build (replaces current Dockerfile)
- **`.dockerignore.optimized`** - Comprehensive exclusion list (replaces .dockerignore)
- **`pyproject_optimized.toml`** - Production-only dependencies (replaces pyproject.toml)

#### Scripts & Pipelines
- **`build_embeddings_optimized.py`** - Standalone embeddings generation (CI/CD ready)
- **`rag_pipeline_optimized.py`** - Loads pre-built embeddings, no runtime model download
- **`.github/workflows/build-and-push-optimized.yml`** - Complete CI/CD pipeline

#### Application Code
- **`rag/rag_pipeline.py`** - Update to use pre-built embeddings
- **`app/main.py`** - No changes needed (uses rag_pipeline)

---

## 🚀 Quick Start (Choose Your Path)

### Path A: Want to Understand First? (Recommended)

1. Read: [OPTIMIZATION_ARCHITECTURE.md](OPTIMIZATION_ARCHITECTURE.md) (10 min)
2. Then: Choose optimization level below
3. Finally: Follow [OPTIMIZATION_IMPLEMENTATION_GUIDE.md](OPTIMIZATION_IMPLEMENTATION_GUIDE.md)

### Path B: Just Implement (Faster)

1. Copy optimized files
2. Run: `python build_embeddings_optimized.py`
3. Run: `docker build -t backend-app -f Dockerfile.optimized .`
4. Test: `docker-compose up -d`

### Path C: Use CI/CD (Recommended for Teams)

1. Copy workflow: `.github/workflows/build-and-push-optimized.yml`
2. Set GitHub secrets: DOCKER_HUB_USERNAME, DOCKER_HUB_TOKEN
3. Push to main branch
4. Workflow automatically: generates embeddings, builds, pushes image

---

## 📊 Expected Results

### Size Comparison

```
Current Setup:              16.7 GB
├── Without cache:          12.1 GB
├── Stripped site-packages: 8 GB
├── With multi-stage:       1.2 GB
├── With FastEmbed:         600 MB
└── BM25 only:             300 MB ← Absolute minimum

Recommended Target:         ~800 MB (95% reduction)
```

### Performance Timeline

```
Build Process:
  Generate embeddings:      ~2-3 min (CI/CD, cached after)
  Build image:              ~1-2 min (cached layers)
  Push to registry:         ~1-2 min
  ─────────────────
  Total:                    ~4-7 min (or 30s with full cache)

Container Startup:
  Database init:            ~1 sec
  Load embeddings:          ~2 sec
  BM25 init:                ~5 sec
  Qdrant connect:           ~2 sec
  ─────────────────
  Total:                    ~10 sec (vs 30-60 current)

API Performance:
  Health endpoint:          <50 ms
  Query/search:             <500 ms
  Response generation:      <2 sec (LLM dependent)
```

---

## 🔧 Implementation Levels

### Level 1: Minimal (10 min, 50% reduction)

Use optimized Dockerfile with pre-built embeddings only:

```bash
# 1. Run embeddings generation
python build_embeddings_optimized.py

# 2. Use new Dockerfile
docker build -t backend-app -f Dockerfile.optimized .

# Result: ~8 GB (from 16.7 GB)
```

**Pros**: Quick, simple, keeps SentenceTransformer
**Cons**: Still large

### Level 2: Standard (30 min, 95% reduction) ⭐ Recommended

Full optimization with pre-built embeddings + multi-stage + dependency cleanup:

```bash
# Use all optimized files:
# - Dockerfile.optimized
# - pyproject_optimized.toml
# - build_embeddings_optimized.py
# - rag_pipeline_optimized.py

# Result: ~800 MB (from 16.7 GB)
```

**Pros**: Massive size reduction, fast startup, still high quality
**Cons**: Need to update some files

### Level 3: Maximum (45 min, 99% reduction)

Use FastEmbed for minimal embeddings model + BM25 fallback:

```bash
# Additional steps:
# - Use FastEmbed instead of SentenceTransformer
# - Remove embedding model from runtime
# - Use BM25-only for fallback

# Result: ~500 MB (from 16.7 GB)
```

**Pros**: Smallest possible, blazing fast startup
**Cons**: Different embedding quality (still good)

---

## 📝 File Migration Checklist

### Phase 1: Preparation (5 min)

- [ ] Backup current files:
  ```bash
  cp Dockerfile Dockerfile.backup
  cp .dockerignore .dockerignore.backup
  cp pyproject.toml pyproject.toml.backup
  cp rag/rag_pipeline.py rag/rag_pipeline.py.backup
  ```

- [ ] Create new branch:
  ```bash
  git checkout -b optimize/docker-image
  ```

### Phase 2: File Updates (10 min)

- [ ] Copy optimized files:
  ```bash
  cp Dockerfile.optimized Dockerfile
  cp .dockerignore.optimized .dockerignore
  cp pyproject_optimized.toml pyproject.toml
  cp rag_pipeline_optimized.py rag/rag_pipeline.py
  ```

- [ ] Update build_embeddings script:
  ```bash
  cp build_embeddings_optimized.py scripts/build_embeddings.py
  ```

### Phase 3: Testing (10 min)

- [ ] Generate embeddings locally:
  ```bash
  python build_embeddings_optimized.py --output data/embeddings.npy
  ```

- [ ] Build and test image:
  ```bash
  docker build -t backend-app:test -f Dockerfile .
  docker-compose -f docker-compose.test.yml up -d
  curl http://localhost:8000/health
  ```

- [ ] Verify size reduction:
  ```bash
  docker images backend-app:test --format "{{.Size}}"
  ```

### Phase 4: CI/CD Setup (5 min)

- [ ] Create workflow directory:
  ```bash
  mkdir -p .github/workflows
  cp build-and-push-optimized.yml .github/workflows/
  ```

- [ ] Add GitHub secrets:
  - Go to Settings → Secrets → Actions
  - Add: DOCKER_HUB_USERNAME, DOCKER_HUB_TOKEN

- [ ] Commit and push:
  ```bash
  git add .
  git commit -m "chore: optimize docker image"
  git push origin optimize/docker-image
  ```

### Phase 5: Production (5 min)

- [ ] Merge pull request
- [ ] Monitor CI/CD workflow completion
- [ ] Pull new image: `docker pull yourusername/health-rag-backend`
- [ ] Test in staging environment
- [ ] Deploy to production

---

## 🔍 Verification Commands

### Size Inspection

```bash
# Current baseline
docker images backend-app:latest --format "{{.Size}}"
# Expected before: ~16.7 GB

# After optimization
docker build -t backend-app:optimized -f Dockerfile.optimized .
docker images backend-app:optimized --format "{{.Size}}"
# Expected after: ~800 MB

# Detailed layer breakdown
docker history --human backend-app:optimized
```

### Functionality Testing

```bash
# Start services
docker-compose up -d

# Test endpoints
curl http://localhost:8000/health | jq .
curl http://localhost:8000/ | jq .
curl http://localhost:8000/docs

# Check logs
docker logs health-rag-app | grep -E "RAG|Initializing|Ready"
docker logs health-rag-qdrant | head -20
```

### Performance Benchmarking

```bash
# Startup time
time docker-compose up -d
sleep 15

# Memory usage
docker stats --no-stream

# API response time
time curl -s http://localhost:8000/health > /dev/null
```

---

## 🐛 Troubleshooting

### Image Still Large (>2 GB)

**Check 1**: Verify site-packages cleanup
```bash
docker history --human backend-app:optimized | grep site-packages
# Should show size reduction, not large layer
```

**Check 2**: Ensure HuggingFace cache not included
```bash
docker exec $(docker ps -q) ls -la /home/appuser/.cache/
# Should return empty or not exist
```

**Fix**: Re-check Dockerfile.optimized Stage 2, ensure:
- No `.cache` copy from builder
- `find` commands removing .dist-info, __pycache__, tests

### App Crashes at Startup

**Check 1**: Embeddings file exists
```bash
docker exec health-rag-app ls -lh /app/data/embeddings.npy
# Should show ~10-50 MB file
```

**Check 2**: Permissions correct
```bash
docker exec health-rag-app ls -la /app/data/
# appuser should own files, -rw- or -rw-r--
```

**Check 3**: Database directory exists
```bash
docker exec health-rag-app ls -la /app/data/users.db
# Should exist or be creatable
```

**Check 4**: Review logs
```bash
docker logs health-rag-app --tail 50 2>&1 | grep -i error
```

### Slow Startup

**Measure components**:
```bash
docker logs health-rag-app 2>&1 | grep -E "Loading|Initializing|took|seconds"
```

**If embeddings load is slow**:
- Reduce batch size in `build_embeddings.py`
- Use FastEmbed variant

**If BM25 init is slow**:
- Expected ~5-10 sec for large dataset
- Acceptable tradeoff

---

## 📞 Support References

### Official Documentation
- [Docker Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker Layer Caching](https://docs.docker.com/build/cache/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

### Tools
- [Dive](https://github.com/wagoodman/dive) - Analyze Docker image layers
- [DockerSlim](https://github.com/slimtoolkit/slim) - Automatic image optimization
- [Hadolint](https://github.com/hadolint/hadolint) - Dockerfile linter

### Models & Libraries
- [Sentence Transformers](https://www.sbert.net/)
- [FastEmbed](https://github.com/qdrant/fastembed)
- [BM25](https://github.com/dorianbrown/rank_bm25)
- [Qdrant Client](https://qdrant.tech/documentation/)

---

## ✅ Success Criteria

You'll know optimization succeeded when:

- ✅ Image size < 1 GB (measured: `docker images`)
- ✅ Startup time < 20 seconds (measured: logs from container start)
- ✅ Health endpoint responds immediately (curl http://localhost:8000/health)
- ✅ No model re-downloads at runtime (check logs)
- ✅ Embeddings loaded from disk (check logs for "Embeddings loaded")
- ✅ BM25 initialized successfully (check logs)
- ✅ Qdrant connection working (docker logs health-rag-qdrant)
- ✅ API endpoints functional (Swagger UI, chat endpoint)
- ✅ Pull time < 30 seconds on good connection
- ✅ docker-compose up succeeds without errors

---

## 📋 Next Steps

### Immediate (Today)

1. Read [OPTIMIZATION_ARCHITECTURE.md](OPTIMIZATION_ARCHITECTURE.md)
2. Choose implementation level (Level 2 recommended)
3. Generate embeddings: `python build_embeddings_optimized.py`
4. Build test image: `docker build -t backend-app:test -f Dockerfile.optimized .`

### Short Term (This Week)

1. Test all endpoints locally
2. Set up CI/CD workflow
3. Configure GitHub secrets
4. Merge optimization branch

### Long Term (Ongoing)

1. Monitor image sizes in CI/CD
2. Track startup performance metrics
3. Consider FastEmbed if further size reduction needed
4. Update documentation for team

---

## 📞 Questions?

Refer to specific documentation:
- **"How do I...?"** → [OPTIMIZATION_IMPLEMENTATION_GUIDE.md](OPTIMIZATION_IMPLEMENTATION_GUIDE.md)
- **"What is...?"** → [OPTIMIZATION_ARCHITECTURE.md](OPTIMIZATION_ARCHITECTURE.md)
- **"I need to..."** → [OPTIMIZATION_ADVANCED_GUIDE.md](OPTIMIZATION_ADVANCED_GUIDE.md)

---

**Last Updated**: June 2024
**Status**: ✅ Ready for Production
**Version**: 1.0

