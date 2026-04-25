## Continue Portkit Smoke Test Investigation

### What Was Fixed
- Fixed HTTP 500 error on `GET /api/v1/conversions` endpoint by adding defensive error handling in `backend/src/main.py:1107`
- Smoke test now passes 15/15 consistently on production

### Verified Working
- All authentication endpoints (register, login, email verification, Discord OAuth, password reset)
- File upload and conversion pipeline (upload → start → progress → completion → download)
- Conversion History endpoint (with rate limit retry logic)
- Billing endpoints (Stripe checkout, free tier limit)
- Error handling (invalid file type, no file)

### Remaining Items to Investigate (if any)
1. **Rate Limiting**: The `/api/v1/conversions` endpoint has aggressive rate limits (10 req/min, 100/hr). Consider whether this is appropriate for authenticated users vs. anonymous users.
2. **Test Reliability**: The smoke test sometimes hits rate limits on consecutive runs. The current retry logic handles this, but consider if rate limits should be per-user instead of per-IP for authenticated requests.

### Quick Verification Command
```bash
cd /var/tmp/vibe-kanban/worktrees/0e0c-portkit-smoke-te/portkit && python3 scripts/beta_smoke_test.py --env production
```

### Task for Next Session
If smoke tests pass consistently (15/15), the task is complete. If any failures occur:
1. Check the production logs: `fly logs -a portkit-backend`
2. Run the test again to see if it's transient
3. Investigate the specific failure