# CLAUDE.md - ModPorter-AI Agent Handbook

**Version:** 1.0
**Updated:** 2026-03-31

---

## Project Overview

**ModPorter-AI** is an AI-powered Java to Bedrock Minecraft mod converter.

- **Backend:** FastAPI (Python 3.11+)
- **AI Engine:** Multi-agent conversion pipeline with RAG
- **Database:** PostgreSQL with pgvector
- **Queue:** Redis with RQ
- **Frontend:** Next.js 14 (separate repo)

---

## Critical Rules for AI Agents

### MUST DO (Non-Negotiable)

1. **Read `.factory/tasks.md` BEFORE any action** - Contains current task state
2. **Mark tasks `in_progress` BEFORE starting work** - Not during or after
3. **Only ONE task `in_progress` at a time** - Parallel work via subagents only
4. **Complete tasks IMMEDIATELY when done** - Don't batch completions
5. **Write artifacts to FILES, not inline** - Code goes to files, return only file path + description
6. **Run tests after changes** - `cd backend && python3 -m pytest src/tests/unit/ -q --tb=no`

### NEVER DO (Forbidden Patterns)

```
❌ "Let me first understand..."
❌ "I'll start by exploring..."
❌ "Let me check what..."
❌ "I need to investigate..."
❌ Start work without creating/marking a task first
❌ Return code inline - always write to file
❌ Use sed/awk for edits - use patch instead
❌ Use cat/head/tail for reading - use read_file instead
```

### Correct Workflow

```
1. Read .factory/tasks.md
2. Create task if needed → Mark in_progress
3. Investigate → Implement → Verify
4. Complete task immediately
5. Show full task list
```

---

## Project Structure

```
ModPorter-AI/
├── backend/
│   ├── src/
│   │   ├── api/              # FastAPI endpoints
│   │   ├── services/         # Business logic
│   │   ├── models/           # Pydantic models
│   │   ├── db/               # Database models & connections
│   │   ├── ai-engine/        # Multi-agent conversion system
│   │   │   ├── agents/       # Agent implementations
│   │   │   ├── tools/        # Agent tools
│   │   │   └── pipelines/    # Conversion pipelines
│   │   └── tests/
│   │       ├── unit/         # Unit tests
│   │       └── integration/  # Integration tests
│   └── requirements.txt
├── docs/                     # Documentation
├── .factory/
│   └── tasks.md             # Current task state (MANDATORY READ)
├── .claude/                  # Claude-specific configs
│   ├── commands/            # Slash commands
│   └── skills/               # Reusable skills
└── .github/
    └── workflows/           # CI/CD pipelines
```

---

## Coding Standards

### Python Patterns

| Pattern | Use | Example |
|---------|-----|---------|
| **Async First** | All I/O operations | `async def fetch_user()` |
| **Pydantic V2** | Data validation | `class User(BaseModel)` |
| **Dependency Injection** | Shared resources | `Depends(get_db)` |
| **Context Managers** | Resource cleanup | `async with` for DB |
| **Type Hints** | All function signatures | `def process(x: int) -> str` |

### Forbidden Patterns

```python
# ❌ NEVER do these:
- time.sleep()              # Use asyncio.sleep()
- requests.get()           # Use httpx async client
- json.loads()             # Use pydantic models
- dict.get() with default  # Use pydantic validation
- global state              # Use dependency injection
```

### Error Handling

```python
# ✅ CORRECT error handling pattern:
try:
    result = await risky_operation()
except SpecificError as e:
    logger.warning(f"Handled error: {e}")
    return fallback_result()
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise  # Re-raise unexpected errors
```

---

## Testing Standards

### Test Structure

```
tests/
├── unit/
│   ├── test_<module>.py           # One file per module
│   └── conftest.py                 # Shared fixtures
└── integration/
    └── test_<workflow>.py          # E2E workflows
```

### Test Naming

```
test_<feature>_<scenario>_<expected>
```

Examples:
- `test_user_create_success` → Creates user successfully
- `test_user_create_duplicate_email` → Handles duplicate email
- `test_conversion_job_status_transitions` → Validates job state machine

### Test Markers

```python
@pytest.mark.unit           # Unit tests (fast, no I/O)
@pytest.mark.integration    # Integration tests (DB, Redis)
@pytest.mark.slow           # Tests > 5 seconds
@pytest.mark.xfail(reason="Known issue")  # Expected failures
```

### Running Tests

```bash
# Full unit suite (fast)
cd backend && python3 -m pytest src/tests/unit/ -q --tb=no

# With coverage
cd backend && python3 -m pytest src/tests/unit/ --cov=src --cov-fail-under=80

# Single test file
cd backend && python3 -m pytest src/tests/unit/test_validation_api.py -v

# Single test class
cd backend && python3 -m pytest src/tests/unit/test_validation_api.py::TestValidationAPI -v
```

---

## API Design Patterns

### Endpoint Structure

```python
# ✅ Standard CRUD pattern:
@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate, db: AsyncSession = Depends(get_db)):
    """Create a new item with validation."""
    result = await db.execute(select(Item).where(Item.id == item.id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Item already exists")
    # ... implementation
    return item

# ✅ Standard list pattern with pagination:
@router.get("/items", response_model=ListResponse)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
```

### Response Models

