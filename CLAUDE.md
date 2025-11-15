# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Docker Development (Recommended)
```bash
# Start all services with hot reload
docker compose -f docker compose.dev.yml up -d

# Production build
docker compose up -d --build

# View logs
docker compose logs [service-name]

# Access container shells
docker compose exec backend bash
docker compose exec ai-engine bash
docker compose exec frontend sh
```

### Advanced Development Commands
```bash
# Performance & Monitoring
python scripts/performance-analysis.py
python scripts/optimize-conversion-engine.py

# Database operations
./scripts/test-db.sh start|stop|reset|logs
./scripts/postgres-backup.sh
./scripts/ssl-setup.sh

# System benchmarking
python scripts/benchmark_graph_db.py

# CI/CD automation
./scripts/deploy.sh
./scripts/fly-startup.sh
```

### Local Development (Without Docker)
```bash
# Install all dependencies
pnpm run install-all

# Start development servers
pnpm run dev

# Individual services
pnpm run dev:frontend    # Frontend on :3000
pnpm run dev:backend     # Backend on :8000
cd ai-engine && python -m uvicorn main:app --reload --port 8001  # AI Engine on :8001
```

### Testing Commands
```bash
# All tests with coverage
pnpm run test

# Individual service tests
pnpm run test:frontend   # Vitest + React Testing Library
pnpm run test:backend    # Pytest with coverage (80%+ required)
cd ai-engine && pytest   # AI Engine tests

# Docker-based testing
docker compose exec backend pytest --cov=src --cov-report=html
docker compose exec ai-engine pytest --cov=src

# Coverage analysis
./backend/analyze_coverage.py
./run_automated_confidence_tests.py
./find_missing_tests.py

# Test database management
./scripts/test-db.sh start|stop|reset|logs
```

### Code Quality
```bash
# Linting
pnpm run lint
pnpm run lint:frontend   # ESLint + TypeScript
pnpm run lint:backend    # Ruff

# Formatting
pnpm run format
pnpm run format:backend  # Black + Ruff --fix
```

## Architecture Overview

ModPorter-AI is a microservices system for converting Minecraft Java mods to Bedrock add-ons using AI.

### Core Services
- **Frontend**: React 19 + TypeScript + Vite (Port 3000)
- **Backend**: FastAPI + SQLAlchemy + AsyncPG (Port 8000)
- **AI Engine**: CrewAI + LangChain for conversion logic (Port 8001)
- **PostgreSQL**: Primary database with pgvector for vector search (Port 5432)
- **Neo4j**: Graph database for knowledge representation (Ports 7474/7687)
- **Redis**: Caching and session management (Port 6379)

### Key Technologies
- **AI/ML**: CrewAI agents, OpenAI/Anthropic LLMs, RAG systems
- **Frontend**: Material-UI, React Query, Monaco Editor, Playwright
- **Backend**: FastAPI, async/await patterns, comprehensive testing
- **Infrastructure**: Docker, NGINX, GitHub Actions CI/CD

### Service Communication
- Frontend ↔ Backend: REST API via `/api/v1/` endpoints
- Backend ↔ AI Engine: REST API for conversion tasks
- All services: Shared PostgreSQL/Redis/Neo4j access

## Code Organization

### Backend (`backend/src/`)
- `api/`: FastAPI routers (assets, knowledge_graph, conversion_inference, etc.)
- `db/`: Database models, CRUD operations, connection management
- `services/`: Business logic (asset conversion, confidence scoring, caching)
- `main.py`: FastAPI application entry point

### AI Engine (`ai-engine/`)
- `agents/`: CrewAI agents (java_analyzer, expert_knowledge, advanced_rag)
- `crew/`: CrewAI workflow definitions
- `search/`: Hybrid search with reranking capabilities
- `main.py`: FastAPI service entry point

### Frontend (`frontend/src/`)
- `components/`: UI components (FileUpload, ConversionProgress, CodeEditor)
- `pages/`: Route-level components
- `services/`: API client functions
- `utils/`: Helper functions and utilities

## Database Schema
- **PostgreSQL**: Jobs, Addons, Assets, Users, conversion metadata
- **Neo4j**: Knowledge graphs for conversion patterns and expertise
- **Redis**: Job state caching, rate limiting, session data

## Testing Requirements
- **80%+ test coverage mandatory** (enforced in CI/CD)
- **275+ test files** across all components
- **Pytest** for backend with async support
- **Vitest** for frontend with React Testing Library
- **Playwright** for E2E testing

## Environment Variables
Required in `.env`:
```bash
# AI API Keys
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Database (auto-configured for Docker)
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/modporter
NEO4J_URI=bolt://neo4j:7687
REDIS_URL=redis://redis:6379
```

