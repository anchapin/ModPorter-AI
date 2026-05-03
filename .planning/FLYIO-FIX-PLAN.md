# Fly.io Deployment Fix Plan

**Date:** 2026-04-22
**Status:** Draft

---

## Issues Identified

### 1. Critical: No Machines Running
- **Problem:** Both `portkit-backend` and `portkit-backend-staging` have no machines available
- **Evidence:** `flyctl machines list` returns "No machines are available"
- **Impact:** Application is completely offline

### 2. Secrets Not Deployed
- **Problem:** 12 secrets showing "Staged" status but not deployed
- **Evidence:** `fly secrets list` shows "There are 12 secrets not deployed"
- **Impact:** Application cannot access required configuration

### 3. Health Check Mismatch
- **Problem:** Startup script checks `/api/v1/health` but nginx only exposes `/health`
- **Evidence:** `scripts/fly-startup.sh` line 43 checks `localhost:8000/api/v1/health`
- **Impact:** Startup script may fail health checks, causing machine restarts

### 4. CSP Header Domain Mismatch
- **Problem:** CSP header references `portkit.cloud` but fly.io uses `.fly.dev`
- **Evidence:** `nginx-fly.conf` line 50 has hardcoded `portkit.cloud`
- **Impact:** Browser may block connections from fly.io domain

### 5. Auto-Stop Configuration
- **Problem:** `auto_stop_machines = "stop"` causes machines to shut down when idle
- **Evidence:** `fly.toml` line 40
- **Impact:** Machines disappear after inactivity, causing "no machines available"

---

## Fix Plan

### Phase 1: Immediate Fixes (Deploy Now)

#### 1.1 Fix Health Check Endpoints
**File:** `scripts/fly-startup.sh`

Change health check paths:
```diff
- if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
+ if curl -f http://localhost:8000/health > /dev/null 2>&1; then

- if curl -f http://localhost:8001/api/v1/health > /dev/null 2>&1; then
+ if curl -f http://localhost:8001/health > /dev/null 2>&1; then
```

#### 1.2 Update CSP Headers for Fly.io
**File:** `nginx-fly.conf`

Replace hardcoded domain with environment variable:
```diff
- add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://portkit.cloud wss://portkit.cloud;" always;
+ add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' $CSP_CONNECT;" always;
```

#### 1.3 Fix Auto-Stop Configuration
**File:** `fly.toml`

Remove auto-stop to keep machines running:
```diff
  [[services]]
    processes = ["app"]
    internal_port = 80
    protocol = "tcp"
-   auto_stop_machines = "stop"
    auto_start_machines = true
    min_machines_running = 1
```

#### 1.4 Deploy Secrets
```bash
flyctl secrets deploy -a portkit-backend
flyctl secrets deploy -a portkit-backend-staging
```

### Phase 2: Deployment

#### 2.1 Deploy to Staging First
```bash
cd /home/alex/Projects/portkit
flyctl deploy --app portkit-backend-staging --remote-only
```

#### 2.2 Verify Staging
```bash
# Check machines are running
flyctl machines list -a portkit-backend-staging

# Check health
curl -f https://portkit-backend-staging.fly.dev/health

# View logs
flyctl logs -a portkit-backend-staging
```

#### 2.3 Deploy to Production
```bash
flyctl deploy --app portkit-backend --remote-only
```

#### 2.4 Verify Production
```bash
# Check machines are running
flyctl machines list -a portkit-backend

# Check health
curl -f https://portkit-backend.fly.dev/health

# View logs
flyctl logs -a portkit-backend
```

### Phase 3: Post-Deployment Verification

#### 3.1 Health Checks
```bash
# Test main health endpoint
curl https://portkit-backend.fly.dev/health

# Test API endpoints
curl https://portkit-backend.fly.dev/api/v1/health
```

#### 3.2 Monitor Logs
```bash
# Watch logs for errors
flyctl logs -a portkit-backend
```

---

## Rollback Plan

If deployment fails:
```bash
# Revert changes
git checkout HEAD~1 -- scripts/fly-startup.sh nginx-fly.conf fly.toml

# Redeploy
flyctl deploy --app portkit-backend --remote-only
```

---

## Success Criteria

- [ ] Machines are running in both staging and production
- [ ] Health check `/health` returns 200
- [ ] API endpoints are accessible
- [ ] No errors in application logs
- [ ] Secrets are deployed (not staged)
