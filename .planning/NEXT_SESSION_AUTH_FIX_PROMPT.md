# Next Session: Debug Auth Endpoints on Production

## Context

Backend API deployed to production on Fly.io (`portkit-backend.fly.dev`). Health endpoints work, but auth endpoints return 404.

## Completed

- Fixed alembic migration path (`src/db/migrations`)
- Fixed Dockerfile Python packages path (`/usr/local/lib/python3.11/dist-packages`)
- Fixed PYTHONPATH in `fly-startup.sh`
- Fixed migration branching (renamed `0002_add_comparison_tables` → `0007`)
- Ran database migrations successfully (at `0007`)
- Set DATABASE_URL with asyncpg driver: `postgresql+asyncpg://...`
- Set feature flags: `FEATURE_FLAG_USER_ACCOUNTS=true`, `FEATURE_FLAG_API_KEYS=true`

## Current Issue

Auth endpoints return 404. Auth module loads successfully but routes are not registered in FastAPI app.

## Commands to Debug

```bash
# Check if auth routes are in OpenAPI
curl -s https://portkit-backend.fly.dev/openapi.json | jq '.paths | keys[] | select(contains("auth"))'

# SSH into fly machine
flyctl ssh console -a portkit-backend

# Inside machine, test auth import
export PYTHONPATH=/usr/local/lib/python3.11/dist-packages:/app/backend:/app/backend/src
cd /app/backend
python3 -c "from api import auth; print('Auth loaded')"
python3 -c "from main import app; print([r.path for r in app.routes if 'auth' in r.path])"

# Check feature flags
python3 -c "from services.feature_flags import get_feature_flag_manager; mgr = get_feature_flag_manager(); print('user_accounts:', mgr.is_enabled('user_accounts'))"

# Test backend startup manually
cd /app/backend && export PYTHONPATH=/usr/local/lib/python3.11/dist-packages:/app/backend:/app/backend/src && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Files to Check

- `backend/src/main.py` - line 218: `app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])`
- `backend/src/api/auth.py` - check imports and router definition
- `scripts/fly-startup.sh` - verify PYTHONPATH is being set correctly during startup

## Key Questions

1. Is the auth router being included in FastAPI app at startup?
2. Are there any import errors preventing auth module from loading?
3. Are feature flags being loaded before auth router registration?
4. Is PYTHONPATH being set correctly in the actual running process?

## Branch

Current branch: `vk/0e0c-portkit-smoke-te`
