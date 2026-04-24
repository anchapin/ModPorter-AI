# Next Session: Complete Auth Fix & Staging Deployment

## Current Status (2026-04-23)

**Production (portkit-backend.fly.dev):**
- ✅ Auth endpoints FIXED and verified
- ✅ Commits: d03a8d95, a69a9f1b, 48a03e8f, 9da2ee8c
- ⚠️ Some smoke tests still failing (rate limiting, conversion issues)

**Staging (staging.portkit.cloud):**
- ❌ Status unknown - needs investigation
- Likely has same auth 404 issues as production had

## Priority Tasks

### 1. Verify Staging Server Status
```bash
# Check if staging is alive and has auth endpoints
curl -s https://staging.portkit.cloud/health
curl -s https://staging.portkit.cloud/api/v1/auth/register -X POST -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"TestPass123!"}'
```

### 2. Apply Fixes to Staging
Staging likely needs same fixes as production:
- **fly-startup.sh**: Change `uvicorn main:app` → `uvicorn src.main:app`
- **Remove obsolete** `backend/main.py` (if exists)
- **Fix imports**: `from websocket.*` → `from src.websocket.*` in:
  - `src/api/conversions.py`
  - `src/services/conversion_service.py`
  - `src/main.py`
- **Add test mode**: `SKIP_EMAIL_VERIFICATION=true` secret

### 3. Deploy to Staging
```bash
# Check if staging uses separate deploy
fly deploy --app portkit-staging --remote-only
# OR if it's same app with different config
# Identify staging deployment method
```

### 4. Verify Staging Auth Endpoints
```bash
curl -s https://staging.portkit.cloud/openapi.json | jq '.paths | keys[] | select(contains("auth"))'
python3 scripts/beta_smoke_test.py --env staging
```

### 5. Investigate Remaining Smoke Test Failures
After auth is working on both environments:
- **File upload**: Check `/api/v1/upload` endpoint
- **Conversion pipeline**: Check AI Engine connectivity
- **Billing**: Verify Stripe configuration and auth requirements
- **Error handling**: Check validation error messages

## Key Files Modified This Session

- `scripts/fly-startup.sh` - uvicorn entry point
- `backend/src/main.py` - websocket import
- `backend/src/api/conversions.py` - websocket import
- `backend/src/services/conversion_service.py` - websocket import
- `backend/src/config.py` - added skip_email_verification
- `backend/src/api/auth.py` - auto-verify logic
- `scripts/beta_smoke_test.py` - fixed test email domain and IndexError

## Commands to Run Immediately

```bash
# 1. Check staging health
curl -s https://staging.portkit.cloud/health

# 2. Test auth on staging
curl -s -X POST https://staging.portkit.cloud/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"staging-test@example.com","password":"TestPass123!"}'

# 3. Run smoke test against staging
python3 scripts/beta_smoke_test.py --env staging --verbose

# 4. Check fly apps
fly apps list
```

## Next Steps Checklist

- [ ] Verify staging server exists and is accessible
- [ ] Identify staging deployment method (separate app or same app?)
- [ ] Apply auth fixes to staging if needed
- [ ] Deploy fixes to staging
- [ ] Verify auth endpoints on staging
- [ ] Run full smoke test on staging
- [ ] Compare production vs staging behavior
- [ ] Document any differences
- [ ] Investigate conversion pipeline issues
- [ ] Investigate billing endpoint 403 errors
- [ ] Fix remaining smoke test failures

## Memory Context

Search memory for: "auth endpoint debugging", "auth router registration", "feature flag user_accounts"

Key findings from this session:
- Main issue was wrong `main.py` being loaded (obsolete 31KB vs new 60KB)
- Fix: Change uvicorn to use `src.main:app`
- Side effect: Import paths needed `src.` prefix for websocket modules
- Added `SKIP_EMAIL_VERIFICATION=true` for smoke testing
