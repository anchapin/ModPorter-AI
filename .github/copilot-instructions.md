# ModPorter AI - AI Coding Agent Instructions

## 🎯 Project Overview
ModPorter AI is a **multi-agent AI system** that converts Minecraft Java Edition mods to Bedrock Edition add-ons using CrewAI, RAG (Retrieval Augmented Generation), and smart assumptions to bridge technical gaps.

## 🏗️ Architecture (3-Service + Multi-Agent Pattern)

### Service Structure
- **Frontend**: React+TypeScript+Vite+pnpm (port 3000) - Nginx-served UI with proxy routing
- **Backend**: FastAPI+SQLAlchemy+AsyncPG (port 8080) - API orchestration, file handling, database operations
- **AI Engine**: CrewAI+LangChain+FastAPI (port 8001) - Multi-agent conversion system with 6 specialized agents
- **Infrastructure**: PostgreSQL (5433) + Redis (6379) + Docker orchestration with optimized base images

### AI Agent System (Core Innovation)
The conversion uses **6 specialized AI agents** working in sequence:
1. `JavaAnalyzerAgent` - Analyzes mod structure and features
2. `BedrockArchitectAgent` - Designs conversion strategy with smart assumptions  
3. `LogicTranslatorAgent` - Converts Java code to Bedrock JavaScript
4. `AssetConverterAgent` - Converts textures/models/sounds
5. `PackagingAgent` - Assembles final .mcaddon files
6. `QAValidatorAgent` - Validates conversion quality

**Key Files**: `ai-engine/src/crew/conversion_crew.py`, `ai-engine/src/agents/`, `ai-engine/src/utils/smart_assumption_engine.py`

## 🚀 Development Workflow

### Essential Commands (PNPM Workspace Pattern)
```bash
# Install all dependencies
pnpm install && cd frontend && pnpm install

# Start all services (Docker recommended)
docker-compose up -d                    # Production images
docker-compose -f docker-compose.dev.yml up -d  # Development with hot reload

# Local development (requires services)
npm run dev                             # Both frontend + backend
npm run dev:frontend                    # Frontend only (port 3000)
npm run dev:backend                     # Backend only (port 8000)

# Testing (multi-service pattern)
npm run test                           # All services
npm run test:frontend                  # Vitest + React Testing Library
npm run test:backend                   # pytest with async support
cd ai-engine && pytest tests/         # AI agents + RAG system

# Code quality
npm run lint && npm run format         # All services
npm run lint:frontend                  # ESLint strict mode
npm run lint:backend                   # Ruff + Black
```

### CI/CD Optimization (60-70% Build Time Reduction)
- **Pre-built Base Images**: Heavy ML dependencies (sentence-transformers, chromadb, crewai) pre-installed
- **Smart Cache Keys**: Dependency hash-based invalidation (`python-hash`, `node-hash`)
- **Parallel Test Matrix**: All test suites run simultaneously
- **Optimized vs Standard**: Graceful fallback when base images unavailable

**Key Files**: `.github/workflows/ci-optimized.yml`, `docker/base-images/`, `*/Dockerfile.optimized`

## 🔧 Code Patterns & Conventions

### Database (Async SQLAlchemy + pgvector Pattern)
```python
# Always use async sessions with proper imports
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from pgvector.sqlalchemy import VECTOR  # For embeddings

async def get_conversion(db: AsyncSession, conversion_id: str):
    result = await db.execute(select(Conversion).where(Conversion.id == conversion_id))
    return result.scalar_one_or_none()
```

### Agent Tool Pattern (CrewAI + Singleton)
```python
# Each agent uses singleton pattern with specialized tools
class JavaAnalyzerAgent:
    @classmethod
    def get_instance(cls, llm=None):
        if not hasattr(cls, '_instance'):
            cls._instance = cls(llm)
        return cls._instance
    
    def get_tools(self):
        return [AnalyzeModStructureTool(), ExtractDependenciesTool()]
```

