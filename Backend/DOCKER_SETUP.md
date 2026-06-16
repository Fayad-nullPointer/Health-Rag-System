# Docker & Caching Setup Guide

This document explains the Docker configuration, caching strategy, and GitHub Actions workflows for the Health RAG System.

## Table of Contents

- [Docker Setup](#docker-setup)
- [Docker Compose](#docker-compose)
- [Caching Strategy](#caching-strategy)
- [GitHub Actions Workflows](#github-actions-workflows)
- [Running Locally](#running-locally)
- [Production Deployment](#production-deployment)

## Docker Setup

### Dockerfile Architecture

The `Dockerfile` uses a **multi-stage build** to optimize image size and startup time:

#### Stage 1: Builder
- Installs system dependencies
- Installs Python dependencies
- **Pre-downloads transformers model** (BAAI/bge-m3) during build
- Model cache is placed in `/build/.cache/huggingface`

**Why this matters:**
- Model download (~500MB) happens during build, not at runtime
- Application starts immediately without waiting for model download
- Cache is reused from GitHub Actions build cache

#### Stage 2: Runtime
- Lightweight Python 3.11 slim image
- Copies pre-cached models from builder stage
- Runs as non-root user (security)
- Health checks enabled

### Key Features

```dockerfile
# Pre-download transformers model
RUN python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('BAAI/bge-m3')"

# Copy cached models from builder (super fast!)
COPY --from=builder --chown=appuser:appuser /build/.cache /home/appuser/.cache
```

## Docker Compose

### Production Compose (`docker-compose.yml`)

Services:
- **app**: FastAPI application (8000)
- **qdrant**: Vector database (6333)

Volume management:
- `huggingface_cache`: Persists transformers models across restarts
- `qdrant_storage`: Persists vector database
- `qdrant_snapshots`: Backup snapshots

### Development Compose (`docker-compose.dev.yml`)

Enhanced for development:
- Auto-reload enabled with `--reload` flag
- Volume mounts for live code editing
- Debug logging enabled
- Same services as production

## Caching Strategy

### 1. GitHub Actions Build Cache

**Workflow: `.github/workflows/build-cache.yml`**

The workflow automatically:
1. ✅ Caches all build layers (Python dependencies)
2. ✅ Pre-downloads transformers model during build
3. ✅ Pushes image to GitHub Container Registry (GHCR)
4. ✅ Caches embeddings.npy for quick restoration

**Cache Scope:**
- `health-rag-backend`: Shared across all builds
- Automatically reused by all subsequent builds
- Uploaded as artifacts for deployment

**Triggers:**
- Push to `main` or `develop` branches
- Changes to Dockerfile, dependencies, or app code
- Weekly schedule (for regular refresh)
- Manual trigger via `workflow_dispatch`

### 2. Docker Layer Caching

Build stages cache at each layer:
```
Stage 1 (Builder):
  └─ apt-get install       [cached]
  └─ pip install           [cached from GHA]
  └─ Download model        [cached in GHA]

Stage 2 (Runtime):
  └─ Lightweight image     [minimal layers]
  └─ Copy cache from builder [fast copy]
```

### 3. Local Development Cache

- `huggingface_cache` volume persists across container restarts
- No need to re-download models locally
- Embeddings loaded from `./data/embeddings.npy`

### 4. CI/CD Cache Invalidation

Cache is automatically invalidated when:
- `pyproject.toml` changes (new dependencies)
- `Dockerfile` changes
- App code changes (new model requirements)

Manual invalidation:
- GitHub Actions UI: "Clear all caches"
- Or re-run workflow with cache clear

## GitHub Actions Workflows

### 1. Build Cache Workflow (`build-cache.yml`)

**Purpose:** Build Docker image with cached transformers model

**Steps:**
1. Checkout code
2. Setup Docker Buildx
3. Build with GHA cache (reads from previous builds)
4. Push image to GHCR
5. Upload embeddings artifact
6. Verify image layers

**Outputs:**
- Docker image pushed to: `ghcr.io/<owner>/health-rag-backend:<tag>`
- Embeddings cached as artifact
- Build cache stored in GitHub Actions

### 2. Deploy Workflow (`deploy.yml`)

**Purpose:** Deploy using cached image and artifacts

**Triggers:**
- Workflow completion of `build-cache.yml` on main branch
- Manual trigger

**Steps:**
1. Download cached embeddings artifact
2. Pull pre-built image from registry
3. Verify image integrity
4. Ready for deployment

### 3. Reusable Workflow (`reusable-docker-build.yml`)

**Purpose:** Template for other workflows to use

**Usage:**
```yaml
jobs:
  build-with-cache:
    uses: ./.github/workflows/reusable-docker-build.yml@main
    with:
      context: ./Backend
      dockerfile: ./Backend/Dockerfile
      image-name: ghcr.io/owner/health-rag-backend
      push: true
```

## Running Locally

### Prerequisites

- Docker Desktop or Docker + Docker Compose
- 4GB+ RAM
- 20GB+ disk space (for models and volumes)

### Quick Start

```bash
# Navigate to Backend directory
cd Backend

# Production mode
docker-compose up -d

# Or development mode with auto-reload
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

### First Run

First build will:
1. Download and cache transformers model (~500MB)
2. Build image (~1.5GB)
3. Start Qdrant vector database
4. Start FastAPI application

**Expected startup time:**
- First build: 5-10 minutes (includes model download)
- Subsequent builds: <2 minutes (uses cache)
- App startup: 30-40 seconds

### Testing Application

```bash
# Health check
curl http://localhost:8000/health

# API docs (Swagger UI)
http://localhost:8000/docs

# ReDoc documentation
http://localhost:8000/redoc

# Qdrant console
http://localhost:6333/dashboard

# Check model cache
docker exec health-rag-app-dev du -sh /home/appuser/.cache/huggingface
```

## Production Deployment

### Docker Hub / GHCR Registry

The cached image is automatically pushed to GitHub Container Registry:

```bash
# Pull cached image
docker pull ghcr.io/your-org/health-rag-backend:latest

# Or with specific version
docker pull ghcr.io/your-org/health-rag-backend:v1.0.0

# Run with Compose
docker-compose up -d
```

### Environment Variables

Create `.env` file:

```env
# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_API_KEY=your-api-key-here

# Application
LOG_LEVEL=info

# Other configs
DATABASE_URL=postgresql://user:pass@db:5432/health_rag
```

### Volumes

For production, use named volumes with backups:

```yaml
volumes:
  qdrant_storage:
    driver: local
    driver_opts:
      type: nfs
      o: addr=nfs.example.com,vers=4,soft,timeo=180,bg,tcp,rw
      device: ":/export/qdrant"
```

### Resource Limits

Recommended resource allocation:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
  qdrant:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 8G
```

### Monitoring

Add health checks and logging:

```bash
# Check application health
docker-compose exec app curl -f http://localhost:8000/health

# View application logs
docker-compose logs -f app --tail=50

# Check resource usage
docker stats
```

## Troubleshooting

### Model Not Cached

**Symptom:** Slow startup on first run

**Solution:**
1. Check GitHub Actions workflow passed
2. Verify cache in GitHub Actions settings
3. Re-run build workflow to populate cache

### Cache Miss

**Symptom:** Build takes longer than expected

**Trigger re-cache:**
```bash
# Manual rebuild (clears local cache)
docker-compose build --no-cache app
```

### Out of Disk Space

Models and volumes can consume significant space:

```bash
# Check space usage
docker system df

# Clean up unused volumes
docker volume prune

# Remove specific volume
docker volume rm health-rag-system_huggingface_cache
```

### Port Conflicts

Default ports:
- 8000: FastAPI
- 6333: Qdrant

Change in `.env` or compose file:

```yaml
services:
  app:
    ports:
      - "8001:8000"  # Map to 8001 instead
```

## Performance Optimization

### Build Time Optimization

```bash
# Use Docker buildx with multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 .

# Monitor build cache hit rate
export BUILDKIT_PROGRESS=plain
docker-compose build app
```

### Runtime Optimization

1. **Model Caching:** Already optimized via pre-download
2. **Volume Mounting:** Use `-v` for bind mounts (dev) or named volumes (prod)
3. **Network:** Use bridge network for inter-container communication

## Best Practices

✅ **Do:**
- Use multi-stage builds to minimize image size
- Cache dependencies at the top layers
- Pre-download models during build
- Use non-root users for security
- Enable health checks
- Use `.dockerignore` to exclude unnecessary files

❌ **Don't:**
- Install dependencies at runtime
- Download models in ENTRYPOINT
- Use `latest` tag in production
- Mount sensitive configs read-write
- Skip health checks

## References

- [Docker Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [GitHub Actions Caching](https://docs.docker.com/build/ci/github-actions/cache/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
