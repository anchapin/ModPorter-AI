# Repository Guidelines

portkit is an AI-powered Java to Bedrock Minecraft mod converter.

## Project Structure & Module Organization

```
backend/src/
├── api/              # FastAPI endpoints
├── services/         # Business logic, conversion pipelines, background workers
├── models/           # Pydantic models
├── db/               # Database models, CRUD, connections
├── security/          # File security, rate limiting, resource limits
└── tests/
    ├── unit/         # Test modules per feature
    └── integration/  # E2E workflows
frontend/src/
├── api/             # API client functions
├── components/       # React components
├── pages/           # Route pages
└── services/        # Frontend business logic
ai-engine/           # Multi-agent conversion system (separate service)
```

Docker services: frontend, backend, postgres, redis, ai-engine, clamav, jaeger, prometheus.

## Build, Test, and Development Commands

```bash
# Development
pnpm run dev                    # Start both frontend (3000) and backend (8080)
pnpm run dev:frontend          # Frontend only (Next.js + Vite)
pnpm run dev:backend           # Backend only (uvicorn --reload)

# Docker
docker compose up -d           # Production mode
docker compose -f docker-compose.dev.yml up -d  # Development with hot reload

# Testing
pnpm run test                 # All tests
pnpm run test:backend         # pytest on backend
cd backend && python3 -m pytest src/tests/unit/ -q --tb=no  # Fast unit tests
cd backend && python3 -m pytest src/tests/unit/ -v  # Verbose output

# Code Quality
pnpm run lint                 # Check all
pnpm run format               # Format all (ruff format, prettier)
pnpm run format:backend       # Ruff format + lint --fix
```

## Coding Style & Naming Conventions

**Python (Backend)**
- **Linter/Formatter**: ruff (line-length: 100, target: py311)
- **Enabled rules**: E, F, W, I, Q, N, D, UP, C901, SIM, T20
- **Async first**: All I/O operations must be async (`async def`, `async with`)
- **Pydantic V2**: Use `model_config = ConfigDict(from_attributes=True)`
- **Dependency injection**: Use `Depends(get_db)` for shared resources
- **Type hints**: Required on all function signatures
- **Forbidden**: `time.sleep()`, `requests.get()`, `json.loads()`, global state

**Test Naming**: `test_<feature>_<scenario>_<expected>`

**Test Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.real_service` (requires USE_REAL_SERVICES=1), `@pytest.mark.asyncio`

## Testing Guidelines

**Framework**: pytest with pytest-asyncio

**Coverage**: 80%+ required for PR merges

**Test Database**: Use `./scripts/test-db.sh {start|stop|reset}`

**Run single test**: `pytest path/to/test_file.py::TestClass::test_method -v`

## Commit & Pull Request Guidelines

**Commit Format**: `<type>(<scope>): <description>`

Types: `feat|fix|docs|style|refactor|test|chore|ci`
Scopes: `api|backend|ai-engine|tests|docs|ci|frontend`

**Branch Naming**: `feature/<ticket>-<desc>` or `bugfix/<ticket>-<desc>`

**PR Checklist**:
- Tests pass (`pytest src/tests/unit/ -q`)
- Coverage maintained/improved
- No linting errors (`ruff check`)
- PR description explains WHY, not just WHAT

**Pre-commit**: ruff format, ruff lint, Bandit security scan, Gitleaks secrets detection