## Key API Endpoints
- `POST /api/v1/convert` - Start mod conversion
- `GET /api/v1/convert/{job_id}/status` - Check conversion status
- `POST /api/v1/knowledge-graph/query` - Query knowledge graph
- `GET /api/v1/assets/{asset_id}` - Retrieve converted assets

## AI Agent Architecture

### Conversion Pipeline Agents
- **JavaAnalyzerAgent**: Analyzes Java mod structure and dependencies
- **ExpertKnowledgeAgent**: Leverages knowledge graph for conversion patterns
- **AdvancedRAGAgent**: Enhanced retrieval-augmented generation
- **AssetConverterAgent**: Handles Minecraft asset format conversion
- **ValidationAgent**: Validates converted add-ons
- **PackagingAgent**: Creates final .mcaddon packages

### CrewAI Workflow Structure
- **Main Conversion Crew**: Orchestrates the entire conversion process
- **Knowledge Crew**: Manages knowledge graph queries and updates
- **Validation Crew**: Ensures quality and compatibility
- **Testing Crew**: Runs automated validation tests

### Knowledge Graph Architecture
- **Neo4j Schema**: Nodes for mods, blocks, entities, behaviors
- **Vector Integration**: PostgreSQL + pgvector for semantic search
- **Relationship Types**: Inheritance, dependency, conversion patterns
- **Caching Strategy**: Redis for frequently accessed patterns

## Code Patterns & Conventions

### Python Backend Patterns
- **Async First**: All async endpoints with proper exception handling
- **Database**: AsyncSessionLocal for database operations
- **Caching**: Redis with async client for session management
- **Error Handling**: Custom HTTPException with detailed error messages
- **Validation**: Pydantic models with Field validation

### API Design Patterns
- **Versioning**: All endpoints under `/api/v1/`
- **Response Format**: Consistent JSON structure with status_code, message, data
- **Rate Limiting**: Redis-based rate limiting for endpoints

### Docker Patterns
- **Multi-stage builds**: Optimized for production
- **Health checks**: All services have health monitoring
- **Environment**: Development vs production configurations

## Debugging & Troubleshooting

### Service Debugging
```bash
# Backend debugging
curl http://localhost:8000/api/v1/health
docker compose logs backend --tail 50
python -m pdb backend/src/main.py

# AI Engine debugging
curl http://localhost:8001/api/v1/health
docker compose logs ai-engine --tail 50

# Frontend debugging
npm run dev -- --host 0.0.0.0
npm run test:ui
npm run test:e2e:debug
```

### Database Debugging
```bash
# PostgreSQL
docker compose exec postgres psql -U postgres -d modporter
docker compose exec postgres psql -U postgres -d modporter -c "SELECT * FROM jobs LIMIT 10;"

# Neo4j
docker compose exec neo4j cypher-shell -u neo4j -p password
docker compose exec neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN n LIMIT 10;"

# Redis
docker compose exec redis redis-cli
docker compose exec redis redis-cli "KEYS *"
```

### Performance Troubleshooting
```bash
# Container performance
docker compose stats
docker compose top backend

# API performance
curl -w "Time: %{time_total}s\nSize: %{size_download} bytes\n" http://localhost:8000/api/v1/convert
```

## File Structure & Patterns

### Key Configuration Files
- `backend/src/config.py`: Environment-based settings management
- `backend/.env.example`: Environment variable template
- `backend/alembic.ini`: Database migration configuration
- `ai-engine/.env`: AI service configuration

### Test Organization
- **Backend**: `backend/tests/` with conftest.py fixtures
- **Frontend**: `frontend/src/__tests__/` with component tests
- **Integration**: `backend/tests/integration/` for cross-service tests
- **Performance**: `backend/tests/performance/` for benchmarking

### Logging Patterns
- **Structured JSON logging** for all services
- **Environment-based log levels** (DEBUG, INFO, ERROR)
- **File logging** with rotation for production

## Development Notes
- All services run in Docker containers with health checks
- Hot reload available in development mode (`docker compose.dev.yml`)
- Comprehensive logging with structured JSON format
- Async/await patterns throughout Python codebase
- TypeScript strict mode enabled in frontend
- Vector search capabilities via pgvector extension

## Health Checks
```bash
curl http://localhost:3000/health      # Frontend
curl http://localhost:8000/api/v1/health  # Backend
curl http://localhost:8001/api/v1/health  # AI Engine
docker compose ps                      # All service status
```

## Database Configuration
- **Production**: PostgreSQL with connection pooling
- **Testing**: SQLite with aiosqlite (auto-configured)
- **Migration Support**: Alembic for schema management
- **Vector Search**: PostgreSQL + pgvector for semantic similarity
- **Graph Database**: Neo4j for knowledge representation