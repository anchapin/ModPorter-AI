# Next Session: Run Smoke Tests Against Staging & Production

## Current Status (2026-04-24)

**Production (portkit-backend.fly.dev):**
- ✅ Auth endpoints FIXED and verified
- ✅ Commits: d03a8d95, a69a9f1b, 48a03e8f, 9da2ee8c

**Staging (portkit-backend-staging.fly.dev):**
- ✅ Auth endpoints FIXED and verified (2026-04-24)
- ✅ Deployed with correct uvicorn entry point: `uvicorn src.main:app`
- ✅ Feature flags enabled: `FEATURE_FLAG_USER_ACCOUNTS=true`, `FEATURE_FLAG_API_KEYS=true`
- ✅ Auto-verify enabled: `SKIP_EMAIL_VERIFICATION=true`

## Priority Tasks

### 1. Run Smoke Tests Against Staging
```bash
cd portkit
python3 scripts/beta_smoke_test.py --env staging --verbose
```

### 2. Run Smoke Tests Against Production
```bash
cd portkit
python3 scripts/beta_smoke_test.py --env production --verbose
```

### 3. Compare Results
Compare which tests pass/fail on each environment:
- **Expected to pass on both:** Auth (register, login, email verification, OAuth, password reset)
- **Investigate failures:** File upload, conversion pipeline, billing endpoints, error handling

### 4. Fix Remaining Failures
Based on smoke test results:

**If file upload fails:**
- Check `/api/v1/upload` endpoint is accessible
- Verify multipart form handling
- Check file size limits and allowed types

**If conversion fails:**
- Check AI Engine connectivity
- Verify Redis is running for job queue
- Check conversion job status tracking

**If billing fails:**
- Verify Stripe secrets are configured
- Check billing endpoint authentication requirements
- Ensure billing feature flags are enabled

**If rate limiting errors occur:**
- Check Redis connectivity for rate limiter
- Verify rate limit rules are appropriate for testing

## Commands to Run Immediately

```bash
# 1. Test staging
python3 scripts/beta_smoke_test.py --env staging --verbose

# 2. Test production
python3 scripts/beta_smoke_test.py --env production --verbose

# 3. Compare reports
ls -la scripts/beta_smoke_test_report_*.json | tail -2
```

## Expected Outcomes

- **80%+ pass rate:** Beta ready
- **60-79% pass rate:** Proceed with caution - fix minor issues
- **<60% pass rate:** No-go - critical issues must be resolved

## Key Files

- `scripts/beta_smoke_test.py` - Smoke test script
- `scripts/beta_smoke_test_report_*.json` - Generated reports
- `.planning/NEXT_SESSION_PROMPT.md` - This file
