# Continue Portkit Smoke Test Verification

## Current Status
- **Production**: 15/15 PASSED (100%) ✅
- **Staging**: 15/15 PASSED (100%) ✅

## What's Been Done
1. ✅ Fixed PYTHONPATH in worker process config (`/app/backend/src` instead of `/app/backend`)
2. ✅ Fixed staging Redis URL (using Upstash instead of non-existent internal DNS)
3. ✅ Both worker machines running on production and staging

## Task
Run the smoke tests on both environments to verify systems are still operational:

```bash
cd /var/tmp/vibe-kanban/worktrees/0e0c-portkit-smoke-te/portkit
python3 scripts/beta_smoke_test.py --env production
python3 scripts/beta_smoke_test.py --env staging
```

If tests fail, investigate:
1. Check worker status: `fly machine list -a portkit-backend` and `fly machine list -a portkit-backend-staging`
2. Check worker logs: `fly logs -a portkit-backend --machine <machine-id> -n`
3. Check Redis connectivity in worker logs

## Previous Root Causes (for reference)
- **PYTHONPATH**: Workers couldn't find `services` module due to missing `/src` in path
- **Redis**: Staging used wrong DNS (`staging-redis.internal` instead of Upstash URL)

## Configuration Files
- `fly.toml` - Contains worker process definition with PYTHONPATH
- Worker machines use Celery to process conversion jobs from Redis queue