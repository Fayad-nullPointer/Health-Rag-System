# 🐳 Docker & Deployment Guide

This directory contains everything needed to run the Health RAG System using Docker and GitHub Actions.

## 📋 Quick Reference

| Feature | File | Purpose |
|---------|------|---------|
| **Production Image** | `Dockerfile` | Multi-stage build with cached models |
| **Production Compose** | `docker-compose.yml` | Production setup (FastAPI + Qdrant) |
| **Dev Compose** | `docker-compose.dev.yml` | Development setup with auto-reload |
| **CI/CD Build Cache** | `.github/workflows/build-cache.yml` | Builds & caches transformers model |
| **Deployment** | `.github/workflows/deploy.yml` | Deploys using cached image |
| **Reusable Workflow** | `.github/workflows/reusable-docker-build.yml` | Template for other workflows |

## 🚀 Getting Started

### Option 1: Automated Setup (Recommended)

```bash
# Linux/macOS
cd Backend
bash quickstart.sh

# Windows (PowerShell)
cd Backend
.\quickstart.ps1
```

### Option 2: Manual Setup

```bash
cd Backend

# Copy environment template
cp .env.example .env

# Build images
docker-compose build

# Start services
docker-compose up -d

# Check status
curl http://localhost:8000/health
```

## 🎯 Key Features

### ✅ Optimized Caching
- **Transformers Model**: Pre-downloaded during build (500MB)
- **Python Dependencies**: Cached as Docker layers
- **GitHub Actions Cache**: Shared across all builds
- **Local Volumes**: Persistent cache for development

### ✅ Production Ready
- Non-root user for security
- Health checks enabled
- Multi-stage builds for minimal size
- Resource limits configured
- Automatic restarts

### ✅ Fast Startup
- **First Build**: 5-10 minutes (includes model download)
- **Subsequent Builds**: < 2 minutes (uses cache)
- **App Startup**: 30-40 seconds (models already cached)

## 📚 Documentation

Detailed information is available in:
- **[DOCKER_SETUP.md](./DOCKER_SETUP.md)** - Complete guide covering:
  - Docker architecture explanation
  - Caching strategy details
  - GitHub Actions workflows
  - Troubleshooting
  - Performance optimization
  - Best practices

## 🔄 GitHub Actions Workflows

### Build & Cache (build-cache.yml)
Automatically triggered on:
- Push to main/develop
- Changes to Dockerfile, dependencies, or app code
- Weekly schedule (refresh cache)
- Manual trigger

**What it does:**
1. Builds Docker image with cached layers
2. Pre-downloads transformers model
3. Pushes to GitHub Container Registry
4. Caches embeddings.npy artifact

### Deploy (deploy.yml)
Triggered after successful build

**What it does:**
1. Downloads cached embeddings
2. Pulls pre-built image
3. Verifies image integrity
4. Ready for deployment

## 📦 Services

### FastAPI Application
- **Port**: 8000
- **Health**: `http://localhost:8000/health`
- **Docs**: `http://localhost:8000/docs`
- **Database**: Connected to Qdrant

### Qdrant Vector Database
- **Port**: 6333 (REST), 6334 (gRPC)
- **Dashboard**: `http://localhost:6333/dashboard`
- **Storage**: Persistent volume

## 🛠️ Common Commands

```bash
# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Execute command in container
docker-compose exec app python -m pytest

# Check disk usage
docker system df

# View resource usage
docker stats
```

## 🔍 Caching Strategy

### How It Works

1. **GitHub Actions Build Cache**
   ```
   Push code → Trigger build-cache.yml → 
   → Build with cache layers → Push to registry
   ```

2. **Docker Layer Caching**
   ```
   Stage 1: System deps → Python deps → Download model
   Stage 2: Lightweight runtime ← Copy cached model
   ```

3. **Local Development**
   ```
   Docker volume persists HuggingFace cache →
   → No re-download on container restart
   ```

### Cache Locations

| Cache | Location | Size | TTL |
|-------|----------|------|-----|
| Python packages | Builder layer | ~300MB | Until pyproject.toml changes |
| Transformers model | `/build/.cache/huggingface` | ~500MB | Until image rebuilt |
| Embeddings | `./data/embeddings.npy` | ~500MB | 30 days (artifact) |
| Qdrant DB | Docker volume | Variable | Persistent |

## 🚨 Troubleshooting

### Slow First Build
**Solution**: First build includes model download. Use cached image on subsequent runs.

### Model Not Cached
**Solution**: Check GitHub Actions workflow passed. Re-run to populate cache.

### Out of Disk Space
```bash
docker volume prune      # Remove unused volumes
docker system prune      # Clean up everything
docker image prune       # Remove unused images
```

### Port Already in Use
Edit `.env` or docker-compose to use different ports:
```yaml
ports:
  - "8001:8000"  # Use 8001 instead of 8000
```

## 📈 Performance Metrics

| Operation | Time | Notes |
|-----------|------|-------|
| First build | 5-10 min | Includes model download |
| Cached build | < 2 min | Reuses layers |
| App startup | 30-40 s | Models already loaded |
| RAG init | 30-60 s | Background thread |

## 🔐 Security

- ✅ Non-root user (UID 1000)
- ✅ Read-only config mounts
- ✅ Health checks enabled
- ✅ Resource limits
- ✅ HTTPS ready (via reverse proxy)

## 📋 Environment Variables

See [.env.example](./.env.example) for all available options:
- API Keys (Groq, OpenAI, Google, Cohere)
- JWT Configuration
- Database Settings
- Logging Configuration
- CORS Settings

## 🔗 Related Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

## ✨ Next Steps

1. **Run locally**: Use quickstart script or manual setup
2. **Configure**: Edit .env with your API keys
3. **Test**: Visit http://localhost:8000/docs
4. **Deploy**: Push to GitHub and use CI/CD workflows

---

**Questions?** See [DOCKER_SETUP.md](./DOCKER_SETUP.md) for comprehensive documentation.
