# Fly.io Deployment Optimization Guide

## 🎯 Quick Wins (30-60% faster)

### 1. Enable BuildKit Caching

```bash
# Set DOCKER_BUILDKIT=1 for all builds
export DOCKER_BUILDKIT=1

# For Fly.io, update fly.toml:
# fly.toml already uses Dockerfile.fly, but add:
[build]
  dockerfile = "Dockerfile.fly.optimized"
```

### 2. Use Remote Builder with Cache

```bash
# Configure Fly to use remote builder with caching
flyctl config set build_strategy=remote
flyctl config set build_cache_enabled=true

# Or pass flags during deploy
fly deploy --remote-only --build-arg BUILDKIT_INLINE_CACHE=1
```

### 3. Pre-build Frontend Locally

For deployments that only change backend code:

```bash
# Build frontend once locally
cd frontend && pnpm run build

# Skip frontend build in container
# Comment out frontend build stage in Dockerfile
# Or use build arg:
fly deploy --build-arg SKIP_FRONTEND_BUILD=true
```

## 🔧 Intermediate Optimizations (Additional 20-40% faster)

### 4. Optimize Requirements Files

Pin versions to avoid package resolution on every build:

```bash
# Generate pinned requirements
cd backend && pip freeze > requirements.lock.txt
cd ../ai-engine && pip freeze > requirements.lock.txt

# Use lock files in Dockerfile
COPY backend/requirements.lock.txt /tmp/backend-requirements.txt
```

### 5. Use Multi-stage Build Cache

```dockerfile
# Add to fly.toml:
[build]
  dockerfile = "Dockerfile.fly.optimized"
  [build.settings]
    cache_from = ["type=registry,ref=registry.fly.io/portkit-backend:cache"]
    cache_to = ["type=registry,ref=registry.fly.io/portkit-backend:cache,mode=max"]
```

### 6. Parallel Stage Builds

Build frontend and Python deps in parallel:

```dockerfile
# Use BuildKit's parallel execution
# syntax=docker/dockerfile:1.6

# Both stages run in parallel
FROM node:25-alpine AS frontend-builder
# ... frontend build ...

FROM python:3.11-slim AS python-builder
# ... python deps ...
```

## 🚀 Advanced Optimizations (Additional 10-30% faster)

### 7. Layer Caching Strategy

```dockerfile
# Order layers from least to most frequently changed:

# 1. Base image (rarely changes)
FROM debian:bookworm-slim

# 2. System dependencies (rarely changes)
RUN apt-get update && apt-get install -y nginx python3 ...

# 3. Python packages (changes when requirements.txt changes)
COPY --from=python-builder /usr/local/lib/python3.11/site-packages ...

# 4. Application code (changes most frequently)
COPY backend/ /app/backend/
```

### 8. Use .buildignore

Already created at `.buildignore` - reduces build context by excluding:
- Documentation files
- Test fixtures
- Large assets
- Build artifacts

### 9. Optimize NPM/Celery Worker Separation

```toml
# fly.toml - separate worker with caching
[processes]
  app = "/startup.sh"
  worker = "sh -c 'cd /app/backend && PYTHONPATH=/usr/lib/python3.11/site-packages:/app/backend python -m celery -A src.services.celery_config worker --loglevel=info'"

# Cache worker separately
[[services]]
  processes = ["worker"]
  # ... worker-specific config ...
```

## 📊 Expected Speedup Breakdown

| Optimization | Time Saved | Complexity |
|-------------|-----------|------------|
| BuildKit cache mounts | 40-60% | Low |
| Remote builder with cache | 20-30% | Low |
| Pre-build frontend locally | 30-50% | Medium |
| Pin requirements versions | 10-20% | Low |
| Parallel stage builds | 15-25% | Low |
| Layer ordering optimization | 5-15% | Low |
| .buildignore context reduction | 5-10% | Low |

**Combined: 60-80% faster deployments**

## 🔍 Monitoring Build Performance

```bash
# Time your builds
time fly deploy --verbose

# Check build cache hit rate
flyctl config | grep build

# Monitor build logs
flyctl logs --app portkit-backend
```

## 📝 Migration Checklist

- [ ] Test optimized Dockerfile locally
- [ ] Enable BuildKit caching
- [ ] Configure remote builder
- [ ] Update fly.toml to use optimized Dockerfile
- [ ] Verify deployment succeeds
- [ ] Measure performance improvement
- [ ] Roll back if issues occur

## 🚨 Common Issues

### Issue: BuildKit cache not working
```bash
# Ensure DOCKER_BUILDKIT is set
echo "export DOCKER_BUILDKIT=1" >> ~/.bashrc

# Verify BuildKit is active
docker buildx version
```

### Issue: Cache mounting fails
```bash
# Check Docker version (requires 19.03+)
docker --version

# Ensure BuildKit experimental features enabled
export DOCKER_CLI_EXPERIMENTAL=enabled
```

### Issue: Remote builder timeout
```bash
# Increase timeout in fly.toml
[build]
  [build.settings]
    timeout = 3600  # 1 hour for first build
```

## 📚 References

- [Docker BuildKit Documentation](https://docs.docker.com/build/buildkit/)
- [Fly.io Build Optimization](https://fly.io/docs/reference/builders/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/dev-best-practices/)
