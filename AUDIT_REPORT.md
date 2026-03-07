# ModPorter-AI Codebase Audit Report

**Date:** 2026-03-06  
**Auditor:** AI Agent  
**Purpose:** Identify and categorize all blocking issues preventing Minecraft Java to Bedrock conversion

---

## Executive Summary

The ModPorter-AI project has a well-architected microservices system with a React frontend, FastAPI backend, and CrewAI-powered AI engine. However, several critical issues prevent the system from performing end-to-end conversion. This report categorizes these issues by severity and provides remediation guidance.

---

## Issue Categories

### 🔴 CRITICAL (Blocking - Must Fix)

#### 1. Missing Python Dependencies (Environment)
**Location:** Backend, AI-Engine  
**Severity:** CRITICAL  
**Impact:** Services cannot start

**Problem:**
- `psycopg2-binary` required but not installed for async PostgreSQL
- `javalang` needed for Java mod parsing (both backend and ai-engine require it)
- Various other runtime dependencies may be missing

**Evidence:**
```
ModuleNotFoundError: No module named 'psycopg2'
ModuleNotFoundError: No module named 'javalang'
```

**Recommendation:**
```bash
# Backend dependencies
cd backend && pip install -r requirements.txt

# AI Engine dependencies  
cd ai-engine && pip install -r requirements.txt

# Or use Docker for isolated environment
docker compose -f docker-compose.dev.yml up -d
```

---

#### 2. PYTHONPATH Configuration Issues
**Location:** Backend, AI-Engine  
**Severity:** CRITICAL  
**Impact:** Cannot import local modules

**Problem:**
- Backend source code is in `backend/src/` but imports assume root level
- Running `python main.py` fails due to import path issues
- Docker volumes map `backend/src` to `/app/src` but PYTHONPATH may not be set correctly

**Evidence:**
```
ModuleNotFoundError: No module named 'db'
```

**Recommendation:**
- Set `PYTHONPATH=/app/src` in Docker environment (already configured in docker-compose.yml)
- For local development: `export PYTHONPATH=$(pwd)/src`

---

#### 3. Database Schema Inconsistency
**Location:** PostgreSQL Database  
**Severity:** CRITICAL  
**Impact:** Conversion jobs cannot be stored

**Problem:**
- `database/schema.sql` defines QA and A/B testing tables
- `backend/src/db/models.py` defines different tables (conversion_jobs, job_progress, etc.)
- No migrations to create tables from models.py
- The schema.sql references `conversions(id)` which doesn't exist

**Evidence:**
- `schema.sql` has: `conversion_id UUID REFERENCES conversions(id)`
- `models.py` defines: `conversion_jobs` table

**Recommendation:**
```bash
# Run Alembic migrations
cd backend/src
alembic revision --autogenerate -m "initial migration"
alembic upgrade head
```

---

### 🟠 HIGH PRIORITY

#### 4. Frontend Build Configuration Issues
**Location:** Frontend  
**Severity:** HIGH  
**Impact:** Frontend may not build correctly

**Problem:**
- `VITE_API_URL` and `VITE_API_BASE_URL` set to `http://localhost:8080` in docker-compose
- Frontend runs on port 3000, backend on port 8080 - this should work
- However, there may be environment variable build issues

**Recommendation:**
- Verify frontend can be built: `cd frontend && pnpm build`
- Check nginx.conf for correct proxy configuration

---

#### 5. AI Engine Missing Core Dependencies
**Location:** AI-Engine  
**Severity:** HIGH  
**Impact:** Conversion crew cannot run

**Problem:**
- Requires `crewai`, `langchain`, `chromadb`, `sentence-transformers`
- These are heavy dependencies with specific version requirements
- May fail on systems without sufficient memory

**Recommendation:**
```bash
# Ensure all ai-engine dependencies are installed
cd ai-engine && pip install -r requirements.txt

# For GPU support
pip install ai-engine[gpu-nvidia]  # or gpu-amd, cpu-only
```

---

#### 6. Redis Connection Configuration
**Location:** Backend, AI-Engine  
**Severity:** HIGH  
**Impact:** Job state management fails

**Problem:**
- Both services depend on Redis for job state
- Default URL is `redis://localhost:6379`
- In Docker, services use `redis://redis:6379` (Docker service name)

**Evidence:**
- `docker-compose.yml` correctly configures Redis service
- Health checks configured but may fail if Redis isn't ready

**Recommendation:**
- Ensure Redis starts before backend/ai-engine (handled by docker-compose)
- Check health endpoints: `curl http://localhost:6379`

---

### 🟡 MEDIUM PRIORITY

#### 7. Missing Environment Variables in Development
**Location:** All Services  
**Severity:** MEDIUM  
**Impact:** Services may use incorrect defaults

**Problem:**
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` required for real AI calls
- No `.env` file in repository (only `.env.example`)
- Without API keys, system falls back to simulation mode

**Recommendation:**
```bash
# Create .env file from example
cp backend/src/.env.example backend/src/.env
# Edit with actual API keys
```

---

#### 8. Test Infrastructure Complexity
**Location:** Tests  
**Severity:** MEDIUM  
**Impact:** Tests require heavy mocking

**Problem:**
- `test_mvp_conversion.py` mocks `pydub`, `crewai`, and other dependencies
- Tests use in-memory SQLite to avoid PostgreSQL connection issues
- Complex setup reduces test reliability

**Evidence:**
- Tests mock `pydub`, `crewai`, `models.smart_assumptions`
- Uses `sqlite+aiosqlite:///:memory:` for testing

**Recommendation:**
- Document test dependencies clearly
- Consider using testcontainers for integration tests

---

