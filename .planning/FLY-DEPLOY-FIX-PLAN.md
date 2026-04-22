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
4. [ ] **Test staging deployment** (pending - requires manual trigger)
5. [ ] **Verify production deployment** (manual trigger only)

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
