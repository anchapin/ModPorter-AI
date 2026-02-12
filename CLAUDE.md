# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ModPorter AI is an AI-powered tool that converts Minecraft Java Edition mods to Bedrock Edition add-ons using a multi-agent AI system. The project uses a microservices architecture with CrewAI for agent orchestration and RAG (Retrieval Augmented Generation) for knowledge enhancement.

## Architecture

### Services

```
┌─────────────┐    ┌──────────┐    ┌────────────┐    ┌───────────┐
│  Frontend   │───▶│ Backend  │───▶│ AI Engine │    │ PostgreSQL │
│  (React)    │    │(FastAPI) │    │ (CrewAI)  │    │           │
│  Port 3000  │    │Port 8080 │    │ Port 8001  │    │  Port 5433 │
└─────────────┘    └──────────┘    └────────────┘    └───────────┘
                                                 ▲
                                                 │
                                        ┌──────────┴──────────┐
                                        │  Redis  │           │
                                        │ Port 6379│           │
                                        └────────────────────┘
```

### Service Responsibilities

**Frontend** (`frontend/`): React 19 + TypeScript + Vite
- User interface for mod upload, progress tracking, and reports
- Served by Nginx in production, Vite dev server in development
- Port 3000 (external) → 80 (container)

**Backend** (`backend/`): FastAPI + SQLAlchemy + AsyncPG
- API orchestration, file handling, database operations
- Manages PostgreSQL with pgvector for RAG embeddings storage
- Communicates with AI Engine for conversions (30-minute timeout)
- Port 8080

**AI Engine** (`ai-engine/`): CrewAI + LangChain + FastAPI
- Multi-agent conversion system with 6+ specialized agents
- RAG system for knowledge retrieval (document embeddings, semantic search)
- Supports GPU acceleration (NVIDIA/AMD/CPU-only options)
- Port 8001

## Development Commands

### Prerequisites
- Node.js 22+ (for frontend Vite 7.2.2+)
- Python 3.9+ (backend/ai-engine)
- Docker & Docker Compose (recommended)
- pnpm 7+

### Docker Development (Recommended)

```bash
# Development with hot reload (use this!)
docker compose -f docker compose.dev.yml up -d

# Production deployment
docker compose up -d

# View logs
docker compose logs [service-name]
docker compose logs -f  # Follow all logs

# Rebuild after changes
docker compose -f docker compose.dev.yml up -d --build

# Stop all services
docker compose -f docker compose.dev.yml down

# Service URLs:
# Frontend: http://localhost:3000
# Backend:  http://localhost:8080
# AI Engine: http://localhost:8001
# Database: localhost:5433
# Redis: localhost:6379
```

### Local Development (Without Docker)

```bash
# Install dependencies
pnpm install && cd frontend && pnpm install

# Start all services
pnpm run dev                # Both frontend + backend
pnpm run dev:frontend       # Frontend only (port 3000)
pnpm run dev:backend        # Backend only (port 8000)

# Note: Requires PostgreSQL, Redis running separately
# Set DATABASE_URL and REDIS_URL in .env
```

### Testing

```bash
# All tests
pnpm run test

# Frontend tests (Vitest + Testing Library)
cd frontend && pnpm test
pnpm test:coverage
pnpm test:watch

# Backend tests (pytest with async support)
cd backend && python -m pytest
pytest tests/unit/
pytest tests/integration/ --cov=src

# AI Engine tests
cd ai-engine && pytest
pytest tests/test_rag_crew.py

# End-to-end tests
pnpm run test:e2e

# Test database management
./scripts/test-db.sh start
./scripts/test-db.sh reset
./scripts/test-db.sh stop
```

### Code Quality

```bash
# All services
pnpm run lint && pnpm run format

# Frontend only
cd frontend && pnpm run lint    # ESLint strict mode

# Backend/AI Engine only
cd backend && python -m ruff check src/
python -m black src/ tests/  # Format
python -m ruff check --fix src/  # Auto-fix
```