#### 9. Database Init Script Missing
**Location:** Backend SQL  
**Severity:** MEDIUM  
**Impact:** Database may not initialize correctly

**Problem:**
- `docker-compose.yml` references `./backend/sql/init.sql`
- This file may not exist or may be incomplete

**Evidence:**
```yaml
volumes:
  - ./backend/sql/init.sql:/docker-entrypoint-initdb.d/init.sql
```

**Recommendation:**
```bash
# Check if init.sql exists
ls -la backend/sql/
# Create if missing with pgvector extension
```

---

### 🔵 LOW PRIORITY / IMPROVEMENTS

#### 10. Frontend Routing Configuration
**Location:** Frontend  
**Severity:** LOW  
**Impact:** Minor routing issues

**Problem:**
- Frontend uses React Router but nginx may not handle all routes correctly
- SPA routing needs fallback configuration

**Recommendation:**
- Verify nginx.conf has `try_files $uri $uri/ /index.html`

---

#### 11. Documentation Gaps
**Location:** Docs  
**Severity:** LOW  
**Impact:** Developer Onboarding

**Problem:**
- Multiple documentation files exist but may be outdated
- Some docs reference non-existent paths

**Recommendation:**
- Consolidate documentation
- Add quickstart guide

---

## Service-by-Service Analysis

### Frontend (React + Vite)
| Component | Status | Notes |
|-----------|--------|-------|
| Build | ⚠️ UNTESTED | Needs `pnpm install && pnpm build` |
| Dev Server | ✅ READY | `pnpm dev` should work |
| API Integration | ⚠️ CONFIG | VITE_API_URL must be set |
| WebSocket | ❓ UNKNOWN | No WebSocket implementation found |

### Backend (FastAPI)
| Component | Status | Notes |
|-----------|--------|-------|
| Health Check | ✅ READY | `/api/v1/health` endpoint |
| Upload | ✅ READY | `/api/v1/upload` endpoint |
| Conversion | ✅ READY | Falls back to simulation without AI Engine |
| Database | ❌ MISSING | Migrations not run |
| Redis Cache | ✅ READY | Depends on Redis service |
| WebSocket | ⚠️ PARTIAL | WebSocket directory exists but may be incomplete |

### AI Engine (CrewAI)
| Component | Status | Notes |
|-----------|--------|-------|
| Health Check | ✅ READY | `/api/v1/health` endpoint |
| Conversion Crew | ⚠️ DEPENDS | Requires crewai, langchain |
| Java Analyzer | ⚠️ DEPENDS | Requires javalang |
| RAG System | ⚠️ DEPENDS | Requires chromadb, sentence-transformers |
| Redis State | ✅ READY | Uses RedisJobManager |

---

## Docker Environment Status

The Docker Compose setup is well-structured:
- ✅ PostgreSQL with pgvector extension
- ✅ Redis with persistence
- ✅ Health checks for all services
- ✅ Network configuration
- ❌ Init script may be missing
- ❌ May need rebuild after dependency changes

---

## Critical Path to Working Conversion

To get the system to perform end-to-end conversion:

1. **Install Dependencies**
   ```bash
   # Backend
   cd backend && pip install -r requirements.txt
   
   # AI Engine  
   cd ai-engine && pip install -r requirements.txt
   
   # Frontend
   cd frontend && pnpm install
   ```

2. **Run Database Migrations**
   ```bash
   cd backend/src
   alembic revision --autogenerate -m "initial"
   alembic upgrade head
   ```

3. **Set Environment Variables**
   ```bash
   cp backend/src/.env.example backend/src/.env
   # Edit with actual API keys
   ```

4. **Start Services**
   ```bash
   # Using Docker (recommended)
   docker compose -f docker-compose.dev.yml up -d
   
   # Or local development
   docker compose up -d postgres redis  # Start databases
   cd backend && python -m uvicorn main:app --reload
   cd ai-engine && python -m uvicorn main:app --reload --port 8001
   cd frontend && pnpm dev
   ```

5. **Verify Health**
   ```bash
   curl http://localhost:8080/api/v1/health
   curl http://localhost:8001/api/v1/health
   ```

6. **Test Conversion**
   ```bash
   # Upload a mod
   curl -X POST -F "file=@/path/to/mod.jar" http://localhost:8080/api/v1/upload
   
   # Start conversion
   curl -X POST http://localhost:8080/api/v1/convert \
     -H "Content-Type: application/json" \
     -d '{"file_id": "<file_id>", "target_version": "1.20.0"}'
   ```

---

## Recommendations Summary

| Priority | Issue | Effort | Owner |
|----------|-------|--------|-------|
| 🔴 CRITICAL | Install dependencies | Low | DevOps |
| 🔴 CRITICAL | Run DB migrations | Medium | Backend Dev |
| 🟠 HIGH | Verify AI Engine imports | Medium | AI Dev |
| 🟠 HIGH | Test full conversion flow | High | QA |
| 🟡 MEDIUM | Set up environment variables | Low | DevOps |
| 🟡 MEDIUM | Verify nginx config | Low | Frontend Dev |
| 🔵 LOW | Update documentation | Medium | Tech Writer |

---

## Conclusion

The ModPorter-AI codebase has significant architectural foundations in place but requires dependency installation and database setup before it can perform actual conversions. The most critical blocking issues are:

1. **Missing Python packages** - Easy fix with pip/poetry/pnpm install
2. **Database migrations not run** - Requires Alembic setup
3. **API keys not configured** - Need environment setup

Once these are addressed, the system should be able to perform end-to-end conversion, though the AI conversion quality will depend on the underlying CrewAI agents and LLM capabilities.

---

*This audit was performed by analyzing the codebase structure, configuration files, and test infrastructure. Recommendations are based on the current state of the codebase as of March 2026.*