### Error Handling (Structured HTTP + Logging)
```python
# Use structured error responses with proper logging
import logging
logger = logging.getLogger(__name__)

raise HTTPException(
    status_code=422, 
    detail={"message": "Invalid file format", "code": "INVALID_FORMAT"}
)
```

### Import Organization (Critical Pattern)
```python
# Group imports: stdlib, third-party, local
import uuid
from typing import List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from src.db.models import DocumentEmbedding
from src.utils.rate_limiter import create_rate_limited_llm
```

## 🔄 Inter-Service Communication

### Backend ↔ AI Engine (Extended Timeouts)
```python
# Long-running conversions with 30-minute timeouts
AI_ENGINE_TIMEOUT = httpx.Timeout(1800.0)
async with httpx.AsyncClient(timeout=AI_ENGINE_TIMEOUT) as client:
    response = await client.post(f"{AI_ENGINE_URL}/api/v1/convert", files=files)
```

### Frontend ↔ Backend (Nginx Proxy Pattern)
```typescript
// Frontend uses Nginx proxy - access API via /api/ or direct port
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';
// OR proxy route: http://localhost:3000/api/
```

## 🛠️ Configuration & Environment

### Required Environment Variables
```bash
# AI API Keys (required for agents)
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key

# Database & Cache
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/modporter  
REDIS_URL=redis://redis:6379

# AI Engine Specific
USE_MOCK_LLM=false                    # For testing without API keys
TEST_LLM_PROVIDER=mock                # Test environment
MAX_CONVERSION_TIME=1800              # 30 minutes for rate-limited scenarios
```

### Docker Volume Management (Cross-Service)
```yaml
# Shared volumes for file operations
volumes:
  - conversion-outputs:/app/conversion_outputs  # .mcaddon files
  - temp-uploads:/app/temp_uploads              # .jar file staging
  - conversion-cache:/app/cache                 # Redis persistence
```

## 🧪 Testing Approach

### Mock LLM Pattern (CI/Testing)
```python
# Use mock LLM for tests (avoid API costs)
if os.getenv("USE_MOCK_LLM", "false").lower() == "true":
    from tests.mocks.mock_llm import MockLLM
    self.llm = MockLLM(responses=["mock response"])
```

### Test Organization
```bash
# Frontend: Vitest + React Testing Library
cd frontend && pnpm test -- --coverage

# Backend: pytest with async support + alembic migrations
cd backend && python -m pytest --cov=. tests/ --timeout=300

# AI Engine: Unit + Integration splits
cd ai-engine && pytest tests/unit/
cd ai-engine && pytest tests/integration/ --cov=src
```

## ⚠️ Common Issues & Solutions

### CI/CD Optimization Issues
- **Base Image Failures**: Check GitHub Container Registry permissions and lowercase image names
- **Docker User Permissions**: Use `--user root` for CI containers when installing packages
- **Cache Invalidation**: Update dependency hashes when `requirements.txt` or `pnpm-lock.yaml` change

### Docker Service Dependencies
```yaml
# Always wait for health checks
depends_on:
  service:
    condition: service_healthy
```

### Rate Limiting in AI Conversions
- CrewAI agents make 20+ LLM calls per conversion
- Use `AI_ENGINE_TIMEOUT=1800` and WebSocket progress monitoring
- Consider Ollama fallback for development: `USE_OLLAMA=true`

## 📁 Key Integration Points

- **Conversion Orchestration**: `ai-engine/src/crew/conversion_crew.py` - Multi-agent workflow coordination
- **Smart Assumptions Engine**: `ai-engine/src/utils/smart_assumption_engine.py` - Handles Java→Bedrock incompatibilities  
- **RAG System**: `ai-engine/src/engines/` - Vector embeddings + knowledge retrieval
- **API Router Organization**: `backend/src/api/` - Modular endpoint structure (validation, comparison, embeddings)
- **CI Optimization**: `.github/workflows/ci-optimized.yml` - 60-70% faster builds with base images

## Tool Use
 **GitHub logs**: access with GitHub CLI tool (gh)