### Build & Deploy

```bash
# Frontend build
pnpm run build:frontend
# Output: frontend/dist/

# Backend/AI Engine (Python packages)
cd backend && python -m build
# Or: pip install -e .
```

## Code Architecture

### AI Agent System

The AI Engine uses a multi-agent CrewAI system. Agents work in sequence:

1. **JavaAnalyzerAgent** (`ai-engine/agents/java_analyzer.py`): Analyzes Java mod structure using `javalang`
2. **BedrockArchitectAgent** (`ai-engine/agents/bedrock_architect.py`): Designs Bedrock conversion strategy
3. **LogicTranslatorAgent** (`ai-engine/agents/logic_translator.py`): Converts Java logic to JavaScript
4. **AssetConverterAgent** (`ai-engine/agents/asset_converter.py`): Handles texture/model/sound conversion
5. **PackagingAgent** (`ai-engine/agents/packaging_agent.py`): Assembles final .mcaddon
6. **QAValidatorAgent** (`ai-engine/agents/qa_validator.py`): Validates conversion quality

**Key Integration**: `ai-engine/crew/conversion_crew.py` orchestrates the workflow.

### Database Pattern (Async SQLAlchemy)

All database operations use async/await patterns:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

async def get_conversion(db: AsyncSession, conversion_id: str):
    result = await db.execute(
        select(Conversion).where(Conversion.id == conversion_id)
    )
    return result.scalar_one_or_none()
```

**Models**: `backend/src/db/models.py` defines SQLAlchemy models with pgvector VECTOR(1536) type for embeddings.

**Migrations**: Alembic in `backend/src/db/migrations/`. Create new migration:
```bash
cd backend && alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Backend API Structure

Modular routers in `backend/src/api/`:
- `embeddings.py`: RAG document indexing/search (POST `/api/v1/embeddings/`, `/api/v1/embeddings/search/`)
- `validation.py`: Conversion validation endpoints
- `comparison.py`: Java vs Bedrock comparison
- `behavioral_testing.py`: Behavioral test orchestration
- `assets.py`: Add-on asset management

**Key middleware**: CORS, health checks, structured error responses via `pydantic`.

### Frontend Component Structure

Components organized by feature in `frontend/src/components/`:
- `ConversionUpload/`: Mod file upload with drag-drop
- `ConversionProgress/`: Real-time WebSocket progress tracking
- `ConversionReport/`: Detailed conversion results with assumptions
- `BehaviorEditor/`: Visual editor for behavior files (blocks, recipes, loot tables)
- `ComparisonView/`: Side-by-side Java vs Bedrock comparison
- `QAReport/`: Quality assurance validation display

**Routing**: `frontend/src/main.tsx` defines React Router routes.

### RAG System

**Backend** (`backend/src/api/embeddings.py`):
- Stores document embeddings in PostgreSQL with pgvector
- Vector dimension: 1536 (OpenAI `text-embedding-ada-002` compatible)
- Deduplication via MD5 `content_hash`

**AI Engine** (`ai-engine/search/`, `ai-engine/engines/`):
- `VectorDBClient`: HTTP client to backend embeddings API
- `SearchTool`: CrewAI tool for semantic search
- `KnowledgeBaseAgent`: RAG-enabled agent for knowledge retrieval

**Limitations**: Currently uses placeholder/dummy embeddings. Actual embedding generation is TODO.

## Environment Variables

### Required

```bash
# AI API Keys (for production LLM calls)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/modporter

# Redis (caching, sessions, job state)
REDIS_URL=redis://redis:6379

# Frontend build args
VITE_API_URL=http://localhost:8080/api/v1
VITE_API_BASE_URL=http://localhost:8080
```

### Optional

