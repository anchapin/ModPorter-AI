# Next Session: Complete Auth Fix & Staging Deployment

## Current Status (2026-04-24)

**Production (portkit-backend.fly.dev):**
- ✅ Auth endpoints FIXED and verified
- ✅ Commits: d03a8d95, a69a9f1b, 48a03e8f, 9da2ee8c
- ⚠️ Some smoke tests still failing (rate limiting, conversion issues)

**Staging (portkit-backend-staging.fly.dev):**
- ✅ Auth endpoints FIXED and verified (2026-04-24)
- ✅ Deployed with correct uvicorn entry point: `uvicorn src.main:app`
- ✅ Feature flags enabled: `FEATURE_FLAG_USER_ACCOUNTS=true`, `FEATURE_FLAG_API_KEYS=true`
- ✅ Auto-verify enabled: `SKIP_EMAIL_VERIFICATION=true`
- ✅ Secrets deployed: SECRET_KEY, JWT_SECRET_KEY, REDIS_URL

## Completed Tasks (2026-04-24)

### 1. Staging Deployment Fixed
- Deployed with `fly deploy --app portkit-backend-staging --remote-only`
- Updated to version 44 with correct `src.main:app` entry point

### 2. Secrets Added to Staging
- `FEATURE_FLAG_USER_ACCOUNTS=true`
- `FEATURE_FLAG_API_KEYS=true`
- `SKIP_EMAIL_VERIFICATION=true`
- `SECRET_KEY` (generated)
- `JWT_SECRET_KEY` (generated)
- `REDIS_URL=redis://staging-redis.internal:6379`

### 3. Auth Endpoints Verified
```bash
# Register works - returns user_id
curl -X POST https://portkit-backend-staging.fly.dev/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"staging-test@example.com","password":"TestPass123!"}'
# Response: {"message":"User registered. Account verified automatically (test mode).","user_id":"..."}

# Login works - returns tokens
curl -X POST https://portkit-backend-staging.fly.dev/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"staging-test@example.com","password":"TestPass123!"}'
# Response: {"access_token":"...","refresh_token":"...","token_type":"bearer"}
```

## Priority Tasks

### 1. Investigate Remaining Smoke Test Failures
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