```python
class ItemResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ListResponse(BaseModel):
    items: list[ItemResponse]
    total: int
    skip: int
    limit: int
```

---

## Git Workflow

### Commit Messages

```
<type>(<scope>): <description>

Types: feat|fix|docs|style|refactor|test|chore|ci
Scopes: api|backend|ai-engine|tests|docs|ci

Examples:
feat(ai-engine): add semantic checker agent
fix(validation): correct job status transition logic
docs(readme): update installation instructions
test(batch): add batch conversion edge cases
ci(github): add coverage gate to PR checks
```

### Branch Naming

```
feature/<ticket>-<short-description>
bugfix/<ticket>-<short-description>
hotfix/<ticket>-<short-description>
```

### Pull Request Checklist

- [ ] Tests pass (`pytest src/tests/unit/ -q`)
- [ ] Coverage maintained or improved
- [ ] No linting errors (`ruff check`)
- [ ] Docs updated if needed
- [ ] PR description explains WHY, not just WHAT

---

## CI/CD Pipeline

### Quality Gates (Automated)

```
1. Pre-commit:
   - ruff format check
   - ruff lint check
   - Bandit security scan
   - Gitleaks secrets detection

2. PR Checks:
   - Unit tests (80%+ coverage required)
   - Integration tests
   - Type checking (ruff)
   - Security scan (Trivy, CodeQL)

3. Merge Gate:
   - All green
   - At least 1 approval
   - No unresolved comments
```

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci-tests.yml` | PR/push | Run test suite |
| `ci-security.yml` | PR/push | Security scanning |
| `ci-lint.yml` | PR/push | Code quality |
| `deploy-staging.yml` | Push to develop | Deploy staging |
| `deploy-prod.yml` | Release tag | Deploy production |

---

## Common Workflows

### Implementing a New Feature

```
1. Create branch: git checkout -b feature/TICKET-description
2. Create task in .factory/tasks.md
3. Mark task in_progress
4. Write tests first (TDD)
5. Implement feature
6. Run tests: pytest src/tests/unit/ -q
7. Commit with conventional message
8. Push and create PR
```

### Fixing a Bug

```
1. Create branch: git checkout -b bugfix/TICKET-description
2. Create task in .factory/tasks.md
3. Mark task in_progress
4. Write failing test that reproduces bug
5. Fix the bug
6. Verify test passes
7. Commit and PR
```

### Code Review

```
1. AI performs automatic review (CLAUDE.md code-review skill)
2. Human reviews:
   - Logic correctness
   - Security implications
   - UX/UI consistency
   - Performance concerns
3. Address feedback
4. Approve and merge
```

---

## Environment Variables

### Backend (.env)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/modporter

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Engine
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=codellama:13b

# Security
SECRET_KEY=<generate-with-openssl-rand-base64-32>
REFRESH_SECRET_KEY=<generate-separate-key>

# Testing
TESTING=true
```

---

## Resources

### Key Files

| File | Purpose |
|------|---------|
| `.factory/tasks.md` | Current task state |
| `docs/GAP-ANALYSIS-v2.5.md` | v2.5 gaps |
| `docs/AI-AGENT-BEST-PRACTICES.md` | AI agent patterns |
| `backend/src/main.py` | FastAPI app entry |
| `backend/src/api/` | API endpoints |
| `backend/src/ai-engine/` | Multi-agent system |

### Documentation

- **Requirements:** `.planning/REQUIREMENTS.md`
- **Roadmap:** `.planning/ROADMAP.md`
- **Architecture:** `.planning/ARCHITECTURE.md`
- **ADRs:** `.planning/adrs/`

---

## Emergency Procedures

### If Tests Are Failing

```bash
# 1. Run with verbose output
cd backend && python3 -m pytest src/tests/unit/ -v --tb=short 2>&1 | tail -50

# 2. Check for import errors
cd backend && python3 -c "from src.main import app"

# 3. Verify environment
cd backend && python3 -c "import os; print(os.getenv('TESTING'))"

# 4. Run single failing test
cd backend && python3 -m pytest path/to/failing_test.py -v
```

### If Service Won't Start

```bash
# 1. Check environment variables
cd backend && python3 -c "from src.config import settings; print(settings)"

# 2. Verify database connection
cd backend && python3 -c "import asyncio; from src.db.database import engine; asyncio.run(engine.connect())"

# 3. Check Redis
redis-cli ping

# 4. Verify port availability
lsof -i :8000
```

---

## Agent Memory

### Cross-Session Facts (Saved to Memory)

- User preferences (communication style, preferred workflows)
- Environment details (ports, paths, tool versions)
- Project conventions (naming, patterns)
- Tool quirks (known issues, workarounds)

### Skills Available

```
autonomous-ai-agents/
├── claude-code      # Delegate to Claude Code subagent
├── codex            # Delegate to OpenAI Codex
├── opencode         # Delegate to OpenCode
└── hermes-agent     # Delegate to Hermes subagent

software-development/
├── code-review      # Automated code review
├── plan             # Plan mode for complex tasks
├── subagent-driven  # Orchestrate multiple subagents
├── systematic-debugging  # Debug workflow
├── test-driven-development  # TDD workflow
└── writing-plans    # Write implementation plans
```

---

**Last Updated:** 2026-03-31
**Next Review:** When v2.5 phases change