```bash
# Local LLM development (no API costs)
USE_OLLAMA=true
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434  # Auto-detected if not set

# Docker environment detection
DOCKER_ENVIRONMENT=true  # Changes Ollama URL to http://ollama:11434

# RAG Configuration
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_SIMILARITY_THRESHOLD=0.7
RAG_MAX_RESULTS=10

# Testing
TESTING=true              # Skip DB initialization
USE_MOCK_LLM=false      # Mock LLM for tests
TEST_LLM_PROVIDER=mock   # Test environment
MAX_CONVERSION_TIME=1800  # 30 minutes for rate-limited scenarios
```

## Key Patterns

### Backend → AI Engine Communication

```python
# Long-running conversions with extended timeout
AI_ENGINE_TIMEOUT = httpx.Timeout(1800.0)  # 30 minutes
async with httpx.AsyncClient(timeout=AI_ENGINE_TIMEOUT) as client:
    response = await client.post(f"{AI_ENGINE_URL}/api/v1/convert", files=files)
```

### Frontend → Backend API

```typescript
// Uses Nginx proxy in production
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';
// Direct access also available: http://localhost:8080/api/v1
```

### Mock LLM for Testing

```python
# In tests, avoid API costs
if os.getenv("USE_MOCK_LLM", "false").lower() == "true":
    from tests.mocks.mock_llm import MockLLM
    self.llm = MockLLM(responses=["mock response"])
```

### Health Checks

All services expose health endpoints:
- Frontend: `GET /` → Nginx status
- Backend: `GET /api/v1/health`
- AI Engine: `GET /api/v1/health`

Check in Docker: `docker compose ps` shows health status.

## CI/CD Optimization

The project uses pre-built base images for 60-70% faster CI builds:

**Base images**: `docker/base-images/` contain heavy ML dependencies (sentence-transformers, chromadb, crewai)
**Optimized Dockerfiles**: `*/Dockerfile.optimized` use base images
**Cache strategy**: Dependency hash-based (`python-hash`, `node-hash`)

See `.github/workflows/ci-optimized.yml` for implementation.

## GPU Support

AI Engine supports GPU acceleration:

```bash
# NVIDIA (CUDA)
pip install ai-engine[gpu-nvidia]

# AMD (ROCm on Linux, DirectML on Windows)
pip install ai-engine[gpu-amd]

# CPU-only (for testing/development)
pip install ai-engine[cpu-only]
```

Detection: `ai-engine/utils/gpu_config.py` auto-detects available GPU.

## Common Issues

### Port Conflicts
Default ports: 3000 (frontend), 8080 (backend), 8001 (ai-engine), 5433 (postgres), 6379 (redis).
Modify in `docker-compose.yml` if conflicts exist.

### Database Connection Failures
- Check PostgreSQL container is healthy: `docker compose logs postgres`
- Verify `DATABASE_URL` format: `postgresql+asyncpg://...`
- Ensure `pgvector` extension is enabled (in Docker image)

### AI Engine Timeouts
- Conversions can take 30+ minutes for complex mods
- Frontend uses WebSocket for real-time progress updates
- Backend uses 30-minute timeout for AI Engine calls

### Ollama Connection Issues
```bash
# Test Ollama directly
curl http://localhost:11434/api/tags

# Check model availability
ollama list

# Pull model if missing
ollama pull llama3.2
```

### CI Build Failures
- **Base image not found**: Ensure GitHub Container Registry permissions
- **Docker user permissions**: Use `--user root` for CI containers
- **Cache not invalidating**: Update hashes in `ci-optimized.yml` when dependencies change

## Important Notes

- **Always use `docker compose.dev.yml` for development** - contains hot-reload configuration
- **Never use just `docker compose build`** - it uses production config
- **Frontend environment variables** are build args in Docker, embedded at build time
- **AI agents use singleton pattern** - call `Agent.get_instance()` instead of instantiating
- **All DB operations must be async** - use `await db.execute()` not `db.scalar()`
- **Test isolation** - Use `aiosqlite` for in-memory async SQLite in tests
