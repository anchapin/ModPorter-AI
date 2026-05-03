# Fly.io Redeploy Fix Plan

**Date:** 2026-04-22
**Status:** Ready to Implement

---

## Issues Found

### 1. Health Check Endpoint Mismatch
- **Problem:** Startup script checks `/health` but both services expose `/api/v1/health`
- **Evidence:** `backend/src/main.py:315` and `ai-engine/main.py:287` have `/api/v1/health`
- **Impact:** Health checks fail, services restart continuously

### 2. Worker Process Fails - Celery Not Found
- **Problem:** Worker command "No module named celery"
- **Evidence:** Logs show `/usr/local/bin/python: No module named celery`
- **Cause:** PYTHONPATH not set correctly for worker process

### 3. Alembic Configuration Missing
- **Problem:** Migration fails with "No 'script_location' key found"
- **Evidence:** `backend/src/alembic.ini` exists but not copied to container

### 4. Services Not Listening on Expected Ports
- **Problem:** Backend and AI Engine start but don't bind to ports 8000/8001
- **Evidence:** Nginx error "connect() failed (111: Connection refused)"

---

## Fix Plan

### 1. Fix Startup Script Health Checks
**File:** `scripts/fly-startup.sh`

Change health check paths:
```diff
- if curl -f http://localhost:8000/health > /dev/null 2>&1; then
+ if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then

- if curl -f http://localhost:8001/health > /dev/null 2>&1; then
+ if curl -f http://localhost:8001/api/v1/health > /dev/null 2>&1; then
```

### 2. Copy Alembic Configuration
**File:** `Dockerfile.fly`

Add after copying backend:
```diff
# Copy application code
COPY backend/ /app/backend/
COPY ai-engine/ /app/ai-engine/
+ COPY backend/src/alembic.ini /app/backend/alembic.ini
```

### 3. Fix Worker Command with Full PYTHONPATH
**File:** `fly.toml`

Update worker process to include site-packages in PYTHONPATH:
```diff
  worker = "sh -c 'cd /app/backend && PYTHONPATH=/app/backend python -m celery -A src.services.celery_config worker --loglevel=info'"
+ worker = "sh -c 'cd /app/backend && PYTHONPATH=/usr/local/lib/python3.12/site-packages:/app/backend python -m celery -A src.services.celery_config worker --loglevel=info'"
```

### 4. Add Root Health Endpoints for Simpler Monitoring
**Files:** `backend/src/main.py` and `ai-engine/main.py`

Add simple `/health` endpoint that returns 200:

```python
@app.get("/health")
async def simple_health():
    return {"status": "healthy"}
```

---

## Implementation Order

1. Fix `scripts/fly-startup.sh` health check paths
2. Add alembic.ini to Dockerfile.fly
3. Update worker PYTHONPATH in fly.toml
4. Add /health endpoints to both services
5. Deploy to staging and verify
6. Deploy to production

---

## Verification Steps

```bash
# Test health endpoints
curl https://portkit-backend-staging.fly.dev/health
curl https://portkit-backend-staging.fly.dev/api/v1/health

# Check machines
flyctl machines list -a portkit-backend-staging

# Check logs for errors
flyctl logs -a portkit-backend-staging | grep -i error
```
