# ModPorter AI - AI Coding Agent Instructions

## 🎯 Project Overview
ModPorter AI is a **multi-agent AI system** that converts Minecraft Java Edition mods to Bedrock Edition add-ons using CrewAI, RAG (Retrieval Augmented Generation), and smart assumptions to bridge technical gaps.

## 🏗️ Architecture (3-Service + Multi-Agent Pattern)

### Service Structure
- **Frontend**: React+TypeScript+Vite (port 3000) - User interface for mod uploads and conversion tracking
- **Backend**: FastAPI+SQLAlchemy+AsyncPG (port 8080) - API orchestration, file handling, database operations
- **AI Engine**: CrewAI+LangChain+FastAPI (port 8001) - Multi-agent conversion system with 6 specialized agents
- **Infrastructure**: PostgreSQL (5433) + Redis (6379) + Docker orchestration

### AI Agent System (Core Innovation)
The conversion uses **6 specialized AI agents** working in sequence:
1. `JavaAnalyzerAgent` - Analyzes mod structure and features
2. `BedrockArchitectAgent` - Designs conversion strategy with smart assumptions  
3. `LogicTranslatorAgent` - Converts Java code to Bedrock JavaScript
4. `AssetConverterAgent` - Converts textures/models/sounds
5. `PackagingAgent` - Assembles final .mcaddon files
6. `QAValidatorAgent` - Validates conversion quality

**Key Files**: `ai-engine/src/crew/conversion_crew.py`, `ai-engine/src/agents/`

## 🚀 Development Workflow

### Essential Commands
```bash
# Start all services (uses Docker Compose)
docker-compose up -d

# Development with hot reload
docker-compose -f docker-compose.dev.yml up -d

# Frontend only (when backend is running)
cd frontend && pnpm run dev

# Backend only (with venv)
cd backend && source .venv/bin/activate && python -m uvicorn src.main:app --reload --port 8000

# Run tests (multi-service pattern)
npm run test                    # All services
npm run test:frontend          # Vitest + React Testing Library
npm run test:backend           # pytest with async support
cd ai-engine && pytest        # AI agents + RAG system
```

### File Upload & Conversion Flow
1. **Upload**: `/api/v1/upload` endpoint accepts `.jar` files
2. **Conversion**: Backend calls AI Engine `/api/v1/convert` with CrewAI workflow
3. **Progress**: WebSocket updates via `/api/v1/conversion/{id}/progress`
4. **Output**: `.mcaddon` file delivered via `/api/v1/download/{conversion_id}`

## 🔧 Code Patterns & Conventions

### Database (Async SQLAlchemy Pattern)
```python
# Always use async sessions
async def get_conversion(db: AsyncSession, conversion_id: str):
    result = await db.execute(select(Conversion).where(Conversion.id == conversion_id))
    return result.scalar_one_or_none()
```

### API Error Handling (Consistent HTTP Pattern)
```python
# Use structured error responses
raise HTTPException(
    status_code=422, 
    detail={"message": "Invalid file format", "code": "INVALID_FORMAT"}
)
```

### Component Structure (Frontend)
```
frontend/src/components/ComponentName/
├── ComponentName.tsx          # Main component
├── ComponentName.test.tsx     # Vitest tests
├── ComponentName.stories.tsx  # Storybook stories
├── ComponentName.css         # Component styles
└── index.ts                  # Exports
```

### Agent Tool Pattern (AI Engine)
```python
# Each agent has specialized tools
class JavaAnalyzerAgent:
    def get_tools(self):
        return [AnalyzeModStructureTool(), ExtractDependenciesTool()]
```

## 🔄 Inter-Service Communication

### Backend ↔ AI Engine
```python
# Long-running conversions with extended timeouts
AI_ENGINE_TIMEOUT = httpx.Timeout(1800.0)  # 30 minutes
async with httpx.AsyncClient(timeout=AI_ENGINE_TIMEOUT) as client:
    response = await client.post(f"{AI_ENGINE_URL}/api/v1/convert", files=files)
```

### Frontend ↔ Backend  
```typescript
// API client with environment-aware base URL
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';
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
USE_MOCK_LLM=false            # For testing without API keys
MAX_CONVERSION_TIME=1800      # 30 minutes for rate-limited scenarios
CREW_SIZE=6                   # Number of agents in conversion crew
```

### Docker Volume Management
- `conversion-outputs/` - Stores .mcaddon files
- `temp_uploads/` - Temporary .jar file storage  
- `cache/` - Redis and conversion cache

## 🧪 Testing Approach

### RAG System Testing
```bash
# RAG evaluation suite
python ai-engine/src/testing/rag_evaluator.py

# Test specific agent workflows
pytest ai-engine/tests/integration/test_conversion_workflow.py
```

### Component Testing (Frontend)
```bash
# Single component test
cd frontend && npm test -- ConversionUpload.test.tsx

# With coverage
npm run test -- --coverage
```

## ⚠️ Common Issues & Solutions

### "Rate Limiting" in AI Conversions
- CrewAI agents make multiple LLM calls - expect 20+ minute conversions
- Use `AI_ENGINE_TIMEOUT=1800` for production
- Monitor via WebSocket progress updates

### Docker Service Dependencies  
- Always wait for health checks: `depends_on: service: condition: service_healthy`
- PostgreSQL must initialize before backend starts
- AI Engine needs Redis for job state management

### File Path Handling
```python
# Use absolute paths for cross-service file operations
output_path = Path("/app/conversion_outputs") / f"{conversion_id}.mcaddon"
```

## 📁 Key Integration Points

- **Smart Assumptions**: `ai-engine/src/utils/smart_assumption_engine.py` - Core conversion logic
- **Conversion Status**: WebSocket handler in `backend/src/main.py` line ~800  
- **Agent Configuration**: `ai-engine/src/config/rag_agents.yaml` - Agent roles and tools
- **Database Models**: `backend/src/db/models.py` - Conversion, User, Feedback schemas
