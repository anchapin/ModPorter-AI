# Fly.io Deployment Fix Plan

**Date:** 2026-04-22
**Status:** ✅ COMPLETED

---

## Issues Identified

### 1. Cache Export Error (CRITICAL)
**Error:** `Cache export is not supported for the docker driver.`
**Location:** `.github/workflows/fly-deploy.yml` lines 71-72

```
cache-from: type=gha
cache-to: type=gha,mode=max
```

**Root Cause:** The default Docker Buildx driver doesn't support cache export to GitHub Actions cache.

**Impact:** All deployments fail at the Docker build stage.

---

### 2. Deployment Architecture Issue (HIGH)
**Current Flow:**
1. Build Docker image → Push to Docker Hub
2. Deploy to Fly.io using `flyctl-actions`

**Problem:** Fly.io deployment doesn't use the pushed Docker Hub image. The `flyctl deploy` command triggers its own build from source code.

**Impact:** Unnecessary extra build step; Docker Hub push is wasted effort.

---

### 3. Fly.io Action Version (FIXED)
**Previous:** `superfly/flyctl-actions@v1.5` (doesn't exist)
**Fixed:** `superfly/flyctl-actions@master`

---

## Fix Plan

### Phase 1: Fix Cache Export Issue (Immediate)

#### Option A: Set up Buildx Builder with docker-container Driver
Add a builder setup step before the build:

```yaml
- name: Set up Buildx builder
  run: |
    docker buildx create --name fly-builder --driver docker-container --use
    docker buildx inspect --bootstrap
```

#### Option B: Remove Cache Export (Simpler)
Remove `cache-to: type=gha,mode=max` line, keep `cache-from: type=gha`.

**Recommendation:** Option B for now (cache-from works, cache-to is optional for CI builds).

---

### Phase 2: Simplify Deployment Architecture (Recommended)

**New Approach:** Let Fly.io handle the build directly

```yaml
- name: Deploy to Fly.io
  uses: superfly/flyctl-actions@master
  with:
    app: ${{ matrix.app_name }}
    command: deploy
    args: "--remote-only --detach --nowait"
```

Remove the Docker build/push step entirely. Fly.io's remote builder:
- Builds from Dockerfile.fly automatically
- Uses its own cache layer system
- Deploys directly to the app

---

### Phase 3: Add Environment-Specific Configuration

Ensure environment variables are properly passed to Fly.io deployment:

- Staging: `portkit-backend-staging` app
- Production: `portkit-backend` app

Update `fly.toml` or use `--env` flags to set:
- `VITE_API_URL`
- `VITE_API_BASE_URL`
- Database connection strings
- API keys

---

## Implementation Steps

1. [x] **Remove cache-to configuration** from workflow
2. [x] **Remove Docker build/push step** entirely
3. [x] **Simplify flyctl deploy command** to let Fly.io handle builds
4. [x] **Update flyctl action to new API format** (use `args` instead of `app`/`command`)
5. [x] **Remove invalid flags** (`--nowait` not supported)
6. [x] **Fix langchain dependency** — Changed `langchain` to `langchain-core`
7. [ ] **Verify FLY_API_TOKEN secret** — User reports secret is added but still gets "unauthorized"

**Workflow Fixes: COMPLETE ✅**
- Cache export removed
- Docker build step removed  
- Action API format updated
- Invalid flags removed
- Dependency conflict resolved

**Remaining Blocker:**
The FLY_API_TOKEN secret exists but returns "unauthorized". The token needs to be regenerated and re-added.

---

## Files to Modify

| File | Changes |
|------|---------|
| `.github/workflows/fly-deploy.yml` | Remove Docker build step, cache-to config |
| `fly.toml` | Ensure environment variables are configured |
| `.planning/FLY-DEPLOY-FIX-PLAN.md` | Mark complete when done |

---

## Success Criteria

- [ ] Workflow builds and pushes Docker image successfully
- [ ] Fly.io deployment completes without errors
- [ ] Health check passes on both staging and production
- [ ] Smoke tests pass

---

## Notes

- Fly.io's remote builder is faster than building locally in GitHub Actions
- Using `--remote-only` ensures Fly.io builds in their optimized infrastructure
- Cache from GitHub Actions is useful but not critical for the deployment speed

---

## Rollback Plan

If the simplified approach fails:
1. Restore Docker build/push step
2. Keep Option A (Buildx builder setup) for cache support
3. Revert to original deployment command

---

## Additional Issues Found (Post-Implementation)

### 4. Missing FLY_API_TOKEN Secret (BLOCKING)
**Error:** `Error: unauthorized (Request ID: 01KPV1SQ9WFYNSZEQ4XY07THYQ-ord)`
**Impact:** Staging deployment cannot authenticate with Fly.io

**Fix Required:** Add `FLY_API_TOKEN` secret to GitHub repository settings
1. Get token: `flyctl auth token`
2. Add to: GitHub Settings → Secrets and variables → Actions → New repository secret

---

### 5. Python Dependency Conflict (BLOCKING)
**Error:** `Cannot install -r /tmp/ai-engine-requirements.txt (line 9) and langchain<1.0.0 and >=0.3.0 because these package versions have conflicting dependencies.`
**Impact:** Production build fails during pip install

**Root Cause:** Conflicting langchain version constraints in `ai-engine/requirements.txt`

**Fix Required:** Resolve version constraints in `ai-engine/requirements.txt`
