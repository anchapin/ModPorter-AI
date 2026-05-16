# PortKit Project Reference

**Last Updated**: 2026-05-15
**Project Type**: Python/TypeScript Full-Stack AI Application
**Status**: Active Development

---

## Technology Stack

| Layer | Technology | Port | Notes |
|-------|------------|------|-------|
| Frontend | React 18 + TypeScript + Vite | 3000 | SPA, Nginx proxy |
| Backend | FastAPI + SQLAlchemy (async) + Celery | 8080 | Python 3.12+ |
| AI Engine | FastAPI + LangChain/LangGraph | 8001 | Multi-agent orchestration |
| PostgreSQL | PostgreSQL 15 + pgvector | 5433 | Relational + vector storage |
| Redis | Redis 7 | 6379 | Celery broker + session cache |
| ClamAV | Virus scanning | - | File upload security |

---

## Directory Structure

```
portkit/
├── frontend/src/            # React SPA
│   ├── api/               # API client functions
│   ├── components/         # Reusable UI components
│   ├── pages/             # Route-level components
│   ├── hooks/             # Custom React hooks
│   ├── contexts/           # React context providers
│   └── services/           # Frontend business logic
│
├── backend/src/            # FastAPI application
│   ├── api/               # HTTP route handlers (thin)
│   ├── services/          # Business logic
│   ├── models/            # Pydantic schemas
│   ├── db/                # SQLAlchemy ORM + CRUD
│   └── security/          # Upload sandbox, rate limiting
│
├── ai-engine/              # Multi-agent conversion system
│   ├── agents/             # Converter agent implementations
│   │   ├── java_analyzer/ # Tree-sitter AST parsing
│   │   ├── logic_translator/
│   │   ├── texture_converter/
│   │   └── ...
│   ├── orchestration/      # LangGraph pipelines
│   ├── search/             # RAG pipeline
│   └── qa/                 # Quality assurance
│
└── .planning/              # Project documentation
    ├── ROADMAP.md          # Phase-by-phase roadmap
    ├── MILESTONES.md       # Milestone tracking
    └── phases/             # Individual phase plans
```

---

## Key Design Patterns

| Pattern | Implementation | Notes |
|---------|---------------|-------|
| **Async-first** | All backend I/O uses `async def` + `await` | Never use `requests.get()`, `time.sleep()` |
| **Dependency injection** | `Depends(get_db)` for DB sessions | FastAPI pattern |
| **LangChain tools** | `@tool` decorator on converter functions | Each converter is a tool |
| **LangGraph nodes** | Each agent is a graph node with edges | StateGraph orchestration |
| **RAG retrieval** | pgvector + BM25 hybrid search | Cross-encoder reranking |
| **Celery queuing** | Long conversions run async | Redis broker |

---

## API Conventions

**Base URL**: `http://localhost:8080/api/v1/`

**Response Format**:
```json
{
  "data": {...},
  "error": null
}
```

**Error Format**:
```json
{
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  }
}
```

**Status Codes**:
- `200` — Success
- `201` — Created
- `400` — Bad Request (validation error)
- `401` — Unauthorized
- `403` — Forbidden
- `404` — Not Found
- `500` — Internal Server Error

---

## Database Models

**Key Tables**:
- `users` — User accounts with OAuth (Discord/GitHub/Google)
- `conversions` — Conversion job records
- `conversion_results` — Generated Bedrock files
- `patterns` — RAG pattern library
- `feedback` — User corrections for learning

**ORM**: SQLAlchemy async with `from_attributes = True`

---

## AI Agent System

**Conversion Pipeline**:
```
JAR Upload → java_analyzer (Tree-sitter AST)
                        ↓
           ConversionPipeline (LangGraph)
                        ↓
    ┌───────────────────┼───────────────────┐
    ↓           ↓           ↓           ↓
entity_    recipe_    texture_   logic_
converter  converter  converter  translator
    ↓           ↓           ↓           ↓
    └───────────────────┼───────────────────┘
                        ↓
            bedrock_builder → .mcaddon
                        ↓
            QA Pipeline (multi-candidate + logic_auditor)
                        ↓
            ConversionReport → Frontend
```

**Agent Types** (20+ specialized converters):
- `java_analyzer` — Parse Java mod code
- `entity_converter` — Entity behavior + spawn rules
- `recipe_converter` — Crafting/custom recipes
- `texture_converter` — Texture atlas + images
- `model_converter` — 3D model format conversion
- `sound_converter` — Sound definitions
- `bedrock_builder` — Package assembly
- `logic_translator` — Java→Bedrock logic
- `advancement_converter` — Achievements
- `loot_table_generator` — Loot tables
- `reviewer_agent` — QA validation
- `tester_agent` — Test generation
- `semantic_checker` — Behavior equivalence
- `fixer_agent` — Auto-fix issues
- `logic_auditor_agent` — Adversarial testing

---

## Critical "Do Not Touch" Zones

| File/Module | Reason |
|-------------|--------|
| `ai-engine/search/rag_pipeline.py` | LangChain/LangGraph + Minecraft knowledge coupling |
| `ai-engine/knowledge/patterns/` | Domain-specific Java→Bedrock mappings |
| `backend/src/db/models.py` | Core ORM - schema changes need migrations |
| `ai-engine/orchestration/strategy_selector.py` | PortKit-specific orchestration logic |

---

## Development Commands

```bash
# Start all services (production)
docker compose up -d

# Dev mode (hot reload)
docker compose -f docker-compose.dev.yml up -d

# Frontend only (port 3000)
pnpm run dev:frontend

# Backend only (port 8080)
pnpm run dev:backend

# AI Engine only (port 8001)
cd ai-engine && uvicorn main:app --reload --port 8001

# Run tests
pnpm run test                  # All tests
cd backend && pytest src/tests/unit/ -q  # Fast backend unit tests
cd ai-engine && pytest         # AI engine tests

# Code quality
pnpm run lint
pnpm run format
cd backend && ruff check src/
cd ai-engine && ruff check .
```

---

## Environment Variables

**Required**:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5433/portkit
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Optional**:
```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
SENTRY_DSN=https://...
```

---

## Common Pitfalls (Historical)

1. **Blocking calls in async code** — Never use `requests`, `time.sleep()`, `json.loads()` in coroutines
2. **Missing type hints** — All function signatures must have type hints
3. **Pydantic V1 patterns** — Use `ConfigDict(from_attributes=True)`, not `class Config`
4. **Missing error handling** — Every async operation can fail; handle gracefully
5. **N+1 queries** — Use `selectinload` or `joinedload` for relationships

---

## Testing Standards

- **Framework**: pytest + pytest-asyncio
- **Backend coverage floor**: 40% (CI-blocking)
- **AI engine coverage floor**: 65% (CI-blocking)
- **Test naming**: `test_<feature>_<scenario>_<expected>`
- **Test markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.asyncio`

---

## Image Handling

- **Upload validation**: ClamAV scanning for all uploads
- **Allowed sources**: Unsplash, Picsum (via URL)
- **Forbidden**: Pexels (403 errors on direct linking)
- **Storage**: Local filesystem or S3-compatible storage

---

*This reference document should be updated when project structure or conventions change.*